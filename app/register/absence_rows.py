from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

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
# The marker that tells an absence apart from an observation's move inside
# `runs.pending_moves`. Both travel in the one list so that Examine sees the
# register exactly as Commit will leave it, and Commit writes what Examine saw.
ABSENCE_MOVE = "absence"


async def propose_absences(
    connection: AsyncConnection,
    run_id: UUID,
    project_id: UUID,
) -> list[int]:
    """Work out, in Match, which rows a document was read and silent about.

    Stored on the run beside the observations' moves, never written to a row
    here: Examine reads the list to judge the register as Commit will leave it
    — a rule about a silent testing report cannot see the silence otherwise,
    because `Not mentioned` is only written after the person has answered —
    and Commit writes the same list, so the two can never disagree.

    Two scopes, both needed for one batch of four documents to end exactly
    where the same four documents one at a time end:

    - every requirements or testing document **this run** read, against every
      row the register will hold, the rows this run proposes included;
    - every such document **an earlier run** read, against only the rows this
      run proposes — a row born after a document was read must still record
      that document's silence, and the older rows recorded it when they were
      committed.

    A document mentions a row when the row cites it. What this run is still
    asking about — a possible match, an observation's move awaiting its
    answer — is not counted as a mention yet: if the person approves it, the
    merge or the move runs first at Commit and the cell it filled is left
    alone; if they reject it, the document really did not mention this row
    and the absence stands. Examine sees the same thing the same way, an
    assumed answer winning over an absence on one cell.
    """
    rows = await _rows_an_absence_may_reach(connection, project_id, run_id)
    if not rows:
        return []

    cited_files = await _cited_files_by_row(connection, [row["id"] for row in rows])
    proposed_now = [row for row in rows if not row["is_committed"]]
    moves: list[dict[str, Any]] = []
    absent_row_numbers: set[int] = set()

    for kind, cell_name in CELL_A_KIND_ANSWERS.items():
        read = await documents_read_by_project(
            connection, project_id, kind, include_run_id=run_id
        )
        for document in read:
            reaches = rows if document["run_id"] == run_id else proposed_now
            for row in reaches:
                if document["source_path"] in cited_files.get(str(row["id"]), set()):
                    continue
                if row[cell_name] not in (UNANSWERED_VALUE[cell_name], NOT_MENTIONED):
                    continue
                moves.append(_absence_move(row, cell_name, document))
                absent_row_numbers.add(row["row_number"])

    await _store_beside_the_observation_moves(connection, run_id, moves)
    return sorted(absent_row_numbers)


def is_absence(move: dict[str, Any]) -> bool:
    return move.get("kind") == ABSENCE_MOVE


async def write_absence(
    connection: AsyncConnection,
    row: dict[str, Any],
    move: dict[str, Any],
    run_id: UUID,
) -> bool:
    """Write one document's silence about one row, and say whether a cell moved.

    Called by `apply_moves` inside Commit, after the observations' moves on
    the same row. An absence never overwrites an answer: it fills a cell still
    holding `Not known yet` and leaves `Yes` or a testing verdict exactly as it
    stands — including a `Yes` an approved merge wrote a moment ago. Behind a
    cell an earlier document already left reading `Not mentioned` it adds its
    own evidence and changes nothing — so no history entry, because a cell
    moves history and a citation does not.
    """
    cell_name = move["cell"]
    cells = await _cells_of(connection, row["id"])
    standing = cells[cell_name]
    if standing not in (UNANSWERED_VALUE[cell_name], NOT_MENTIONED):
        return False

    citation = move["citations"][0]
    await _write_the_absence_citation(
        connection, row["id"], cell_name, citation["source_file"]
    )
    if standing == NOT_MENTIONED:
        return False

    await connection.execute(
        f"UPDATE register_rows SET {cell_name} = %s WHERE id = %s",
        (NOT_MENTIONED, row["id"]),
    )
    if row["is_committed"]:
        # A row this run proposed has its whole first history written when it
        # is committed, a moment from now; a committed row gets its
        # before-and-after here.
        await write_cell_change(
            connection,
            row["id"],
            cell_name,
            standing,
            NOT_MENTIONED,
            run_id,
            UUID(citation["document_id"]),
        )
    return True


def _absence_move(
    row: dict[str, Any],
    cell_name: str,
    document: dict[str, Any],
) -> dict[str, Any]:
    return {
        "kind": ABSENCE_MOVE,
        "register_row_id": str(row["id"]),
        "cell": cell_name,
        "value": NOT_MENTIONED,
        "citations": [
            {
                "source_file": document["source_path"],
                "document_id": str(document["document_id"]),
                "absence_statement": absence_statement_for(document["source_path"]),
            }
        ],
        "decision_id": None,
    }


async def _store_beside_the_observation_moves(
    connection: AsyncConnection,
    run_id: UUID,
    absences: list[dict[str, Any]],
) -> None:
    """Replace this run's absences in `pending_moves`, keeping the observations' moves.

    Match is replayed from its start on resume, so the absences are set rather
    than appended: the earlier pass's are dropped first.
    """
    kept = [
        move
        for move in await _pending_moves_of_run(connection, run_id)
        if not is_absence(move)
    ]
    await connection.execute(
        "UPDATE runs SET pending_moves = %s WHERE id = %s",
        (Jsonb(kept + absences), run_id),
    )


async def _pending_moves_of_run(
    connection: AsyncConnection,
    run_id: UUID,
) -> list[dict[str, Any]]:
    result = await connection.execute(
        "SELECT pending_moves FROM runs WHERE id = %s", (run_id,)
    )
    stored = await result.fetchone()
    return (stored["pending_moves"] if stored else []) or []


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
        "SELECT id, row_number, is_committed, " + ", ".join(CELL_NAMES)
        + " FROM register_rows "
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
) -> dict[str, set[str]]:
    result = await connection.execute(
        "SELECT register_row_id, source_file FROM citations "
        "WHERE register_row_id = ANY(%s)",
        (register_row_ids,),
    )
    cited: dict[str, set[str]] = {}
    for citation in await result.fetchall():
        cited.setdefault(str(citation["register_row_id"]), set()).add(
            citation["source_file"]
        )
    return cited
