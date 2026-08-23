from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from psycopg import AsyncConnection

from app.review.review_queue import FINDING_DECISION, raise_finding_decision


async def record_findings(
    connection: AsyncConnection,
    run_id: UUID,
    findings: list[dict[str, Any]],
) -> list[UUID]:
    """Write this run's findings, each with the question that gates it.

    Nothing here touches a register cell: Examine states a problem and asks,
    and only Commit acts on the answer.
    """
    written: list[UUID] = []
    async with connection.transaction():
        await _clear_what_this_run_found_before(connection, run_id)
        for finding in findings:
            decision_key = await raise_finding_decision(
                connection,
                run_id,
                finding["question"],
                finding["parts"],
            )
            finding_id = uuid4()
            await connection.execute(
                "INSERT INTO findings (id, run_id, register_row_id, rule_id, "
                "rule_text, issue, evidence, question, decision_key) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    finding_id,
                    run_id,
                    finding["register_row_id"],
                    finding["rule_id"],
                    finding["rule_text"],
                    finding["issue"],
                    finding["evidence"],
                    finding["question"],
                    decision_key,
                ),
            )
            written.append(finding_id)
    return written


async def _clear_what_this_run_found_before(
    connection: AsyncConnection,
    run_id: UUID,
) -> None:
    """Drop this run's own unanswered findings, so a re-run replaces rather than adds.

    Examine judges the whole register in one call, so a half-written result
    cannot be continued row by row. What goes is strictly this run's findings
    that nobody has answered yet; an answered one is the Delivery Owner's and
    is never thrown away.
    """
    await connection.execute(
        "DELETE FROM findings WHERE run_id = %s AND decision_key IN "
        "(SELECT id FROM decisions WHERE run_id = %s AND outcome IS NULL)",
        (run_id, run_id),
    )
    await connection.execute(
        "DELETE FROM decisions WHERE run_id = %s AND kind = %s "
        "AND outcome IS NULL",
        (run_id, FINDING_DECISION),
    )
