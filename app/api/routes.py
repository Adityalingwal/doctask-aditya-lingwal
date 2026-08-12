from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from psycopg import AsyncConnection
from pydantic import BaseModel, Field

from app.projects.create_project import SourceFolderMissing, create_project
from app.register.export_register import (
    EXPORT_FORMATS,
    JSON_FORMAT,
    MARKDOWN_FORMAT,
    export_as_markdown,
)
from app.review.review_queue import (
    APPROVED,
    REJECTED,
    answer_decision,
    decisions_of_run,
    unanswered_decisions,
)
from app.runs.run_lifecycle import (
    RunEngine,
    resume_after_review,
    start_or_queue_run,
)
from app.runs.run_records import read_project, read_run
from app.runs.statuses import WAITING_FOR_REVIEW


router = APIRouter()


class CreateProject(BaseModel):
    name: str = Field(min_length=1)
    source_folder_path: str = Field(min_length=1)


class StartRun(BaseModel):
    project_id: UUID


class SubmitDecision(BaseModel):
    decision_id: UUID
    outcome: Literal[APPROVED, REJECTED]


@router.post("/projects", status_code=status.HTTP_201_CREATED)
async def create_one_project(
    request: Request,
    payload: CreateProject,
) -> dict[str, str]:
    pool = request.app.state.pool
    async with pool.connection() as connection:
        try:
            project_id = await create_project(
                connection,
                payload.name,
                payload.source_folder_path,
                request.app.state.project_root,
            )
        except SourceFolderMissing as missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(missing),
            ) from missing
    return {"project_id": str(project_id)}


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
async def start_run(request: Request, payload: StartRun) -> dict[str, str]:
    engine = _run_engine(request)
    async with engine.pool.connection() as connection:
        if await read_project(connection, payload.project_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"no project has id {payload.project_id} — create one with "
                    "POST /projects and start the run against the id it returns."
                ),
            )
    started = await start_or_queue_run(engine, payload.project_id)
    return {"run_id": str(started["run_id"]), "status": started["status"]}


@router.get("/runs/{run_id}")
async def read_run_status(request: Request, run_id: UUID) -> dict[str, Any]:
    pool = request.app.state.pool
    async with pool.connection() as connection:
        run = await _run_or_404(connection, run_id)
        decisions = await decisions_of_run(connection, run_id)
    return {
        "run_id": str(run_id),
        "project_id": str(run["project_id"]),
        "status": run["status"],
        "stage": run["current_stage"],
        "skipped": run["skipped"],
        "ended_early_reason": run["ended_early_reason"],
        "failure_reason": run["failure_reason"],
        "decisions": [
            {
                "decision_id": str(decision["id"]),
                "kind": decision["kind"],
                "question": decision["question"],
                "outcome": decision["outcome"],
            }
            for decision in decisions
        ],
        "exported": run["export_json"] is not None,
    }


@router.post("/runs/{run_id}/decisions")
async def submit_decision(
    request: Request,
    run_id: UUID,
    payload: SubmitDecision,
) -> dict[str, str]:
    pool = request.app.state.pool
    async with pool.connection() as connection:
        run = await _run_or_404(connection, run_id)
        if run["status"] != WAITING_FOR_REVIEW:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"this run is '{run['status']}', not at review, so no "
                    "decision can be recorded against it — poll GET "
                    f"/runs/{run_id} until it is '{WAITING_FOR_REVIEW}'."
                ),
            )
        answered = await answer_decision(
            connection,
            run_id,
            payload.decision_id,
            payload.outcome,
        )
    if not answered:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"this run has no decision with id {payload.decision_id} — read "
                f"GET /runs/{run_id} for the decisions it is actually waiting on."
            ),
        )
    return {"decision_id": str(payload.decision_id), "outcome": payload.outcome}


@router.post("/runs/{run_id}/finish-review")
async def finish_review(request: Request, run_id: UUID) -> dict[str, str]:
    engine = _run_engine(request)
    async with engine.pool.connection() as connection:
        run = await _run_or_404(connection, run_id)
        if run["status"] != WAITING_FOR_REVIEW:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"this run is '{run['status']}', not at review, so there is "
                    "no review to finish."
                ),
            )
        outstanding = await unanswered_decisions(connection, run_id)

    if outstanding:
        # Finishing with an unanswered gate would claim the review completed
        # while an approved output may not exist.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"review cannot finish while {len(outstanding)} decision(s) "
                "are unanswered: "
                + "; ".join(
                    f"{decision['id']} — {decision['question']}"
                    for decision in outstanding
                )
                + f". Answer each with POST /runs/{run_id}/decisions, then "
                "finish the review again."
            ),
        )

    resume_after_review(engine, run_id, run["project_id"])
    return {"run_id": str(run_id), "status": "review finished"}


@router.get("/runs/{run_id}/export")
async def read_export(
    request: Request,
    run_id: UUID,
    export_format: str = Query(JSON_FORMAT, alias="format"),
) -> Any:
    if export_format not in EXPORT_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"'{export_format}' is not an export format — ask for "
                f"{' or '.join(EXPORT_FORMATS)}."
            ),
        )
    pool = request.app.state.pool
    async with pool.connection() as connection:
        run = await _run_or_404(connection, run_id)
    if run["export_json"] is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "this run has exported nothing — the register is exported only "
                "after the Delivery Owner approves the export decision and "
                f"POST /runs/{run_id}/finish-review commits the run."
            ),
        )
    if export_format == MARKDOWN_FORMAT:
        return PlainTextResponse(export_as_markdown(run["export_json"]))
    return run["export_json"]


def _run_engine(request: Request) -> RunEngine:
    engine = request.app.state.run_engine
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=request.app.state.run_engine_unavailable,
        )
    return engine


async def _run_or_404(
    connection: AsyncConnection,
    run_id: UUID,
) -> dict[str, Any]:
    run = await read_run(connection, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"no run has id {run_id} — start one with POST /runs and poll "
                "the id it returns."
            ),
        )
    return run
