from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID, uuid4

from psycopg import AsyncConnection

from app.database import build_connection_pool
from app.examine.deliverable_checks import deliverable_findings
from app.examine.register_under_examination import register_under_examination
from app.register.cells import WHAT_TESTING_FOUND, WHAT_WAS_ASKED
from app.runs.statuses import RUNNING
from tests.runs.application import temporary_database


REQUIREMENT = "Send an email to the operations team on intake form submit."
TESTING_OUTCOME = "The email arrived for every submission tested."


def test_a_register_row_citing_no_source_is_asked_about_under_d1() -> None:
    found = _examine_one_row("No evidence yet", cited_cells=())

    assert [finding["rule_id"] for finding in found] == ["D1"]
    assert "cites no source" in found[0]["issue"]
    assert found[0]["question"].endswith("Attach this finding to the row?")


def test_a_done_row_without_a_testing_outcome_is_asked_about_under_d2() -> None:
    found = _examine_one_row("Done", cited_cells=(WHAT_WAS_ASKED,))

    assert [finding["rule_id"] for finding in found] == ["D2"]
    assert "no testing outcome was read" in found[0]["issue"]


def test_a_cited_done_row_with_a_testing_outcome_raises_no_finding() -> None:
    found = _examine_one_row(
        "Done",
        cited_cells=(WHAT_WAS_ASKED, WHAT_TESTING_FOUND),
    )

    assert found == []


def _examine_one_row(
    status: str,
    cited_cells: tuple[str, ...],
) -> list[dict[str, Any]]:
    return asyncio.run(_deliverable_findings_over(status, cited_cells))


async def _deliverable_findings_over(
    status: str,
    cited_cells: tuple[str, ...],
) -> list[dict[str, Any]]:
    with temporary_database() as database_url:
        pool = build_connection_pool(database_url)
        await pool.open(wait=True)
        try:
            async with pool.connection() as connection:
                project_id, run_id = await _project_with_a_running_run(connection)
                await _insert_committed_row(
                    connection, project_id, run_id, status, cited_cells
                )
                rows = await register_under_examination(
                    connection, project_id, run_id
                )
                return deliverable_findings(rows)
        finally:
            await pool.close()


async def _project_with_a_running_run(
    connection: AsyncConnection,
) -> tuple[UUID, UUID]:
    project_id, run_id = uuid4(), uuid4()
    await connection.execute(
        "INSERT INTO projects (id, name, source_folder_path) VALUES (%s, %s, %s)",
        (project_id, "Checked intake portal", "/projects/intake-portal"),
    )
    await connection.execute(
        "INSERT INTO runs (id, project_id, status) VALUES (%s, %s, %s)",
        (run_id, project_id, RUNNING),
    )
    return project_id, run_id


async def _insert_committed_row(
    connection: AsyncConnection,
    project_id: UUID,
    run_id: UUID,
    status: str,
    cited_cells: tuple[str, ...],
) -> None:
    row_id = uuid4()
    await connection.execute(
        "INSERT INTO register_rows (id, project_id, what_was_asked, in_writing, "
        "what_testing_found, status, blocked_on, first_seen, last_moved, "
        "fingerprint, row_number, proposed_by_run_id, is_committed) VALUES "
        "(%s, %s, %s, 'Yes', %s, %s, 'Not blocked', '10 March 2026', "
        "'10 March 2026', 'fingerprint', 1, %s, true)",
        (row_id, project_id, REQUIREMENT, TESTING_OUTCOME, status, run_id),
    )
    for cell_name in cited_cells:
        await connection.execute(
            "INSERT INTO citations (id, register_row_id, cell_name, source_file, "
            "source_place, source_words) VALUES (%s, %s, %s, "
            "'client-requirements-v1.md', 'Requirements', %s)",
            (uuid4(), row_id, cell_name, REQUIREMENT),
        )
