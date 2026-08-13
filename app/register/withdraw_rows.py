from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from psycopg import AsyncConnection

from app.extract.answer import PRIMARY_DOCUMENT_TYPES
from app.match.match_requirements import NEW_ROW
from app.register.audit_entries import write_cell_change
from app.register.cells import (
    CELL_NAMES,
    DATE_UNKNOWN,
    LAST_MOVED,
    STATUS,
    STATUS_WITHDRAWN,
    WHAT_WAS_ASKED,
    fingerprint_of_cells,
)
from app.review.review_queue import (
    APPROVED,
    POSSIBLE_MATCH_DECISION,
    WITHDRAWAL_DECISION,
    decisions_of_run,
    raise_withdrawal_decision,
)


ABSENCE_STATEMENT = (
    "{source_file} was read again in full and no longer asks for this — the "
    "requirement is in none of its words. Open the file to check."
)


async def batch_reads_a_document_a_row_came_from(
    connection: AsyncConnection,
    run_id: UUID,
    project_id: UUID,
) -> bool:
    """Does this batch hold a document some committed row was asked for in?

    Only such a batch can withdraw anything, and it must reach Match even when
    its documents now ask for nothing at all — a document that dropped its last
    requirement is exactly the case a withdrawal exists for.
    """
    result = await connection.execute(
        "SELECT 1 FROM citations "
        "JOIN register_rows ON register_rows.id = citations.register_row_id "
        "WHERE register_rows.project_id = %s AND register_rows.is_committed "
        "AND citations.cell_name = %s AND citations.source_file IN "
        "(SELECT source_path FROM documents WHERE run_id = %s) LIMIT 1",
        (project_id, WHAT_WAS_ASKED, run_id),
    )
    return await result.fetchone() is not None


async def propose_withdrawals(
    connection: AsyncConnection,
    run_id: UUID,
    project_id: UUID,
    requirements: list[dict[str, Any]],
    outcome_by_requirement: dict[int, tuple[str, int | None]],
) -> list[int]:
    """Ask about each row a document this batch read again stopped asking for.

    Only the document whose words a row's `What was asked` citation quotes can
    withdraw that row, and only when its new extraction matched the row at
    neither confidence. Another document's silence proposes nothing: absence of
    mention is not evidence that anything was removed.
    """
    still_asked_for = _rows_this_batch_still_asks_for(
        requirements, outcome_by_requirement
    )
    already_being_asked_about = set(
        await _rows_under_a_possible_match(connection, run_id)
    )
    proposed_row_numbers: list[int] = []

    async with connection.transaction():
        for document in await _documents_read_again(connection, run_id):
            source_file = document["source_path"]
            for row in await _rows_this_document_supplied(
                connection, project_id, source_file
            ):
                if row["row_number"] in still_asked_for.get(source_file, frozenset()):
                    continue
                # Uncertain identity is a different question and is gated
                # already; asking both about one row would split one doubt
                # into two questions nobody can answer separately. The same
                # set keeps two documents from asking about one row twice.
                if row["id"] in already_being_asked_about:
                    continue
                if row[STATUS] == STATUS_WITHDRAWN:
                    continue
                await raise_withdrawal_decision(
                    connection,
                    run_id,
                    _withdrawal_question(row, source_file),
                    row["id"],
                )
                already_being_asked_about.add(row["id"])
                proposed_row_numbers.append(row["row_number"])

    return proposed_row_numbers


async def apply_approved_withdrawals(
    connection: AsyncConnection,
    run_id: UUID,
) -> list[int]:
    """Move each approved row's `Status` cell to `Withdrawn`, and cite the absence.

    This is an ordinary cell change: it writes cell audit, moves that row's
    fingerprint and no other's, and leaves the row's other cells, its existing
    citations and its `First seen` exactly as they were.
    """
    withdrawn_row_numbers: list[int] = []
    for decision in await decisions_of_run(connection, run_id):
        if decision["kind"] != WITHDRAWAL_DECISION:
            continue
        if decision["outcome"] != APPROVED:
            continue
        row_id = decision["candidate_register_row_id"]
        row = await _committed_row(connection, row_id)
        document = await _document_that_stopped_asking(connection, run_id, row_id)
        withdrawn_row_numbers.append(
            await _withdraw_one_row(connection, run_id, row, document)
        )
    return withdrawn_row_numbers


async def _withdraw_one_row(
    connection: AsyncConnection,
    run_id: UUID,
    row: dict[str, Any],
    document: dict[str, Any],
) -> int:
    cells = {name: row[name] for name in CELL_NAMES}
    moved_on = _date_of(document)
    moved = {**cells, STATUS: STATUS_WITHDRAWN, LAST_MOVED: moved_on}

    await connection.execute(
        "UPDATE register_rows SET status = %s, last_moved = %s, fingerprint = %s "
        "WHERE id = %s",
        (STATUS_WITHDRAWN, moved_on, fingerprint_of_cells(moved), row["id"]),
    )
    for cell_name in (STATUS, LAST_MOVED):
        if cells[cell_name] == moved[cell_name]:
            continue
        await write_cell_change(
            connection,
            row["id"],
            cell_name,
            cells[cell_name],
            moved[cell_name],
            run_id,
            document["id"],
        )
    await _cite_the_absence(connection, row["id"], document["source_path"])
    return row["row_number"]


