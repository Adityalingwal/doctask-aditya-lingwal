from __future__ import annotations

from typing import Any, NamedTuple
from uuid import UUID

from psycopg import AsyncConnection

from app.register.cells import CELL_NAMES


async def register_under_examination(
    connection: AsyncConnection,
    project_id: UUID,
    run_id: UUID,
) -> list[dict[str, Any]]:
    """The register as this run leaves it: committed rows plus its own proposals.

    A proposal is examined before it is committed, because a finding a person
    only sees after the export has been approved is a finding raised too late.
    """
    result = await connection.execute(
        "SELECT id, row_number, " + ", ".join(CELL_NAMES) + " FROM register_rows "
        "WHERE project_id = %s AND (is_committed OR proposed_by_run_id = %s) "
        "AND merged_into_register_row_id IS NULL ORDER BY row_number",
        (project_id, run_id),
    )
    rows = list(await result.fetchall())
    if not rows:
        return []

    cited_cells = await _cited_cells_by_row(
        connection, [row["id"] for row in rows]
    )
    moved = await _cells_this_run_moves(connection, run_id)
    return [
        {
            "id": row["id"],
            "row_number": row["row_number"],
            "cells": {name: row[name] for name in CELL_NAMES}
            | moved.values_by_row.get(str(row["id"]), {}),
            "cited_cells": cited_cells.get(row["id"], frozenset())
            | moved.cited_cells_by_row.get(str(row["id"]), frozenset()),
        }
        for row in rows
    ]


class PendingMoves(NamedTuple):
    values_by_row: dict[str, dict[str, str]]
    cited_cells_by_row: dict[str, frozenset[str]]


async def _cells_this_run_moves(
    connection: AsyncConnection,
    run_id: UUID,
) -> PendingMoves:
    """What this run's moves will leave each row holding, once Commit runs.

    A move is not written to the row until Commit, so a rule judging the
    stored cells alone would raise a finding against evidence this very batch
    supplied — and a finding a person only sees after approving the export is
    raised too late.

    The citations travel with the values for the same reason. A rule that saw
    `status` reach `Done` but not the testing citation that moved it there
    would report the row as Done with no testing outcome — a finding against
    the very evidence in front of it.
    """
    result = await connection.execute(
        "SELECT pending_moves FROM runs WHERE id = %s", (run_id,)
    )
    stored = await result.fetchone()
    values: dict[str, dict[str, str]] = {}
    cited: dict[str, set[str]] = {}
    for move in (stored["pending_moves"] if stored else []) or []:
        row_id = move["register_row_id"]
        values.setdefault(row_id, {})[move["cell"]] = move["value"]
        if move["citations"]:
            cited.setdefault(row_id, set()).add(move["cell"])
    return PendingMoves(
        values_by_row=values,
        cited_cells_by_row={
            row_id: frozenset(cells) for row_id, cells in cited.items()
        },
    )


async def _cited_cells_by_row(
    connection: AsyncConnection,
    register_row_ids: list[UUID],
) -> dict[UUID, frozenset[str]]:
    result = await connection.execute(
        "SELECT register_row_id, cell_name FROM citations "
        "WHERE register_row_id = ANY(%s)",
        (register_row_ids,),
    )
    cited: dict[UUID, set[str]] = {}
    for citation in await result.fetchall():
        cited.setdefault(citation["register_row_id"], set()).add(
            citation["cell_name"]
        )
    return {row_id: frozenset(cells) for row_id, cells in cited.items()}
