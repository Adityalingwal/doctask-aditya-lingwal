from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.database import build_connection_pool
from app.examine.register_under_examination import register_under_examination
from app.extract.answer import CLIENT_REQUIREMENTS_DOCUMENT, MEETING_NOTES
from app.register.cells import (
    CELL_NAMES,
    IN_WRITING_NOT_KNOWN_YET,
    IN_WRITING_YES,
    STATUS_REQUESTED,
    TESTING_NOT_KNOWN_YET,
    WHAT_WAS_ASKED,
)
from app.review.review_queue import POSSIBLE_MATCH_DECISION
from app.runs.statuses import RUNNING
from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    match_answer,
    match_answer_existing_row,
    match_marker_for_batch_with,
    no_findings_answer,
    requirement_extraction_answer,
    write_meeting_note,
)
from tests.examine.answers import examine_answer, one_finding
from tests.examine.rules_files import rules_that_always_apply
from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)


COMMITTED_ROWS = 7
UNANSWERED_MATCHES = 6

MEETING_FILE = "meeting-notes-02-jul.md"
REQUIREMENTS_FILE = "client-requirements-v1.md"
THE_ASK = "a voice agent that answers support-line calls"
# The register reaches Examine as JSON, so a marker naming a cell value matches
# only a prompt that actually carried that value.
WRITTEN_DOWN_IN_THE_PROMPT = f'"in_writing": "{IN_WRITING_YES}"'


def test_examine_treats_an_unanswered_possible_match_as_the_existing_row() -> None:
    """A proposal waiting on a match answer is not a row of its own.

    Counted as one, a seven-row register read as thirteen and six findings
    named rows #8 to #13 — rows that were merged away the moment the person
    approved the matches, leaving the sentences pointing at nothing.
    """
    examined = asyncio.run(_examine_a_register_with_unanswered_matches())

    assert [row["row_number"] for row in examined] == list(
        range(1, COMMITTED_ROWS + 1)
    )


def test_examine_sees_the_candidate_with_the_proposals_written_down(
    tmp_path: Path,
) -> None:
    """The row is judged as it will stand after the match is approved.

    The proposal carries the requirements document that answers `Written
    down`. Judging the committed row without it would raise the written-
    requirement finding against evidence sitting in the very batch under
    review.
    """
    second_run = _a_requirements_document_matched_against_a_committed_row(tmp_path)

    assert second_run["examine"]["rows_examined"] == 1
    assert [
        decision for decision in second_run["decisions"]
        if decision["kind"] == "finding"
    ] == []


async def _examine_a_register_with_unanswered_matches() -> list[dict[str, Any]]:
    with temporary_database() as database_url:
        pool = build_connection_pool(database_url)
        await pool.open(wait=True)
        try:
            async with pool.connection() as connection:
                project_id, run_id = await _seed_the_register(connection)
                return await register_under_examination(
                    connection, project_id, run_id
                )
        finally:
            await pool.close()


async def _seed_the_register(connection: Any) -> tuple[UUID, UUID]:
    """Seven committed rows, and six proposals each asked about against one."""
    project_id, run_id = uuid4(), uuid4()
    await connection.execute(
        "INSERT INTO projects (id, name, source_folder_path) VALUES (%s, %s, %s)",
        (project_id, f"Helpline {project_id}", f"sample-projects/helpline-{project_id}"),
    )
    await connection.execute(
        "INSERT INTO runs (id, project_id, status) VALUES (%s, %s, %s)",
        (run_id, project_id, RUNNING),
    )
    committed = [
        await _insert_row(
            connection, project_id, run_id, number, IN_WRITING_NOT_KNOWN_YET, True
        )
        for number in range(1, COMMITTED_ROWS + 1)
    ]
    for offset in range(UNANSWERED_MATCHES):
        proposal = await _insert_row(
            connection,
            project_id,
            run_id,
            COMMITTED_ROWS + offset + 1,
            IN_WRITING_YES,
            False,
        )
        await connection.execute(
            "INSERT INTO decisions (id, run_id, kind, question, "
            "proposed_register_row_id, candidate_register_row_id) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                uuid4(),
                run_id,
                POSSIBLE_MATCH_DECISION,
                f"Is this the same ask as row #{offset + 1}?",
                proposal,
                committed[offset],
            ),
        )
    return project_id, run_id


async def _insert_row(
    connection: Any,
    project_id: UUID,
    run_id: UUID,
    row_number: int,
    in_writing: str,
    is_committed: bool,
) -> UUID:
    row_id = uuid4()
    await connection.execute(
        "INSERT INTO register_rows (id, project_id, "
        + ", ".join(CELL_NAMES)
        + ", fingerprint, row_number, proposed_by_run_id, is_committed) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            row_id,
            project_id,
            f"Requirement {row_number}.",
            in_writing,
            TESTING_NOT_KNOWN_YET,
            STATUS_REQUESTED,
            f"fingerprint-{row_number}",
            row_number,
            run_id,
            is_committed,
        ),
    )
    await connection.execute(
        "INSERT INTO citations (id, register_row_id, cell_name, source_file, "
        "source_place, source_words) VALUES (%s, %s, %s, %s, %s, %s)",
        (
            uuid4(),
            row_id,
            WHAT_WAS_ASKED,
            MEETING_FILE,
            "Discussion",
            f"the client asked for requirement {row_number}",
        ),
    )
    return row_id


def _a_requirements_document_matched_against_a_committed_row(
    tmp_path: Path,
) -> dict[str, Any]:
    """One committed row, then a batch stating the same ask in writing."""
    script_path = tmp_path / "script.json"
    waiting = tmp_path / "not-yet-written"
    waiting.mkdir()

    with temporary_project_folder("assumed-match") as (folder, folder_path):
        spoken_quote = write_meeting_note(folder, MEETING_FILE, THE_ASK)
        written_quote = write_meeting_note(waiting, REQUIREMENTS_FILE, THE_ASK)
        write_script(
            script_path,
            {
                extract_marker(MEETING_FILE): requirement_extraction_answer(
                    THE_ASK, spoken_quote, MEETING_NOTES
                ),
                extract_marker(REQUIREMENTS_FILE): requirement_extraction_answer(
                    THE_ASK, written_quote, CLIENT_REQUIREMENTS_DOCUMENT
                ),
                match_marker_for_batch_with(MEETING_FILE): match_answer(1),
                # The second run's Match names the committed row, which is
                # downgraded into the possible-match question this test leaves
                # unanswered while Examine runs.
                match_marker_for_batch_with(
                    REQUIREMENTS_FILE
                ): match_answer_existing_row(1),
                WRITTEN_DOWN_IN_THE_PROMPT: no_findings_answer(),
                examine_marker(): examine_answer([one_finding(row_number=1)]),
            },
        )
        with temporary_database() as database_url:
            application = ApplicationProcess(
                database_url=database_url,
                script_path=script_path,
                call_log_path=tmp_path / "model-calls.jsonl",
                rules_config_path=rules_that_always_apply(tmp_path),
            )
            application.start()
            try:
                with application.client() as client:
                    project_id = client.post(
                        "/projects", json={"source_folder_path": folder_path}
                    ).json()["project_id"]
                    first = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    wait_for_run_status(client, first, "needs review")
                    approve_every_decision_and_finish_review(client, first)
                    wait_for_run_status(client, first, "done")

                    shutil.copy(
                        waiting / REQUIREMENTS_FILE, folder / REQUIREMENTS_FILE
                    )
                    second = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    return wait_for_run_status(client, second, "needs review")
            finally:
                application.stop()
