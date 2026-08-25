from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import AsyncConnection

from app.examine.read_findings import examine_under_review
from app.review.add_will_write import what_add_will_write
from app.review.review_queue import decisions_of_run
from app.runs.finished_stages import ordered_finished_stages
from app.runs.run_records import require_run
from app.runs.statuses import DONE


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
        "decisions": [_decision_as_read(decision) for decision in decisions],
        # What the adding press would write, and how many questions still
        # stand between the person and pressing it. The screen renders the
        # count as a sentence; the payload carries the number, so both doors
        # are told the same thing and neither is told a sentence twice.
        "add_will_write": await what_add_will_write(connection, run),
        "open_decisions": sum(
            1 for decision in decisions if decision["outcome"] is None
        ),
        "examine": await examine_under_review(connection, run),
        "finished_stages": ordered_finished_stages(run["finished_stages"]),
        # The key name is machinery both doors already answer with; since the
        # snapshot went, `done` is the fact it derives from — a run is
        # `done` exactly when its changes were added to the register.
        "exported": run["status"] == DONE,
    }


def _decision_as_read(decision: dict[str, Any]) -> dict[str, Any]:
    """One decision as both doors answer with it: the text, and its parts.

    The text is the whole thing a person reads, frozen when the decision was
    raised. The parts are the same text taken apart, so a screen can lay it
    out without writing a word of its own (S21) — and neither is rebuilt out
    of cells that have moved since. The export gate is a button, not a card,
    so it has no parts and answers with the empty shapes.
    """
    parts = decision["parts"] or {}
    return {
        "decision_id": str(decision["id"]),
        "kind": decision["kind"],
        "question": decision["question"],
        "outcome": decision["outcome"],
        "rule_text": decision["rule_text"],
        "row_number": decision["row_number"],
        "issue": decision["issue"],
        "evidence": decision["evidence"],
        "row": parts.get("row"),
        "quotes": parts.get("quotes", []),
        "if_approved": parts.get("if_approved", []),
        "if_rejected": parts.get("if_rejected"),
    }
