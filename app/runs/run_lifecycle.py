from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from psycopg import AsyncConnection
from psycopg.errors import UniqueViolation
from psycopg_pool import AsyncConnectionPool

from app.ingest.collect_batch import top_level_files
from app.refusal import RunsUnavailable, UnusableRequest
from app.run_logging import log_run_event
from app.runs.run_records import record_run_failure, require_project
from app.runs.statuses import RUNNING, WAITING


REVIEW_FINISHED = "review finished"
EMPTY_FOLDER_REFUSAL = "This folder has no files. Add a document."


@dataclass(frozen=True)
class RunEngine:
    """Everything a run needs to execute, built once at application start."""

    graph: CompiledStateGraph
    pool: AsyncConnectionPool
    checkpointer: AsyncPostgresSaver
    # A project's folder is named relative to the repository, so the root has
    # to travel with the engine: the empty-folder check below is reached by
    # POST /runs, the MCP tool and the watcher alike, and none of the three
    # can be trusted to pass its own idea of where the repository is.
    project_root: Path
    background_runs: set[asyncio.Task] = field(default_factory=set)


def require_run_engine(
    engine: RunEngine | None,
    unavailable_reason: str | None,
) -> RunEngine:
    """The engine a run needs, or the reason no run can start yet."""
    if engine is None:
        raise RunsUnavailable(unavailable_reason)
    return engine


async def start_run(engine: RunEngine, project_id: UUID) -> dict[str, str]:
    """Start or queue one run against a project that exists, and say which."""
    async with engine.pool.connection() as connection:
        await require_project(connection, project_id)
    started = await start_or_queue_run(engine, project_id)
    return {"run_id": str(started["run_id"]), "status": started["status"]}


async def start_or_queue_run(engine: RunEngine, project_id: UUID) -> dict[str, Any]:
    """Claim the project's durable lock, or queue behind whoever holds it.

    The lock is the active run row itself: PostgreSQL allows only one run per
    project in a running or waiting-for-review state, and that row survives the
    process dying, which is what startup resume takes over.

    A run over an empty folder is refused before the lock is claimed, so the
    three doors that reach this function — POST /runs, the MCP `start_run`
    tool and the watcher — all refuse in the same words (S15).
    """
    await _refuse_a_folder_with_no_files(engine, project_id)
    async with engine.pool.connection() as connection:
        run_id = uuid4()
        if await _insert_run(connection, run_id, project_id, RUNNING):
            _launch(
                engine,
                run_id,
                project_id,
                graph_input=_first_state(run_id, project_id),
            )
            return {"run_id": run_id, "status": RUNNING}

        if await _insert_run(connection, run_id, project_id, WAITING):
            log_run_event(
                logging.INFO,
                "run_queued",
                "Another run is active on this project, so this run is waiting "
                "and starts by itself when that one ends.",
                str(run_id),
            )
            return {"run_id": run_id, "status": WAITING}

        # Only one waiting run per project: a waiting run holds no batch, so a
        # second one would do identical work.
        waiting = await connection.execute(
            "SELECT id FROM runs WHERE project_id = %s AND status = %s",
            (project_id, WAITING),
        )
        already_waiting = await waiting.fetchone()
        return {"run_id": already_waiting["id"], "status": WAITING}


async def _refuse_a_folder_with_no_files(
    engine: RunEngine,
    project_id: UUID,
) -> None:
    """Refuse a run that has nothing to read, naming what to do about it.

    A run over an empty folder reads nothing, proposes nothing and ends early
    — a record of a run that was never worth starting. The same top-level file
    rule Ingest reads by, so the two can never disagree about what a folder
    holds.
    """
    async with engine.pool.connection() as connection:
        project = await require_project(connection, project_id)
    folder = Path(project["source_folder_path"])
    if not folder.is_absolute():
        folder = engine.project_root / folder
    if folder.is_dir() and not await asyncio.to_thread(top_level_files, folder):
        raise UnusableRequest(EMPTY_FOLDER_REFUSAL)


def resume_after_review(engine: RunEngine, run_id: UUID, project_id: UUID) -> None:
    _launch(engine, run_id, project_id, graph_input=Command(resume=REVIEW_FINISHED))


