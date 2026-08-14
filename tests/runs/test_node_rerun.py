from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from psycopg import AsyncConnection

from app.database import build_connection_pool
from app.examine.found_issue import finding_on_row
from app.examine.record_findings import record_findings
from app.ingest.collect_batch import collect_batch
from app.match.match_requirements import NEW_ROW, POSSIBLE_MATCH
from app.register.propose_rows import propose_rows
from app.runs.statuses import RUNNING
from tests.runs.application import temporary_database
from tests.documents.register_documents import write_meeting_note


MARKDOWN_ONLY = frozenset({".md"})
PAGE_LIMIT = 20
COMMITTED_ROW_NUMBER = 1
COMMITTED_REQUIREMENT = "Send a notification when the intake form is submitted."


def test_ingest_rerun_does_not_duplicate_documents(tmp_path: Path) -> None:
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    write_meeting_note(source_folder, "doc-1.md", "an email on form submit")
    write_meeting_note(source_folder, "doc-2.md", "the same over WhatsApp")

    collected = asyncio.run(_collect_batch_twice(source_folder))

    # Both halves matter: no second row for a document, and no document lost
    # out of the batch Extract is about to read.
    assert collected["written"] == 2
    assert collected["first_batch"] == collected["second_batch"]
    assert len(collected["second_batch"]) == 2


def test_match_rerun_does_not_duplicate_proposed_rows(tmp_path: Path) -> None:
    proposed = asyncio.run(_propose_rows_twice())

    assert proposed["uncommitted_rows"] == 2
    assert proposed["citations"] == 2
    assert proposed["decisions"] == 1
    assert proposed["row_numbers"] == [2, 3]
    # The committed row is not this run's to clear.
    assert proposed["committed_rows"] == 1


def test_examine_rerun_does_not_duplicate_findings_for_the_same_run() -> None:
    recorded = asyncio.run(_record_findings_twice())

    # Re-entering Examine after a crash replaces what this run found; it never
    # asks the Delivery Owner the same question a second time.
    assert recorded["findings"] == 1
    assert recorded["decisions"] == 1


async def _record_findings_twice() -> dict[str, Any]:
    with temporary_database() as database_url:
        pool = build_connection_pool(database_url)
        await pool.open(wait=True)
        try:
            async with pool.connection() as connection:
                project_id, run_id = await _project_with_a_running_run(connection)
                await _insert_committed_row(connection, project_id, run_id)
                committed = await connection.execute(
                    "SELECT id, row_number, what_was_asked FROM register_rows "
                    "WHERE proposed_by_run_id = %s",
                    (run_id,),
                )
                row = await committed.fetchone()
                found = [
                    finding_on_row(
                        "R1",
                        "Anything built must have a written requirement.",
                        {
                            "id": row["id"],
                            "row_number": row["row_number"],
                            "cells": {"what_was_asked": row["what_was_asked"]},
                        },
                        "No client requirements document states this in writing.",
                        f"Row #{row['row_number']} cites a meeting note only.",
                    )
                ]
                await record_findings(connection, run_id, found)
                await record_findings(connection, run_id, found)
                return await _finding_counts(connection, run_id)
        finally:
            await pool.close()


async def _finding_counts(
    connection: AsyncConnection,
    run_id: UUID,
) -> dict[str, Any]:
    findings = await connection.execute(
        "SELECT count(*) AS written FROM findings WHERE run_id = %s",
        (run_id,),
    )
    decisions = await connection.execute(
        "SELECT count(*) AS written FROM decisions WHERE run_id = %s "
        "AND kind = 'finding'",
        (run_id,),
    )
    return {
        "findings": (await findings.fetchone())["written"],
        "decisions": (await decisions.fetchone())["written"],
    }


