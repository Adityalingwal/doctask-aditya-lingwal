from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb


POSSIBLE_MATCH_DECISION = "possible match"
OBSERVATION_MATCH_DECISION = "observation match"
EXPORT_DECISION = "export"
FINDING_DECISION = "finding"
APPROVED = "approved"
REJECTED = "rejected"

# What the person read on the button they pressed, frozen with their answer.
# No row count in it: a rules-only run ends the same way with zero proposed
# rows, and a wording naming a count would read wrongly there. This gate is
# the one place a human approves the whole run's work, not a download prompt,
# so "export" is never the verb.
EXPORT_QUESTION = "Add this run's changes to the register?"


async def raise_finding_decision(
    connection: AsyncConnection,
    run_id: UUID,
    question: str,
    parts: dict[str, Any],
) -> UUID:
    decision_id = uuid4()
    await connection.execute(
        "INSERT INTO decisions (id, run_id, kind, question, parts) "
        "VALUES (%s, %s, %s, %s, %s)",
        (decision_id, run_id, FINDING_DECISION, question, Jsonb(parts)),
    )
    return decision_id


async def raise_possible_match_decision(
    connection: AsyncConnection,
    run_id: UUID,
    question: str,
    parts: dict[str, Any],
    proposed_register_row_id: UUID,
    candidate_register_row_id: UUID,
) -> UUID:
    decision_id = uuid4()
    await connection.execute(
        "INSERT INTO decisions (id, run_id, kind, question, parts, "
        "proposed_register_row_id, candidate_register_row_id) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (
            decision_id,
            run_id,
            POSSIBLE_MATCH_DECISION,
            question,
            Jsonb(parts),
            proposed_register_row_id,
            candidate_register_row_id,
        ),
    )
    return decision_id


async def raise_observation_match_decision(
    connection: AsyncConnection,
    run_id: UUID,
    question: str,
    parts: dict[str, Any],
    candidate_register_row_id: UUID,
) -> UUID:
    """Ask before this batch's evidence changes what a committed row says."""
    decision_id = uuid4()
    await connection.execute(
        "INSERT INTO decisions (id, run_id, kind, question, parts, "
        "candidate_register_row_id) VALUES (%s, %s, %s, %s, %s, %s)",
        (
            decision_id,
            run_id,
            OBSERVATION_MATCH_DECISION,
            question,
            Jsonb(parts),
            candidate_register_row_id,
        ),
    )
    return decision_id


async def record_export_answer(
    connection: AsyncConnection,
    run_id: UUID,
    add_to_register: bool,
) -> UUID:
    """Write the gate the person answered by pressing one of the two buttons.

    The question and the answer are written together because the press is the
    decision: it was never sitting in the queue waiting to be answered, and a
    row holding one without the other would say a person read something they
    did not.
    """
    decision_id = uuid4()
    await connection.execute(
        "INSERT INTO decisions (id, run_id, kind, question, outcome, decided_at) "
        "VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)",
        (
            decision_id,
            run_id,
            EXPORT_DECISION,
            EXPORT_QUESTION,
            APPROVED if add_to_register else REJECTED,
        ),
    )
    return decision_id


async def decisions_of_run(
    connection: AsyncConnection,
    run_id: UUID,
) -> list[dict[str, Any]]:
    """Every decision this run raised, with the row and the change it is about.

    The screen shows a finding as labelled parts and never a rule code (screen
    4), which the flat `question` sentence alone cannot carry — so a finding
    decision is joined to its row in `findings` for `rule_text`, `issue` and
    `evidence`. `row_number` is the register row the decision is about,
    whichever kind it is: a finding's own row, or the row a match would attach
    to. The export gate is about no single row and carries null.

    The order is the one every surface shows (S23): by the row the decision is
    about, then possible match before observation match before finding, then
    id. The export gate is about no row, so its null row number sorts last.
    """
    result = await connection.execute(
        "SELECT decisions.id, decisions.kind, decisions.question, "
        "decisions.parts, decisions.proposed_register_row_id, "
        "decisions.candidate_register_row_id, decisions.outcome, "
        "decisions.decided_at, findings.rule_text, findings.issue, "
        "findings.evidence, COALESCE(finding_rows.row_number, "
        "candidate_rows.row_number) AS row_number "
        "FROM decisions "
        "LEFT JOIN findings ON findings.decision_key = decisions.id "
        "LEFT JOIN register_rows AS finding_rows "
        "ON finding_rows.id = findings.register_row_id "
        "LEFT JOIN register_rows AS candidate_rows "
        "ON candidate_rows.id = decisions.candidate_register_row_id "
        "WHERE decisions.run_id = %s "
        "ORDER BY COALESCE(finding_rows.row_number, candidate_rows.row_number), "
        "CASE decisions.kind WHEN %s THEN 0 WHEN %s THEN 1 WHEN %s THEN 2 "
        "ELSE 3 END, decisions.id",
        (
            run_id,
            POSSIBLE_MATCH_DECISION,
            OBSERVATION_MATCH_DECISION,
            FINDING_DECISION,
        ),
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
