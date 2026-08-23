from __future__ import annotations

from typing import Any, NamedTuple
from uuid import UUID

from psycopg import AsyncConnection

from app.examine.read_findings import findings_of_run
from app.register.audit_entries import write_attachment, write_cell_change
from app.register.cells import (
    CELL_NAMES,
    IN_WRITING,
    fingerprint_of_cells,
    in_writing_says_yes,
)
from app.register.move_rows import apply_moves
from app.review.review_queue import (
    APPROVED,
    POSSIBLE_MATCH_DECISION,
    decisions_of_run,
)


class CommitResult(NamedTuple):
    committed_row_numbers: list[int]
    merged_row_numbers: list[int]
    moved_row_numbers: list[int]


async def commit_register(
    connection: AsyncConnection,
    run_id: UUID,
) -> CommitResult:
    """Settle this run's proposals and write their history.

    The caller runs this inside one transaction: rows, fingerprints and audit
    history become permanent together or not at all, because a register
    committed without its history would be lying about itself. Nothing is
    copied anywhere — every reader reads the register live from
    `register_rows`.
    """
    merged_row_numbers = await _merge_approved_matches(connection, run_id)
    document_id_by_file = await _documents_of_run(connection, run_id)
    # After the merges, so a move lands on the row an approved merge sent its
    # evidence to; before the proposals below, so a row created and moved in
    # one batch is committed with the cells the move left it holding.
    # The absences Match worked out travel in the same list and are written
    # here too, after the observations' moves on each row, so a row proposed
    # in this batch is born holding `Not mentioned` rather than gaining it a
    # line later in its own history.
    moved_row_numbers = await apply_moves(connection, run_id, document_id_by_file)

    proposals = await connection.execute(
        "SELECT id, row_number, " + ", ".join(CELL_NAMES) + " FROM register_rows "
        "WHERE proposed_by_run_id = %s AND NOT is_committed "
        "AND merged_into_register_row_id IS NULL ORDER BY row_number",
        (run_id,),
    )
    committed_row_numbers: list[int] = []

    for row in await proposals.fetchall():
        citations = await _citations_of_row(connection, row["id"])
        if not citations:
            # A row without a source citation is an unsupported claim and must
            # never reach the register.
            raise RuntimeError(
                f"Register row #{row['row_number']} carries no citation and "
                "cannot be committed — every committed row states what a "
                "document said and names where it said it. Re-run the batch so "
                "the row is proposed with its evidence."
            )

        cells = {name: row[name] for name in CELL_NAMES}
        await connection.execute(
            "UPDATE register_rows SET is_committed = true, fingerprint = %s "
            "WHERE id = %s",
            (fingerprint_of_cells(cells), row["id"]),
        )
        await _write_audit_entries(
            connection,
            row["id"],
            cells,
            citations,
            run_id,
            document_id_by_file,
        )
        committed_row_numbers.append(row["row_number"])

    await _write_attachment_audit(connection, run_id)
    return CommitResult(
        committed_row_numbers=committed_row_numbers,
        merged_row_numbers=merged_row_numbers,
        moved_row_numbers=moved_row_numbers,
    )


async def _merge_approved_matches(
    connection: AsyncConnection,
    run_id: UUID,
) -> list[int]:
    """Approving a possible match moves the new evidence onto the existing row.

    The proposal itself is kept uncommitted rather than deleted, so the decision
    that settled it still points at what the Delivery Owner was shown. It
    records the row its evidence went into, which is both why it is never
    committed and where a reader is sent to find that evidence.
    """
    merged_row_numbers: list[int] = []
    for decision in await decisions_of_run(connection, run_id):
        if decision["kind"] != POSSIBLE_MATCH_DECISION:
            continue
        if decision["outcome"] != APPROVED:
            continue
        lands_on = await _the_row_a_merge_lands_on(
            connection, decision["candidate_register_row_id"]
        )
        proposal_id = decision["proposed_register_row_id"]
        # Before the citations move, so a cell replaced here drops the citation
        # that supported its old value while the arriving one is still to come.
        await _bring_cells_up_to_the_new_evidence(
            connection, lands_on, proposal_id, run_id
        )
        await connection.execute(
            "UPDATE citations SET register_row_id = %s WHERE register_row_id = %s",
            (lands_on, proposal_id),
        )
        merged = await connection.execute(
            "UPDATE register_rows SET merged_into_register_row_id = %s "
            "WHERE id = %s RETURNING row_number",
            (lands_on, proposal_id),
        )
        # A row already merged into this proposal is re-pointed at the same
        # place, so no marker is ever two hops from the row holding the
        # evidence. Decisions are settled in no fixed order, and every reader
        # of this column follows it exactly once.
        await connection.execute(
            "UPDATE register_rows SET merged_into_register_row_id = %s "
            "WHERE merged_into_register_row_id = %s",
            (lands_on, proposal_id),
        )
        merged_row = await merged.fetchone()
        if merged_row is not None:
            merged_row_numbers.append(merged_row["row_number"])
    return merged_row_numbers