async def _collect_batch_twice(source_folder: Path) -> dict[str, Any]:
    with temporary_database() as database_url:
        pool = build_connection_pool(database_url)
        await pool.open(wait=True)
        try:
            async with pool.connection() as connection:
                project_id, run_id = await _project_with_a_running_run(connection)
                first = await collect_batch(
                    connection,
                    run_id,
                    project_id,
                    source_folder,
                    MARKDOWN_ONLY,
                    PAGE_LIMIT,
                )
                second = await collect_batch(
                    connection,
                    run_id,
                    project_id,
                    source_folder,
                    MARKDOWN_ONLY,
                    PAGE_LIMIT,
                )
                written = await connection.execute(
                    "SELECT count(*) AS written FROM documents WHERE run_id = %s",
                    (run_id,),
                )
                return {
                    "first_batch": sorted(first.document_ids),
                    "second_batch": sorted(second.document_ids),
                    "written": (await written.fetchone())["written"],
                }
        finally:
            await pool.close()


async def _propose_rows_twice() -> dict[str, Any]:
    requirements = [
        _requirement("the intake form sends an email to operations", "doc-1.md"),
        _requirement("old intake records can be searched", "doc-2.md"),
    ]
    with temporary_database() as database_url:
        pool = build_connection_pool(database_url)
        await pool.open(wait=True)
        try:
            async with pool.connection() as connection:
                project_id, run_id = await _project_with_a_running_run(connection)
                await _insert_committed_row(connection, project_id, run_id)
                outcomes = {
                    0: (POSSIBLE_MATCH, COMMITTED_ROW_NUMBER),
                    1: (NEW_ROW, None),
                }
                await propose_rows(
                    connection, run_id, project_id, requirements, outcomes
                )
                await propose_rows(
                    connection, run_id, project_id, requirements, outcomes
                )
                return await _register_counts(connection, run_id)
        finally:
            await pool.close()


def _requirement(summary: str, source_file: str) -> dict[str, Any]:
    return {
        "summary": summary,
        "source_file": source_file,
        "place": "Discussion",
        "source_words": f"The client asked for {summary}.",
        "document_type": "meeting notes",
        "document_date": None,
    }


async def _project_with_a_running_run(
    connection: AsyncConnection,
) -> tuple[UUID, UUID]:
    project_id, run_id = uuid4(), uuid4()
    await connection.execute(
        "INSERT INTO projects (id, name, source_folder_path) VALUES (%s, %s, %s)",
        (project_id, "Re-run intake portal", "/projects/intake-portal"),
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
) -> None:
    await connection.execute(
        "INSERT INTO register_rows (id, project_id, what_was_asked, in_writing, "
        "what_testing_found, status, blocked_on, first_seen, last_moved, "
        "fingerprint, row_number, proposed_by_run_id, is_committed) VALUES "
        "(%s, %s, %s, 'Yes', 'Not known yet', 'No evidence yet', "
        "'Not known yet', '10 March 2026', '10 March 2026', 'fingerprint', "
        "%s, %s, true)",
        (
            uuid4(),
            project_id,
            COMMITTED_REQUIREMENT,
            COMMITTED_ROW_NUMBER,
            run_id,
        ),
    )


async def _register_counts(
    connection: AsyncConnection,
    run_id: UUID,
) -> dict[str, Any]:
    rows = await connection.execute(
        "SELECT row_number, is_committed FROM register_rows "
        "WHERE proposed_by_run_id = %s ORDER BY row_number",
        (run_id,),
    )
    written_rows = list(await rows.fetchall())
    citations = await connection.execute(
        "SELECT count(*) AS written FROM citations JOIN register_rows ON "
        "register_rows.id = citations.register_row_id "
        "WHERE register_rows.proposed_by_run_id = %s AND NOT is_committed",
        (run_id,),
    )
    decisions = await connection.execute(
        "SELECT count(*) AS written FROM decisions WHERE run_id = %s",
        (run_id,),
    )
    return {
        "uncommitted_rows": len([row for row in written_rows if not row["is_committed"]]),
        "row_numbers": [
            row["row_number"] for row in written_rows if not row["is_committed"]
        ],
        "committed_rows": len([row for row in written_rows if row["is_committed"]]),
        "citations": (await citations.fetchone())["written"],
        "decisions": (await decisions.fetchone())["written"],
    }
