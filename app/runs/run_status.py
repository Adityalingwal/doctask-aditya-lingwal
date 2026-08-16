from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import AsyncConnection

from app.examine.read_findings import examine_under_review
from app.review.review_queue import decisions_of_run
from app.runs.finished_stages import ordered_finished_stages
from app.runs.run_records import require_run


async def read_run_status(
    connection: AsyncConnection,
    run_id: UUID,
) -> dict[str, Any]:
    """Everything a caller is told about one run, read back from the database."""
    run = await require_run(connection, run_id)
    decisions = await decisions_of_run(connection, run_id)
    return {
        "run_id": str(run_id),
        "project_id": str(run["project_id"]),
        "status": run["status"],
        "stage": run["current_stage"],
        "skipped": run["skipped"],
        "reported_instructions": run["reported_instructions"],
        "ended_early_reason": run["ended_early_reason"],
        "failure_reason": run["failure_reason"],
        "decisions": [
            {
                "decision_id": str(decision["id"]),
                "kind": decision["kind"],
                "question": decision["question"],
                "outcome": decision["outcome"],
                "rule_text": decision["rule_text"],
                "row_number": decision["finding_row_number"],
                "issue": decision["issue"],
                "evidence": decision["evidence"],
            }
            for decision in decisions
        ],
        "examine": await examine_under_review(connection, run),
        "finished_stages": ordered_finished_stages(run["finished_stages"]),
        "exported": run["export_json"] is not None,
    }
