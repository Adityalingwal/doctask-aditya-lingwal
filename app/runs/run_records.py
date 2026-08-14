from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from app.refusal import UnknownId
from app.runs.statuses import (
    ACTIVE_STATUSES,
    FAILED,
    RUNNING,
    TERMINAL_STATUSES,
    WAITING_FOR_REVIEW,
)


async def require_run(connection: AsyncConnection, run_id: UUID) -> dict[str, Any]:
    """The run a caller named, or the refusal every door reports for it."""
    run = await read_run(connection, run_id)
    if run is None:
        raise UnknownId(
            f"no run has id {run_id} — start one with POST /runs and poll the "
            "id it returns."
        )
    return run


async def read_run(connection: AsyncConnection, run_id: UUID) -> dict[str, Any] | None:
    result = await connection.execute(
        "SELECT id, project_id, status, current_stage, started_at, finished_at, "
        "skipped, ended_early_reason, failure_reason, export_json, "
        "review_finished_at, examined_row_count, finished_stages "
        "FROM runs WHERE id = %s",
        (run_id,),
    )
    return await result.fetchone()


async def read_project(
    connection: AsyncConnection,
    project_id: UUID,
) -> dict[str, Any] | None:
    result = await connection.execute(
        "SELECT id, name, source_folder_path FROM projects WHERE id = %s",
        (project_id,),
    )
    return await result.fetchone()


async def enter_stage(
    connection: AsyncConnection,
    run_id: UUID,
    stage: str,
) -> None:
    await connection.execute(
        "UPDATE runs SET current_stage = %s, "
        "started_at = COALESCE(started_at, CURRENT_TIMESTAMP) WHERE id = %s",
        (stage, run_id),
    )


async def set_run_status(
    connection: AsyncConnection,
    run_id: UUID,
    status: str,
    ended_early_reason: str | None = None,
) -> None:
    finished_at = (
        "CURRENT_TIMESTAMP" if status in TERMINAL_STATUSES else "finished_at"
    )
    await connection.execute(
        "UPDATE runs SET status = %s, "
        "ended_early_reason = COALESCE(%s, ended_early_reason), "
        f"finished_at = {finished_at} WHERE id = %s",
        (status, ended_early_reason, run_id),
    )


async def claim_review_finished(
    connection: AsyncConnection,
    run_id: UUID,
) -> dict[str, Any] | None:
    """Take one run out of review, or report that another caller already did.

    Checking the status and writing it is one statement on purpose: between a
    read and a later write, a second caller finishes the same review and the
    graph is driven twice over one run. review_finished_at is set in this same
    statement so it is exactly as durable as the status change: a crash right
    after this commits still leaves both facts consistent for the next resume.
    """
    result = await connection.execute(
        "UPDATE runs SET status = %s, review_finished_at = CURRENT_TIMESTAMP "
        "WHERE id = %s AND status = %s RETURNING project_id",
        (RUNNING, run_id, WAITING_FOR_REVIEW),
    )
    return await result.fetchone()


async def record_run_failure(
    connection: AsyncConnection,
    run_id: UUID,
    failure_reason: str,
) -> None:
    """End a run that stopped on a cause it cannot recover from.

    Only a run still holding its project's lock is failed: a run that already
    reached a terminal status finished, whatever was raised afterwards.
    """
    await connection.execute(
        "UPDATE runs SET status = %s, failure_reason = %s, "
        "finished_at = CURRENT_TIMESTAMP "
        "WHERE id = %s AND status = ANY(%s)",
        (FAILED, failure_reason, run_id, list(ACTIVE_STATUSES)),
    )


async def append_skipped(
    connection: AsyncConnection,
    run_id: UUID,
    entries: list[dict[str, str]],
) -> None:
    if not entries:
        return
    await connection.execute(
        "UPDATE runs SET skipped = skipped || %s WHERE id = %s",
        (Jsonb(entries), run_id),
    )