async def _cite_the_absence(
    connection: AsyncConnection,
    register_row_id: UUID,
    source_file: str,
) -> None:
    """The first citation this system writes that quotes nothing.

    There are no words to quote, so there is no place to derive either; the
    statement names the file and says what is not in it, which is what a reader
    checks by opening it.
    """
    await connection.execute(
        "INSERT INTO citations (id, register_row_id, cell_name, source_file, "
        "source_place, source_words, absence_statement) "
        "VALUES (%s, %s, %s, %s, NULL, NULL, %s)",
        (
            uuid4(),
            register_row_id,
            STATUS,
            source_file,
            ABSENCE_STATEMENT.format(source_file=source_file),
        ),
    )


def _rows_this_batch_still_asks_for(
    requirements: list[dict[str, Any]],
    outcome_by_requirement: dict[int, tuple[str, int | None]],
) -> dict[str, frozenset[int]]:
    """Which register row each document in this batch still has a requirement for."""
    still_asked: dict[str, set[int]] = {}
    for index, requirement in enumerate(requirements):
        outcome, row_number = outcome_by_requirement[index]
        if outcome == NEW_ROW or row_number is None:
            continue
        still_asked.setdefault(requirement["source_file"], set()).add(row_number)
    return {
        source_file: frozenset(row_numbers)
        for source_file, row_numbers in still_asked.items()
    }


async def _rows_under_a_possible_match(
    connection: AsyncConnection,
    run_id: UUID,
) -> frozenset[UUID]:
    return frozenset(
        decision["candidate_register_row_id"]
        for decision in await decisions_of_run(connection, run_id)
        if decision["kind"] == POSSIBLE_MATCH_DECISION
    )


async def _documents_read_again(
    connection: AsyncConnection,
    run_id: UUID,
) -> list[dict[str, Any]]:
    """This run's documents that Extract actually read and judged a primary type.

    A document Extract skipped has no new extraction, so it says nothing about
    what it no longer asks for; a document that came back a related additional
    or unrelated one never reaches Match either, and silence from it is silence.
    """
    result = await connection.execute(
        "SELECT id, source_path, extraction FROM documents "
        "WHERE run_id = %s AND extraction IS NOT NULL "
        "AND extraction ->> 'document_type' = ANY(%s) ORDER BY source_path",
        (run_id, list(PRIMARY_DOCUMENT_TYPES)),
    )
    return list(await result.fetchall())


async def _rows_this_document_supplied(
    connection: AsyncConnection,
    project_id: UUID,
    source_file: str,
) -> list[dict[str, Any]]:
    result = await connection.execute(
        "SELECT DISTINCT register_rows.id, register_rows.row_number, "
        "register_rows.status, register_rows.what_was_asked FROM register_rows "
        "JOIN citations ON citations.register_row_id = register_rows.id "
        "WHERE register_rows.project_id = %s AND register_rows.is_committed "
        "AND citations.cell_name = %s AND citations.source_file = %s "
        "ORDER BY register_rows.row_number",
        (project_id, WHAT_WAS_ASKED, source_file),
    )
    return list(await result.fetchall())


async def _committed_row(
    connection: AsyncConnection,
    register_row_id: UUID,
) -> dict[str, Any]:
    result = await connection.execute(
        "SELECT id, row_number, " + ", ".join(CELL_NAMES) + " FROM register_rows "
        "WHERE id = %s",
        (register_row_id,),
    )
    return await result.fetchone()


async def _document_that_stopped_asking(
    connection: AsyncConnection,
    run_id: UUID,
    register_row_id: UUID,
) -> dict[str, Any]:
    result = await connection.execute(
        "SELECT documents.id, documents.source_path, documents.extraction "
        "FROM documents JOIN citations ON citations.source_file = "
        "documents.source_path WHERE documents.run_id = %s "
        "AND documents.extraction IS NOT NULL "
        "AND citations.register_row_id = %s AND citations.cell_name = %s "
        "ORDER BY documents.source_path LIMIT 1",
        (run_id, register_row_id, WHAT_WAS_ASKED),
    )
    return await result.fetchone()


def _date_of(document: dict[str, Any]) -> str:
    document_date = document["extraction"]["document_date"]
    return document_date["summary"] if document_date else DATE_UNKNOWN


def _withdrawal_question(row: dict[str, Any], source_file: str) -> str:
    # The sentence is the record: an audit months later must show what the
    # person actually read when they answered it.
    return (
        f"Withdraw row #{row['row_number']} — {row['what_was_asked']}? "
        f"{source_file} was read again and no longer asks for it."
    )
