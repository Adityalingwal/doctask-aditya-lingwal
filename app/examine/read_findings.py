from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import AsyncConnection

from app.examine.deliverable_checks import DELIVERABLE_CHECKS
from app.examine.frozen_rules import frozen_rules_of_run
from app.review.review_queue import APPROVED


_SELECT_FINDINGS = (
    "SELECT findings.id, findings.rule_id, findings.rule_text, findings.issue, "
    "findings.evidence, findings.question, findings.decision_key, "
    "decisions.outcome, register_rows.row_number, "
    "COALESCE(register_rows.merged_into_register_row_id, register_rows.id) "
    "AS register_row_id FROM findings "
    "JOIN decisions ON decisions.id = findings.decision_key "
    "JOIN register_rows ON register_rows.id = findings.register_row_id "
)
_ORDER_FINDINGS = " ORDER BY register_rows.row_number, findings.rule_id"


async def findings_of_run(
    connection: AsyncConnection,
    run_id: UUID,
    approved_only: bool = False,
) -> list[dict[str, Any]]:
    """This run's findings, each carrying the answer read from its decision.

    A finding stores no answer of its own, so the outcome is joined from the
    decision that gates it and there is never a second copy to fall behind.
    """
    if approved_only:
        return await _findings_matching(
            connection,
            "WHERE findings.run_id = %s AND decisions.outcome = %s",
            (run_id, APPROVED),
        )
    return await _findings_matching(
        connection,
        "WHERE findings.run_id = %s",
        (run_id,),
    )


async def approved_findings_of_project(
    connection: AsyncConnection,
    project_id: UUID,
) -> list[dict[str, Any]]:
    """Every finding a person approved onto a row of this project's register."""
    return await _findings_matching(
        connection,
        "WHERE register_rows.project_id = %s AND decisions.outcome = %s",
        (project_id, APPROVED),
    )


async def rules_that_ran(
    connection: AsyncConnection,
    run_id: UUID,
) -> list[dict[str, str]]:
    """Every rule this run was judged against — the user's, then the two owed."""
    frozen = await frozen_rules_of_run(connection, run_id) or []
    return [{"id": rule["id"], "text": rule["text"]} for rule in frozen] + [
        dict(check) for check in DELIVERABLE_CHECKS
    ]


async def _findings_matching(
    connection: AsyncConnection,
    condition: str,
    parameters: tuple[Any, ...],
) -> list[dict[str, Any]]:
    result = await connection.execute(
        _SELECT_FINDINGS + condition + _ORDER_FINDINGS,
        parameters,
    )
    return [
        {
            "finding_id": finding["id"],
            "decision_id": finding["decision_key"],
            "register_row_id": finding["register_row_id"],
            "row_number": finding["row_number"],
            "rule_id": finding["rule_id"],
            "rule_text": finding["rule_text"],
            "issue": finding["issue"],
            "evidence": finding["evidence"],
            "question": finding["question"],
            "outcome": finding["outcome"],
        }
        for finding in await result.fetchall()
    ]
