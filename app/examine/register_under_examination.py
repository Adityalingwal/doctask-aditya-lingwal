from __future__ import annotations

from typing import Any
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
    return [
        {
            "id": row["id"],
            "row_number": row["row_number"],
            "cells": {name: row[name] for name in CELL_NAMES},
            "cited_cells": cited_cells.get(row["id"], frozenset()),
        }
        for row in rows
    ]


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
