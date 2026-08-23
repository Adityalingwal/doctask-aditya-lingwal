from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from psycopg import AsyncConnection

from app.extract.answer import CLIENT_REQUIREMENTS_DOCUMENT, TESTING_FEEDBACK
from app.ingest.read_once import documents_read_by_project
from app.register.audit_entries import write_cell_change
from app.register.cells import (
    CELL_NAMES,
    IN_WRITING,
    IN_WRITING_NOT_KNOWN_YET,
    NOT_MENTIONED,
    TESTING_NOT_KNOWN_YET,
    WHAT_TESTING_FOUND,
    absence_statement_for,
    fingerprint_of_cells,
)


# Which cell each kind of document answers, including by saying nothing. A
# meeting note and a handover summary answer neither, so their silence writes
# nothing at all, and `Status` is never moved by an absence.
CELL_A_KIND_ANSWERS = {
    CLIENT_REQUIREMENTS_DOCUMENT: IN_WRITING,
    TESTING_FEEDBACK: WHAT_TESTING_FOUND,
}
UNANSWERED_VALUE = {
    IN_WRITING: IN_WRITING_NOT_KNOWN_YET,
    WHAT_TESTING_FOUND: TESTING_NOT_KNOWN_YET,
}


async def apply_absences(
    connection: AsyncConnection,
    run_id: UUID,
    project_id: UUID,
) -> list[int]:
    """Record, on every row it does not mention, that a document was read.

    Run inside Commit, after merges, proposals and moves have put on the rows
    everything the documents did say — so what is left is what they did not.
    Two scopes, and both are needed for one batch of four documents to end
    exactly where the same four documents one at a time end:

    - every requirements or testing document **this run** read, against every
      row the register will hold, the rows this run proposes included;
    - every such document **an earlier run** read, against only the rows this
      run proposes — a row born after a document was read must still record
      that document's silence, and the older rows recorded it when they were
      committed.

    A document mentions a row when the row cites it, which is what this run
    already holds; nothing here asks a model what a document left out.
    """
    rows = await _rows_an_absence_may_reach(connection, project_id, run_id)
    if not rows:
        return []

    cited_files = await _cited_files_by_row(connection, [row["id"] for row in rows])
    proposed_now = [row for row in rows if not row["is_committed"]]
    moved_row_numbers: set[int] = set()

    for kind, cell_name in CELL_A_KIND_ANSWERS.items():
        read = await documents_read_by_project(
            connection, project_id, kind, include_run_id=run_id
        )
        for document in read:
            reaches = rows if document["run_id"] == run_id else proposed_now
            for row in reaches:
                if document["source_path"] in cited_files.get(row["id"], set()):
                    continue
                moved = await _record_the_silence(
                    connection, row, cell_name, document, run_id
                )
                if moved:
                    moved_row_numbers.add(row["row_number"])
    return sorted(moved_row_numbers)


async def _record_the_silence(
    connection: AsyncConnection,
    row: dict[str, Any],
    cell_name: str,
    document: dict[str, Any],
    run_id: UUID,
) -> bool:
    """Write one document's silence about one row, and say whether a cell moved.

    An absence never overwrites an answer: it fills a cell still holding `Not
    known yet` and leaves `Yes` or a testing verdict exactly as it stands.
    Behind a cell an earlier document already left reading `Not mentioned` it
    adds its own evidence and changes nothing — so no history entry and no
    fingerprint move, because a cell moves history and a citation does not.
    """
    cells = await _cells_of(connection, row["id"])
    standing = cells[cell_name]
    if standing not in (UNANSWERED_VALUE[cell_name], NOT_MENTIONED):
        return False

    await _write_the_absence_citation(
        connection, row["id"], cell_name, document["source_path"]
    )
    if standing == NOT_MENTIONED:
        return False

    await connection.execute(
        f"UPDATE register_rows SET {cell_name} = %s WHERE id = %s",
        (NOT_MENTIONED, row["id"]),
    )
    if not row["is_committed"]:
        # A row this run proposed has its whole first history and its first
        # fingerprint written when it is committed, a moment from now.
        return True

    await write_cell_change(
        connection,
        row["id"],
        cell_name,
        standing,
        NOT_MENTIONED,
        run_id,
        document["document_id"],
    )
    await connection.execute(
        "UPDATE register_rows SET fingerprint = %s WHERE id = %s",
        (fingerprint_of_cells({**cells, cell_name: NOT_MENTIONED}), row["id"]),
    )
    return True


async def _write_the_absence_citation(
    connection: AsyncConnection,
    register_row_id: UUID,
    cell_name: str,
    source_file: str,
) -> None:
    """Absence evidence: the file that was read, and the sentence saying so.

    No place and no words, because there are none to name — the check
    constraint on `citations` allows exactly this shape and no other.
    """
    await connection.execute(
        "INSERT INTO citations (id, register_row_id, cell_name, source_file, "
        "source_place, source_words, absence_statement) "
        "VALUES (%s, %s, %s, %s, NULL, NULL, %s)",
        (
            uuid4(),
            register_row_id,
            cell_name,
            source_file,
            absence_statement_for(source_file),
        ),
    )


async def _rows_an_absence_may_reach(
    connection: AsyncConnection,
    project_id: UUID,
    run_id: UUID,
) -> list[dict[str, Any]]:
    """The register as this run will leave it: committed rows plus its proposals.

    A proposal merged away is left out: its evidence has gone to the row that
    survives, and that row is in this list already.
    """
    result = await connection.execute(
        "SELECT id, row_number, is_committed FROM register_rows "
        "WHERE project_id = %s AND (is_committed OR proposed_by_run_id = %s) "
        "AND merged_into_register_row_id IS NULL ORDER BY row_number",
        (project_id, run_id),
    )
    return list(await result.fetchall())


async def _cells_of(
    connection: AsyncConnection,
    register_row_id: UUID,
) -> dict[str, str]:
    result = await connection.execute(
        "SELECT " + ", ".join(CELL_NAMES) + " FROM register_rows WHERE id = %s",
        (register_row_id,),
    )
    row = await result.fetchone()
    return {name: row[name] for name in CELL_NAMES}


async def _cited_files_by_row(
    connection: AsyncConnection,
    register_row_ids: list[UUID],
) -> dict[UUID, set[str]]:
    result = await connection.execute(
        "SELECT register_row_id, source_file FROM citations "
        "WHERE register_row_id = ANY(%s)",
        (register_row_ids,),
    )
    cited: dict[UUID, set[str]] = {}
    for citation in await result.fetchall():
        cited.setdefault(citation["register_row_id"], set()).add(
            citation["source_file"]
        )
    return cited
