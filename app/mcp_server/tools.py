from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP

from app.projects.create_project import create_project
from app.projects.list_projects import read_project_list
from app.register.export_register import JSON_FORMAT
from app.register.read_export import read_register
from app.register.read_history import read_history
from app.review.finish_review import finish_review
from app.review.review_queue import APPROVED, REJECTED
from app.review.submit_decision import submit_decision
from app.runs.run_lifecycle import RunEngine, require_run_engine, start_run
from app.runs.run_status import read_run_status


MCP_SERVER_NAME = "requirements-delivery-register"
MCP_PATH = "/mcp"
MCP_INSTRUCTIONS = (
    "Drive the Requirements-to-Delivery Register: create a project, start a "
    "run, poll its status, answer each decision it raises, finish the review, "
    "then read the project's register. A run is not one call — start_run "
    "returns a run id and get_run_status is polled until the run reports it "
    "is done."
)


def build_mcp_server(application: FastAPI) -> FastMCP:
    """The eight endpoints as eight tools over the same core functions they call.

    The tools close over the running application, so they share its connection
    pool and its run engine instead of holding a second copy of either.
    """
    server = FastMCP(
        MCP_SERVER_NAME,
        instructions=MCP_INSTRUCTIONS,
        stateless_http=True,
        streamable_http_path="/",
    )

    @server.tool(name="create_project")
    async def create_project_tool(source_folder_path: str) -> dict[str, Any]:
        """Get or create the one project for this folder, and return its id.

        The folder is the project's identity and its name is derived from it
        — this tool takes no name. Calling it again for a folder that already
        has a project returns that project's id and `created: false`.
        """
        async with application.state.pool.connection() as connection:
            created = await create_project(
                connection,
                source_folder_path,
                application.state.project_root,
                application.state.projects_config_path,
            )
        return {"project_id": str(created.project_id), "created": created.created}

    @server.tool(name="start_run")
    async def start_run_tool(project_id: UUID) -> dict[str, str]:
        """Start or queue one run of a project, and return its id at once."""
        return await start_run(_run_engine(application), project_id)

    @server.tool(name="get_run_status")
    async def get_run_status_tool(run_id: UUID) -> dict[str, Any]:
        """Read one run's status, stage, what it did not use, decisions and findings."""
        async with application.state.pool.connection() as connection:
            return await read_run_status(connection, run_id)

    @server.tool(name="list_projects")
    async def list_projects_tool() -> dict[str, Any]:
        """List every project, each with its runs nested, and the folders a new one may watch."""
        async with application.state.pool.connection() as connection:
            return await read_project_list(
                connection,
                application.state.project_root,
                application.state.projects_config_path,
            )

    @server.tool(name="submit_decision")
    async def submit_decision_tool(
        run_id: UUID,
        decision_id: UUID,
        outcome: Literal[APPROVED, REJECTED],
    ) -> dict[str, str]:
        """Answer one decision this run raised, approving or rejecting it."""
        async with application.state.pool.connection() as connection:
            return await submit_decision(connection, run_id, decision_id, outcome)

    @server.tool(name="finish_review")
    async def finish_review_tool(
        run_id: UUID,
        add_to_register: bool,
    ) -> dict[str, str]:
        """End one run's review once every decision it raised is answered.

        `add_to_register`: yes = add this run's changes to the register; no =
        discard this run's changes. It has no default — one press ends the
        review, and the call has to say which of the two it is.
        """
        return await finish_review(_run_engine(application), run_id, add_to_register)

    @server.tool(name="get_register")
    async def get_register_tool(
        project_id: UUID,
        register_format: str = JSON_FORMAT,
    ) -> Any:
        """Read one project's register, live from its committed rows, as json or as markdown."""
        async with application.state.pool.connection() as connection:
            return await read_register(connection, project_id, register_format)

    @server.tool(name="get_history")
    async def get_history_tool(project_id: UUID) -> dict[str, Any]:
        """Read what changed in one project's register, when, and from which document."""
        async with application.state.pool.connection() as connection:
            return await read_history(connection, project_id)

    return server


def _run_engine(application: FastAPI) -> RunEngine:
    return require_run_engine(
        application.state.run_engine,
        application.state.run_engine_unavailable,
    )
