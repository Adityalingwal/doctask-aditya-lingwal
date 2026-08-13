from __future__ import annotations

from uuid import UUID, uuid4

from psycopg import AsyncConnection


CELL_CHANGE_EVENT = "cell change"
ATTACHMENT_EVENT = "attachment"


async def write_cell_change(
    connection: AsyncConnection,
    register_row_id: UUID,
    cell_name: str,
    old_value: str | None,
    new_value: str,
    run_id: UUID,
    source_document_id: UUID | None,
) -> None:
    """Record what one cell held before and what it holds now."""
    await connection.execute(
        "INSERT INTO audit (id, register_row_id, cell_name, event_kind, "
        "old_value, new_value, run_id, source_document_id) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (
            uuid4(),
            register_row_id,
            cell_name,
            CELL_CHANGE_EVENT,
            old_value,
            new_value,
            run_id,
            source_document_id,
        ),
    )


async def write_attachment(
    connection: AsyncConnection,
    register_row_id: UUID,
    new_value: str,
    run_id: UUID,
) -> None:
    """Record something attached to a row, naming no cell because it moved none."""
    await connection.execute(
        "INSERT INTO audit (id, register_row_id, cell_name, event_kind, "
        "old_value, new_value, run_id, source_document_id) "
        "VALUES (%s, %s, NULL, %s, NULL, %s, %s, NULL)",
        (uuid4(), register_row_id, ATTACHMENT_EVENT, new_value, run_id),
    )