async def _bring_cells_up_to_the_new_evidence(
    connection: AsyncConnection,
    survivor_id: UUID,
    proposal_id: UUID,
    run_id: UUID,
) -> None:
    """Move the surviving row's cells to what the arriving evidence supports.

    A merge attaches the proposal's citations to the row that survives. A cell
    saying the ask is not written down in a file the row now cites is
    contradicted by the row's own evidence — and nothing else in Commit looks
    at that cell again.
    """
    survivor = await _cells_of(connection, survivor_id)
    proposal = await _cells_of(connection, proposal_id)
    if survivor is None or proposal is None:
        return

    changed: dict[str, str] = {}
    if in_writing_says_yes(proposal[IN_WRITING]) and not in_writing_says_yes(
        survivor[IN_WRITING]
    ):
        changed[IN_WRITING] = proposal[IN_WRITING]

    for cell_name, value in changed.items():
        await connection.execute(
            f"UPDATE register_rows SET {cell_name} = %s WHERE id = %s",
            (value, survivor_id),
        )
        # `Written down` holds one claim about one document, so the citation
        # behind the sentence it no longer says goes with that sentence. Only
        # `Status` rests on more than one claim, and no merge moves it.
        await connection.execute(
            "DELETE FROM citations WHERE register_row_id = %s AND cell_name = %s",
            (survivor_id, cell_name),
        )
        if survivor["is_committed"]:
            # A row this run proposed has its whole first history written when
            # it is committed; a row already in the register gets its
            # before-and-after here, the way an approved move does.
            await write_cell_change(
                connection,
                survivor_id,
                cell_name,
                survivor[cell_name],
                value,
                run_id,
                None,
            )

    if changed and survivor["is_committed"]:
        settled = await _cells_of(connection, survivor_id)
        await connection.execute(
            "UPDATE register_rows SET fingerprint = %s WHERE id = %s",
            (
                fingerprint_of_cells({name: settled[name] for name in CELL_NAMES}),
                survivor_id,
            ),
        )


async def _cells_of(
    connection: AsyncConnection,
    register_row_id: UUID,
) -> dict[str, Any] | None:
    result = await connection.execute(
        "SELECT id, is_committed, " + ", ".join(CELL_NAMES) + " FROM register_rows "
        "WHERE id = %s",
        (register_row_id,),
    )
    return await result.fetchone()


async def _the_row_a_merge_lands_on(
    connection: AsyncConnection,
    register_row_id: UUID,
) -> UUID:
    """The row this evidence ends up on, following a merge already approved.

    One batch can propose a row, ask about merging a second row into it, and
    ask about merging that first row into a committed one. The two answers are
    settled in no fixed order, so the candidate may itself have been merged
    away a moment ago — and evidence left on a row Commit never commits is
    evidence lost.
    """
    result = await connection.execute(
        "SELECT merged_into_register_row_id FROM register_rows WHERE id = %s",
        (register_row_id,),
    )
    row = await result.fetchone()
    if row is None or row["merged_into_register_row_id"] is None:
        return register_row_id
    return await _the_row_a_merge_lands_on(
        connection, row["merged_into_register_row_id"]
    )


async def _write_attachment_audit(
    connection: AsyncConnection,
    run_id: UUID,
) -> None:
    """Record each approved finding as attached to its row, naming no cell.

    A finding is an attachment, not a cell change: it says nothing about what
    any of the four cells holds, which is why the row's fingerprint does not
    move when one arrives.
    """
    for finding in await findings_of_run(connection, run_id, approved_only=True):
        await write_attachment(
            connection,
            finding["register_row_id"],
            f"{finding['rule_id']} — {finding['issue']}",
            run_id,
        )


async def _documents_of_run(
    connection: AsyncConnection,
    run_id: UUID,
) -> dict[str, UUID]:
    result = await connection.execute(
        "SELECT id, source_path FROM documents WHERE run_id = %s",
        (run_id,),
    )
    return {row["source_path"]: row["id"] for row in await result.fetchall()}


async def _citations_of_row(
    connection: AsyncConnection,
    register_row_id: UUID,
) -> list[dict[str, Any]]:
    result = await connection.execute(
        "SELECT cell_name, source_file FROM citations WHERE register_row_id = %s",
        (register_row_id,),
    )
    return list(await result.fetchall())


async def _write_audit_entries(
    connection: AsyncConnection,
    register_row_id: UUID,
    cells: dict[str, str],
    citations: list[dict[str, Any]],
    run_id: UUID,
    document_id_by_file: dict[str, UUID],
) -> None:
    source_file_by_cell = {
        citation["cell_name"]: citation["source_file"] for citation in citations
    }
    for cell_name, new_value in cells.items():
        source_file = source_file_by_cell.get(cell_name)
        await write_cell_change(
            connection,
            register_row_id,
            cell_name,
            None,
            new_value,
            run_id,
            document_id_by_file.get(source_file) if source_file else None,
        )
