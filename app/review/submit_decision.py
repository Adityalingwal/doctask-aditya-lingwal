from __future__ import annotations

from uuid import UUID

from psycopg import AsyncConnection

from app.refusal import NotPossibleNow, UnknownId
from app.review.review_queue import answer_decision
from app.runs.run_records import require_run
from app.runs.statuses import WAITING_FOR_REVIEW


async def submit_decision(
    connection: AsyncConnection,
    run_id: UUID,
    decision_id: UUID,
    outcome: str,
) -> dict[str, str]:
    """Record one person's answer to one decision of a run that is at review."""
    run = await require_run(connection, run_id)
    if run["status"] != WAITING_FOR_REVIEW:
        raise NotPossibleNow(
            f"this run is '{run['status']}', not at review, so no decision can "
            f"be recorded against it — poll GET /runs/{run_id} until it is "
            f"'{WAITING_FOR_REVIEW}'."
        )
    if run["review_finished_at"] is not None:
        raise NotPossibleNow(
            "this run's review has already finished, so no decision can be "
            f"recorded against it — poll GET /runs/{run_id} for what it did "
            "next."
        )
    answered = await answer_decision(connection, run_id, decision_id, outcome)
    if not answered:
        raise UnknownId(
            f"this run has no decision with id {decision_id} — read GET "
            f"/runs/{run_id} for the decisions it is actually waiting on."
        )
    return {"decision_id": str(decision_id), "outcome": outcome}
