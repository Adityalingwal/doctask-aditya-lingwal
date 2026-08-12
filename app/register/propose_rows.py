from __future__ import annotations

from typing import Any, NamedTuple
from uuid import UUID, uuid4

from psycopg import AsyncConnection

from app.extract.answer import CLIENT_REQUIREMENTS_DOCUMENT
from app.match.match_requirements import NEW_ROW
from app.register.cells import (
    BLOCKED_ON_NOT_KNOWN_YET,
    DATE_UNKNOWN,
    FIRST_SEEN,
    IN_WRITING,
    IN_WRITING_NOT_KNOWN_YET,
    LAST_MOVED,
    STATUS_NO_EVIDENCE_YET,
    TESTING_NOT_KNOWN_YET,
    WHAT_WAS_ASKED,
)
from app.review.review_queue import raise_possible_match_decision


UNSET_FINGERPRINT = ""


class ProposedRegister(NamedTuple):
    proposed_row_ids: list[UUID]
    gated_row_numbers: list[int]


async def committed_rows(
    connection: AsyncConnection,
    project_id: UUID,
) -> list[dict[str, Any]]:
    result = await connection.execute(
        "SELECT id, row_number, what_was_asked FROM register_rows "
        "WHERE project_id = %s AND is_committed ORDER BY row_number",
        (project_id,),
    )
    return list(await result.fetchall())


async def propose_rows(
    connection: AsyncConnection,
    run_id: UUID,
    project_id: UUID,
    requirements: list[dict[str, Any]],
    outcome_by_requirement: dict[int, tuple[str, int | None]],
) -> ProposedRegister:
    """Write this batch's requirements as proposed rows, gating uncertain ones.

    Nothing here is settled: a proposed row becomes part of the register only
    when Commit runs after the Delivery Owner has approved the export.
    """
    register = await committed_rows(connection, project_id)
    candidate_by_number = {row["row_number"]: row for row in register}
    next_row_number = await _next_row_number(connection, project_id)

    proposed_row_ids: list[UUID] = []
    gated_row_numbers: list[int] = []

    for index, requirement in enumerate(requirements):
        outcome, candidate_number = outcome_by_requirement.get(
            index, (NEW_ROW, None)
        )
        candidate = candidate_by_number.get(candidate_number or -1)

        row_id = await _insert_proposed_row(
            connection,
            run_id,
            project_id,
            next_row_number,
            requirement,
        )
        proposed_row_ids.append(row_id)

        if outcome != NEW_ROW and candidate is not None:
            await raise_possible_match_decision(
                connection,
                run_id,
                _merge_question(requirement, candidate),
                row_id,
                candidate["id"],
            )
            gated_row_numbers.append(next_row_number)

        next_row_number += 1

    return ProposedRegister(
        proposed_row_ids=proposed_row_ids,
        gated_row_numbers=gated_row_numbers,
    )


def _merge_question(
    requirement: dict[str, Any],
    candidate: dict[str, Any],
) -> str:
    # The sentence is the record: months later an audit must show what the
    # person actually read when they answered, not a pointer to a row that may
    # have moved on since.
    return (
        f"Merge '{requirement['summary']}' "
        f"(from {requirement['source_file']}) into row "
        f"#{candidate['row_number']} — {candidate['what_was_asked']}?"
    )


async def _next_row_number(connection: AsyncConnection, project_id: UUID) -> int:
    result = await connection.execute(
        "SELECT COALESCE(MAX(row_number), 0) AS highest FROM register_rows "
        "WHERE project_id = %s",
        (project_id,),
    )
    highest = await result.fetchone()
    return int(highest["highest"]) + 1


async def _insert_proposed_row(
    connection: AsyncConnection,
    run_id: UUID,
    project_id: UUID,
    row_number: int,
    requirement: dict[str, Any],
) -> UUID:
    row_id = uuid4()
    document_date = requirement.get("document_date")
    seen_on = document_date["summary"] if document_date else DATE_UNKNOWN
    in_writing = _in_writing_cell(requirement)

    await connection.execute(
        "INSERT INTO register_rows (id, project_id, what_was_asked, in_writing, "
        "what_testing_found, status, blocked_on, first_seen, last_moved, "
        "fingerprint, row_number, proposed_by_run_id, is_committed) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false)",
        (
            row_id,
            project_id,
            requirement["summary"],
            in_writing,
            TESTING_NOT_KNOWN_YET,
            STATUS_NO_EVIDENCE_YET,
            BLOCKED_ON_NOT_KNOWN_YET,
            seen_on,
            seen_on,
            UNSET_FINGERPRINT,
            row_number,
            run_id,
        ),
    )

    await _insert_citation(connection, row_id, WHAT_WAS_ASKED, requirement)
    if in_writing != IN_WRITING_NOT_KNOWN_YET:
        await _insert_citation(connection, row_id, IN_WRITING, requirement)
    if document_date is not None:
        for cell_name in (FIRST_SEEN, LAST_MOVED):
            await _insert_citation(connection, row_id, cell_name, document_date)
    return row_id


def _in_writing_cell(requirement: dict[str, Any]) -> str:
    # "No" would claim the written requirements document was read in full and
    # this is not in it. Only a document actually read can support that.
    if requirement.get("document_type") == CLIENT_REQUIREMENTS_DOCUMENT:
        return f"Yes — written in {requirement['source_file']}."
    return IN_WRITING_NOT_KNOWN_YET


async def _insert_citation(
    connection: AsyncConnection,
    register_row_id: UUID,
    cell_name: str,
    evidence: dict[str, Any],
) -> None:
    await connection.execute(
        "INSERT INTO citations (id, register_row_id, cell_name, source_file, "
        "source_place, source_words) VALUES (%s, %s, %s, %s, %s, %s)",
        (
            uuid4(),
            register_row_id,
            cell_name,
            evidence["source_file"],
            evidence["place"],
            evidence["source_words"],
        ),
    )