async def resume_unfinished_runs(engine: RunEngine) -> None:
    """Continue whatever a killed process left behind, without a resume call."""
    async with engine.pool.connection() as connection:
        stranded = await connection.execute(
            "SELECT id, project_id FROM runs WHERE status = %s ORDER BY created_at",
            (RUNNING,),
        )
        stranded_runs = list(await stranded.fetchall())

        queued = await connection.execute(
            "SELECT id, project_id FROM runs WHERE status = %s ORDER BY created_at",
            (WAITING,),
        )
        queued_runs = list(await queued.fetchall())

    for run in stranded_runs:
        run_id, project_id = run["id"], run["project_id"]
        continues = await _has_checkpoint(engine, run_id)
        log_run_event(
            logging.INFO,
            "run_resumed",
            "Taking over this project's lock and continuing the run "
            + (
                "from its last checkpoint."
                if continues
                else "from the start, because it was killed before its first "
                "checkpoint was written."
            ),
            str(run_id),
        )
        _launch(
            engine,
            run_id,
            project_id,
            graph_input=None if continues else _first_state(run_id, project_id),
        )

    for run in queued_runs:
        await _start_waiting_run(engine, run["project_id"])


def _first_state(run_id: UUID, project_id: UUID) -> dict[str, Any]:
    return {"run_id": str(run_id), "project_id": str(project_id)}


def _launch(
    engine: RunEngine,
    run_id: UUID,
    project_id: UUID,
    graph_input: Any,
) -> None:
    task = asyncio.create_task(_execute(engine, run_id, project_id, graph_input))
    # Held so the loop cannot collect a run that nobody is awaiting.
    engine.background_runs.add(task)
    task.add_done_callback(engine.background_runs.discard)


async def _execute(
    engine: RunEngine,
    run_id: UUID,
    project_id: UUID,
    graph_input: Any,
) -> None:
    configuration = {"configurable": {"thread_id": str(run_id)}}
    try:
        await engine.graph.ainvoke(graph_input, configuration)
    except Exception as error:  # the top of the run: report, never disappear
        # A run that stopped deliberately is never resumed: the same input
        # would stop it again. A killed process leaves 'running' behind
        # instead, and that is what startup resume takes over.
        failure_reason = f"{error} This run will not restart by itself."
        log_run_event(
            logging.ERROR,
            "run_failed",
            f"The run stopped on {type(error).__name__}: {error} It is "
            "'failed' and is not started again by itself — fix the cause "
            "named here and start another run. Nothing this run read counts "
            "as read, so the next run reads those documents again.",
            str(run_id),
        )
        async with engine.pool.connection() as connection:
            await record_run_failure(connection, run_id, failure_reason)
    await _start_waiting_run(engine, project_id)


async def _start_waiting_run(engine: RunEngine, project_id: UUID) -> None:
    async with engine.pool.connection() as connection:
        waiting = await connection.execute(
            "SELECT id FROM runs WHERE project_id = %s AND status = %s",
            (project_id, WAITING),
        )
        queued = await waiting.fetchone()
        if queued is None:
            return
        try:
            async with connection.transaction():
                await connection.execute(
                    "UPDATE runs SET status = %s WHERE id = %s",
                    (RUNNING, queued["id"]),
                )
        except UniqueViolation:
            # The project's lock is still held, so the queued run keeps waiting.
            return

    log_run_event(
        logging.INFO,
        "queued_run_started",
        "The project's lock was released, so the run that was waiting started.",
        str(queued["id"]),
    )
    _launch(
        engine,
        queued["id"],
        project_id,
        graph_input=_first_state(queued["id"], project_id),
    )


async def _insert_run(
    connection: AsyncConnection,
    run_id: UUID,
    project_id: UUID,
    status: str,
) -> bool:
    try:
        async with connection.transaction():
            await connection.execute(
                "INSERT INTO runs (id, project_id, status) VALUES (%s, %s, %s)",
                (run_id, project_id, status),
            )
    except UniqueViolation:
        return False
    return True


async def _has_checkpoint(engine: RunEngine, run_id: UUID) -> bool:
    saved = await engine.checkpointer.aget_tuple(
        {"configurable": {"thread_id": str(run_id)}}
    )
    return saved is not None
