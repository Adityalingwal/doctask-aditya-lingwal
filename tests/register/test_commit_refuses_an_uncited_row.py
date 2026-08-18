from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest
from psycopg import AsyncConnection

from app.database import build_connection_pool
from app.register.cells import CELL_NAMES
from app.register.commit_register import commit_register
from app.register.propose_rows import UNSET_FINGERPRINT
from app.runs.statuses import RUNNING
from tests.runs.application import temporary_database


REQUIREMENT = "Send an email to the operations team on intake form submit."


def test_a_row_without_a_citation_is_still_refused_at_commit() -> None:
    """The refusal outlives the deleted rule that used to name it.

    Examine's code check raised a finding while the row still reached the
    register; Commit refuses outright, so nothing is left unguarded by the
    check's removal — and the message must state its own reason rather than
    cite a rule id that no longer exists.
    """
    with pytest.raises(RuntimeError) as refused:
        asyncio.run(_commit_a_row_citing_nothing())

    message = str(refused.value)
    assert "carries no citation" in message
    assert "Re-run the batch" in message
    assert "D1" not in message


async def _commit_a_row_citing_nothing() -> None:
    with temporary_database() as database_url:
        pool = build_connection_pool(database_url)
        await pool.open(wait=True)
        try:
            async with pool.connection() as connection:
                project, run_id = await _project_with_a_running_run(connection)
                await _insert_proposed_row(
                    connection, project["id"], run_id
                )
                await commit_register(connection, run_id)
        finally:
            await pool.close()


async def _project_with_a_running_run(
    connection: AsyncConnection,
) -> tuple[dict[str, object], UUID]:
    project_id, run_id = uuid4(), uuid4()
    await connection.execute(
        "INSERT INTO projects (id, name, source_folder_path) VALUES (%s, %s, %s)",
        (project_id, "Uncited intake portal", "sample-projects/uncited-portal"),
    )
    await connection.execute(
        "INSERT INTO runs (id, project_id, status) VALUES (%s, %s, %s)",
        (run_id, project_id, RUNNING),
    )
    return {"id": project_id, "name": "Uncited intake portal"}, run_id


async def _insert_proposed_row(
    connection: AsyncConnection,
    project_id: UUID,
    run_id: UUID,
) -> None:
    columns = ", ".join(CELL_NAMES)
    placeholders = ", ".join(["%s"] * len(CELL_NAMES))
    await connection.execute(
        f"INSERT INTO register_rows (id, project_id, {columns}, fingerprint, "
        "row_number, proposed_by_run_id, is_committed) VALUES "
        f"(%s, %s, {placeholders}, %s, 1, %s, false)",
        (
            uuid4(),
            project_id,
            *_cells_of_a_row_nobody_has_looked_at(),
            UNSET_FINGERPRINT,
            run_id,
        ),
    )


def _cells_of_a_row_nobody_has_looked_at() -> tuple[str, ...]:
    """Whatever the cell list holds today; only the missing citation is the point."""
    written = {
        "what_was_asked": REQUIREMENT,
        "status": "Nothing said yet",
    }
    return tuple(written.get(name, "Not known yet.") for name in CELL_NAMES)
