from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, FastAPI, Query, Request, Response, status
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from app.projects.create_project import create_project
from app.projects.list_projects import read_project_list
from app.refusal import (
    NotPossibleNow,
    ProjectsUnavailable,
    RunsUnavailable,
    UnknownId,
    UnusableRequest,
)
from app.register.export_register import JSON_FORMAT, MARKDOWN_FORMAT
from app.register.read_export import read_export
from app.review.finish_review import finish_review
from app.review.review_queue import APPROVED, REJECTED
from app.review.submit_decision import submit_decision
from app.runs.run_lifecycle import RunEngine, require_run_engine, start_run
from app.runs.run_status import read_run_status


router = APIRouter()

# The one place a core refusal becomes an HTTP status code; the message it
# carries is never rewritten here.
REFUSAL_STATUS_CODES = (
    (UnusableRequest, status.HTTP_400_BAD_REQUEST),
    (UnknownId, status.HTTP_404_NOT_FOUND),
    (NotPossibleNow, status.HTTP_409_CONFLICT),
    (RunsUnavailable, status.HTTP_503_SERVICE_UNAVAILABLE),
    (ProjectsUnavailable, status.HTTP_503_SERVICE_UNAVAILABLE),
)


class CreateProject(BaseModel):
    # Only carried here. What counts as usable is core's answer, so that this
    # door and the MCP tool refuse the same request the same way. There is no
    # `name` field: the project's name is derived from the folder, in core,
    # never supplied by a caller.
    source_folder_path: str


class StartRun(BaseModel):
    project_id: UUID


class SubmitDecision(BaseModel):
    decision_id: UUID
    outcome: Literal[APPROVED, REJECTED]


def add_refusal_responses(application: FastAPI) -> None:
    """Answer each kind of core refusal with the status code that matches it."""
    for refused_kind, status_code in REFUSAL_STATUS_CODES:
        application.add_exception_handler(refused_kind, _refusal_response(status_code))


@router.post("/projects", status_code=status.HTTP_201_CREATED)
async def create_one_project(
    request: Request,
    response: Response,
    payload: CreateProject,
) -> dict[str, Any]:
    async with request.app.state.pool.connection() as connection:
        created = await create_project(
            connection,
            payload.source_folder_path,
            request.app.state.project_root,
            request.app.state.projects_config_path,
        )
    if not created.created:
        # This folder already had a project, so nothing was created — a caller
        # reading only the status code must not be told one was.
        response.status_code = status.HTTP_200_OK
    return {"project_id": str(created.project_id), "created": created.created}


@router.get("/projects")
async def read_all_projects(request: Request) -> dict[str, Any]:
    async with request.app.state.pool.connection() as connection:
        return await read_project_list(
            connection,
            request.app.state.project_root,
            request.app.state.projects_config_path,
        )


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
async def start_one_run(request: Request, payload: StartRun) -> dict[str, str]:
    return await start_run(_run_engine(request), payload.project_id)


@router.get("/runs/{run_id}")
async def read_one_run(request: Request, run_id: UUID) -> dict[str, Any]:
    async with request.app.state.pool.connection() as connection:
        return await read_run_status(connection, run_id)


@router.post("/runs/{run_id}/decisions")
async def submit_one_decision(
    request: Request,
    run_id: UUID,
    payload: SubmitDecision,
) -> dict[str, str]:
    async with request.app.state.pool.connection() as connection:
        return await submit_decision(
            connection,
            run_id,
            payload.decision_id,
            payload.outcome,
        )


@router.post("/runs/{run_id}/finish-review")
async def finish_one_review(request: Request, run_id: UUID) -> dict[str, str]:
    return await finish_review(_run_engine(request), run_id)


@router.get("/runs/{run_id}/export")
async def read_one_export(
    request: Request,
    run_id: UUID,
    export_format: str = Query(JSON_FORMAT, alias="format"),
) -> Any:
    async with request.app.state.pool.connection() as connection:
        exported = await read_export(connection, run_id, export_format)
    if export_format == MARKDOWN_FORMAT:
        return PlainTextResponse(exported)
    return exported


def _refusal_response(
    status_code: int,
) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    async def refused(_: Request, refusal: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(refusal)})

    return refused


def _run_engine(request: Request) -> RunEngine:
    return require_run_engine(
        request.app.state.run_engine,
        request.app.state.run_engine_unavailable,
    )
