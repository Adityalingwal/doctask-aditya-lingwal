from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from app.runs.statuses import STAGE_ORDER


async def record_stage_finished(
    connection: AsyncConnection,
    run_id: UUID,
    stage: str,
) -> None:
    """Mark that one stage finished, keyed by its own name.

    Written with a `||` merge rather than an append, so a node that re-enters
    after a kill (D12) overwrites its own key instead of adding a second one —
    the same reason `runs.stage_timings` was merged this way before it.
    """
    await connection.execute(
        "UPDATE runs SET finished_stages = finished_stages || %s WHERE id = %s",
        (Jsonb({stage: True}), run_id),
    )


def ordered_finished_stages(finished_stages: dict[str, Any]) -> list[str]:
    """Which stages this run has finished, in pipeline order.

    Reads the keyed object back as the ordered list every caller wants: a
    rules-only run's `finished_stages` never gained an `extract` or `match`
    key, so neither one is in what comes back.
    """
    return [stage for stage in STAGE_ORDER if finished_stages.get(stage)]
