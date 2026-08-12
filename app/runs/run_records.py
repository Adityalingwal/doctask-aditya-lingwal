from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from app.runs.statuses import ACTIVE_STATUSES, FAILED, TERMINAL_STATUSES


async def read_run(connection: AsyncConnection, run_id: UUID) -> dict[str, Any] | None:
    result = await connection.execute(
        "SELECT id, project_id, status, current_stage, started_at, finished_at, "
        "skipped, ended_early_reason, failure_reason, export_json FROM runs "
        "WHERE id = %s",
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
