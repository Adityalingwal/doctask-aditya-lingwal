from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from psycopg import AsyncConnection


POSSIBLE_MATCH_DECISION = "possible match"
OBSERVATION_MATCH_DECISION = "observation match"
EXPORT_DECISION = "export"
FINDING_DECISION = "finding"
APPROVED = "approved"
REJECTED = "rejected"


async def raise_finding_decision(
    connection: AsyncConnection,
    run_id: UUID,
    question: str,
) -> UUID:
    decision_id = uuid4()
    await connection.execute(
        "INSERT INTO decisions (id, run_id, kind, question) "
        "VALUES (%s, %s, %s, %s)",
        (decision_id, run_id, FINDING_DECISION, question),
    )
    return decision_id


async def raise_possible_match_decision(
    connection: AsyncConnection,
    run_id: UUID,
    question: str,
    proposed_register_row_id: UUID,
    candidate_register_row_id: UUID,
) -> UUID:
    decision_id = uuid4()
    await connection.execute(
        "INSERT INTO decisions (id, run_id, kind, question, "
        "proposed_register_row_id, candidate_register_row_id) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (
            decision_id,
            run_id,
            POSSIBLE_MATCH_DECISION,
            question,
            proposed_register_row_id,
            candidate_register_row_id,
        ),
    )
    return decision_id


async def raise_observation_match_decision(
    connection: AsyncConnection,
    run_id: UUID,
    question: str,
    candidate_register_row_id: UUID,
) -> UUID:
    """Ask before this batch's evidence changes what a committed row says."""
    decision_id = uuid4()
    await connection.execute(
        "INSERT INTO decisions (id, run_id, kind, question, "
        "candidate_register_row_id) VALUES (%s, %s, %s, %s, %s)",
        (
            decision_id,
            run_id,
            OBSERVATION_MATCH_DECISION,
            question,
            candidate_register_row_id,
        ),
    )
    return decision_id


async def ensure_export_decision(
    connection: AsyncConnection,
    run_id: UUID,
    question: str,
) -> UUID:
    """Raise the export gate once, however often Review is re-entered."""
    existing = await connection.execute(
        "SELECT id FROM decisions WHERE run_id = %s AND kind = %s",
        (run_id, EXPORT_DECISION),
    )
    already_raised = await existing.fetchone()
    if already_raised is not None:
        return already_raised["id"]

    decision_id = uuid4()
    await connection.execute(
        "INSERT INTO decisions (id, run_id, kind, question) VALUES (%s, %s, %s, %s)",
        (decision_id, run_id, EXPORT_DECISION, question),
    )
    return decision_id


async def decisions_of_run(
    connection: AsyncConnection,
    run_id: UUID,
) -> list[dict[str, Any]]:
    """Every decision this run raised, a finding's own rule/row/evidence included.

    The screen shows a finding as three labelled parts and never a rule code
    (screen 4), which the flat `question` sentence alone cannot carry — so a
    finding decision is joined to its row in `findings` for `rule_text`,
    `issue` and `evidence`, and to `register_rows` for the row number the
    finding is against. Every other kind of decision carries these as `null`.
    """
    result = await connection.execute(
        "SELECT decisions.id, decisions.kind, decisions.question, "
        "decisions.proposed_register_row_id, "
        "decisions.candidate_register_row_id, decisions.outcome, "
        "decisions.decided_at, findings.rule_text, findings.issue, "
        "findings.evidence, register_rows.row_number AS finding_row_number "
        "FROM decisions "
        "LEFT JOIN findings ON findings.decision_key = decisions.id "
        "LEFT JOIN register_rows ON register_rows.id = findings.register_row_id "
        "WHERE decisions.run_id = %s ORDER BY decisions.kind, decisions.id",
        (run_id,),
    )
    return list(await result.fetchall())


async def unanswered_decisions(
    connection: AsyncConnection,
    run_id: UUID,
) -> list[dict[str, Any]]:
    result = await connection.execute(
        "SELECT id, kind, question FROM decisions "
        "WHERE run_id = %s AND outcome IS NULL ORDER BY kind, id",
        (run_id,),
    )
    return list(await result.fetchall())


async def answer_decision(
    connection: AsyncConnection,
    run_id: UUID,
    decision_id: UUID,
    outcome: str,
) -> bool:
    """Record one answer, overwriting an earlier one, until review is finished."""
    result = await connection.execute(
        "UPDATE decisions SET outcome = %s, decided_at = CURRENT_TIMESTAMP "
        "WHERE id = %s AND run_id = %s RETURNING id",
        (outcome, decision_id, run_id),
    )
    return await result.fetchone() is not None


async def export_was_approved(connection: AsyncConnection, run_id: UUID) -> bool:
    result = await connection.execute(
        "SELECT outcome FROM decisions WHERE run_id = %s AND kind = %s",
        (run_id, EXPORT_DECISION),
    )
    answered = await result.fetchone()
    return answered is not None and answered["outcome"] == APPROVED
