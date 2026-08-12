from __future__ import annotations

from typing import Any, NamedTuple
from uuid import UUID, uuid4

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from app.register.cells import CELL_NAMES, fingerprint_of_cells
from app.register.export_register import build_export
from app.review.review_queue import (
    APPROVED,
    POSSIBLE_MATCH_DECISION,
    decisions_of_run,
)


class CommitResult(NamedTuple):
    committed_row_numbers: list[int]
    merged_row_numbers: list[int]
    export: dict[str, Any]


async def commit_register(
    connection: AsyncConnection,
    project: dict[str, Any],
    run_id: UUID,
    exported_at: str,
) -> CommitResult:
    """Settle this run's proposals, write their history, and produce the export.

    The caller runs this inside one transaction: rows, fingerprints, audit
    history and the export become permanent together or not at all, because a
    register committed without its history would be lying about itself.
    """
    merged_row_numbers = await _merge_approved_matches(connection, run_id)
    document_id_by_file = await _documents_of_run(connection, run_id)

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
            # D1: a row without a source citation is an unsupported claim and
            # must never reach the register.
            raise RuntimeError(
                f"Register row #{row['row_number']} carries no citation and "
                "cannot be committed — rule D1 requires every committed row to "
                "cite a source. Re-run the batch so the row is proposed with "
                "its evidence."
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

    export = await build_export(connection, project, run_id, exported_at)
    await connection.execute(
        "UPDATE runs SET export_json = %s WHERE id = %s",
        (Jsonb(export), run_id),
    )
    return CommitResult(
        committed_row_numbers=committed_row_numbers,
        merged_row_numbers=merged_row_numbers,
        export=export,
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
        await connection.execute(
            "UPDATE citations SET register_row_id = %s WHERE register_row_id = %s",
            (
                decision["candidate_register_row_id"],
                decision["proposed_register_row_id"],
            ),
        )
        merged = await connection.execute(
            "UPDATE register_rows SET merged_into_register_row_id = %s "
            "WHERE id = %s RETURNING row_number",
            (
                decision["candidate_register_row_id"],
                decision["proposed_register_row_id"],
            ),
        )
        merged_row = await merged.fetchone()
        if merged_row is not None:
            merged_row_numbers.append(merged_row["row_number"])
    return merged_row_numbers


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
        await connection.execute(
            "INSERT INTO audit (id, register_row_id, cell_name, old_value, "
            "new_value, run_id, source_document_id) "
            "VALUES (%s, %s, %s, NULL, %s, %s, %s)",
            (
                uuid4(),
                register_row_id,
                cell_name,
                new_value,
                run_id,
                document_id_by_file.get(source_file) if source_file else None,
            ),
        )
