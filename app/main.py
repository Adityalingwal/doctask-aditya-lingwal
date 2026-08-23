from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from app.api.routes import add_refusal_responses, router
from app.database import build_connection_pool
from app.examine.frozen_rules import load_rules
from app.graph.register_graph import build_register_graph
from app.ingest.read_source_document import READER_EXTENSIONS
from app.mcp_server.tools import MCP_PATH, build_mcp_server
from app.model.client import build_model_client
from app.review_screen.serve_screen import serve_review_screen
from app.run_logging import configure_run_logging, log_run_event
from app.runs.run_lifecycle import RunEngine, resume_unfinished_runs
from app.runs.watch_source_folders import load_watcher_settings, watch_source_folders
from app.startup import (
    load_formats_config,
    migrate_database,
    report_formats_without_readers,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_URL_ENVIRONMENT_VARIABLE = "DATABASE_URL"
FORMATS_CONFIG_PATH = PROJECT_ROOT / "config" / "formats.yaml"
MODEL_CONFIG_PATH = PROJECT_ROOT / "config" / "model.yaml"
PROJECTS_CONFIG_PATH = PROJECT_ROOT / "config" / "projects.yaml"
RULES_CONFIG_PATH_ENVIRONMENT_VARIABLE = "RULES_CONFIG_PATH"
DEFAULT_RULES_CONFIG_PATH = PROJECT_ROOT / "config" / "rules.yaml"
WATCHER_CONFIG_PATH_ENVIRONMENT_VARIABLE = "WATCHER_CONFIG_PATH"
DEFAULT_WATCHER_CONFIG_PATH = PROJECT_ROOT / "config" / "watcher.yaml"
REVIEW_SCREEN_PATH = "/ui"
BUILT_REVIEW_SCREEN = PROJECT_ROOT / "ui" / "dist"


def database_url_from_environment() -> str:
    database_url = os.environ.get(DATABASE_URL_ENVIRONMENT_VARIABLE)
    if database_url is None:
        raise RuntimeError(
            "DATABASE_URL is not set — set it to the PostgreSQL connection URL "
            "before starting the application."
        )
    return database_url


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_run_logging()
    database_url = database_url_from_environment()
    await asyncio.to_thread(migrate_database, PROJECT_ROOT, database_url)
    await asyncio.to_thread(
        report_formats_without_readers,
        FORMATS_CONFIG_PATH,
        READER_EXTENSIONS,
    )
    formats = await asyncio.to_thread(load_formats_config, FORMATS_CONFIG_PATH)
    watcher_settings = await asyncio.to_thread(
        load_watcher_settings,
        _config_path(
            os.environ,
            WATCHER_CONFIG_PATH_ENVIRONMENT_VARIABLE,
            DEFAULT_WATCHER_CONFIG_PATH,
        ),
    )
    rules_config_path = _config_path(
        os.environ,
        RULES_CONFIG_PATH_ENVIRONMENT_VARIABLE,
        DEFAULT_RULES_CONFIG_PATH,
    )
    # Read here only to refuse a broken rules file at startup rather than on
    # the first run, which would be after a person had already started one.
    # Every run still freezes the file itself, so what is loaded here is not
    # what any run is judged against.
    await asyncio.to_thread(load_rules, rules_config_path)

    pool = build_connection_pool(database_url)
    await pool.open(wait=True)
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()

    app.state.pool = pool
    app.state.project_root = PROJECT_ROOT
    app.state.projects_config_path = PROJECTS_CONFIG_PATH
    app.state.run_engine, app.state.run_engine_unavailable = _build_run_engine(
        pool,
        checkpointer,
        frozenset(formats.accepted_extensions),
        formats.page_limit,
        rules_config_path,
    )

    engine = app.state.run_engine
    watching: asyncio.Task | None = None
    if engine is not None:
        # Not awaited: a resumed run heads for human review and would never
        # return, leaving the application unable to answer anything.
        resuming = asyncio.create_task(resume_unfinished_runs(engine))
        engine.background_runs.add(resuming)
        resuming.add_done_callback(engine.background_runs.discard)
        watching = asyncio.create_task(
            watch_source_folders(engine, PROJECT_ROOT, watcher_settings)
        )

    # The mounted MCP server is not started by its own lifespan, so this one
    # runs its session manager for as long as the application answers at all.
    async with app.state.mcp_server.session_manager.run():
        yield
    if watching is not None:
        watching.cancel()
    await pool.close()


def _config_path(
    environment: Mapping[str, str],
    variable_name: str,
    shipped_default: Path,
) -> Path:
    named = environment.get(variable_name)
    return Path(named) if named else shipped_default


def _build_run_engine(
    pool: AsyncConnectionPool,
    checkpointer: AsyncPostgresSaver,
    accepted_extensions: frozenset[str],
    page_limit: int,
    rules_config_path: Path,
) -> tuple[RunEngine | None, str | None]:
    """Build the one model client and the graph that is handed it.

    A missing key is reported rather than crashing the application: the
    stranger who has just run `docker compose up` gets a healthy service that
    tells them exactly what to supply before a run can start.
    """
    try:
        model_client = build_model_client(MODEL_CONFIG_PATH, os.environ)
    except RuntimeError as unavailable:
        log_run_event(
            logging.WARNING,
            "runs_unavailable",
            f"Runs cannot start yet: {unavailable}",
            None,
        )
        return None, str(unavailable)

    graph = build_register_graph(
        model_client,
        pool,
        checkpointer,
        PROJECT_ROOT,
        accepted_extensions,
        page_limit,
        rules_config_path,
    )
    return (
        RunEngine(
            graph=graph,
            pool=pool,
            checkpointer=checkpointer,
            project_root=PROJECT_ROOT,
        ),
        None,
    )


app = FastAPI(lifespan=lifespan)
app.include_router(router)
add_refusal_responses(app)
app.state.mcp_server = build_mcp_server(app)
app.mount(MCP_PATH, app.state.mcp_server.streamable_http_app())
serve_review_screen(app, BUILT_REVIEW_SCREEN, REVIEW_SCREEN_PATH)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}
