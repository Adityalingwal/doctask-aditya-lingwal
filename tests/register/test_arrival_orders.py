from __future__ import annotations

from pathlib import Path
from typing import Any, NamedTuple

from sqlalchemy import create_engine, text

from app.register.cells import CELL_NAMES
from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    handover_answer,
    feedback_extraction_answer,
    match_answer,
    match_marker,
    no_findings_answer,
    observation_answer_of,
    observation_marker,
    several_requirements_answer,
    write_document_stating,
)
from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)


MEETING_NOTE = "meeting-notes-10-mar.md"
HANDOVER = "handover-summary-30-mar.md"
TESTING_FEEDBACK = "testing-feedback-25-mar.md"

ASK = "an email notification to the operations team on submit"
ASK_QUOTE = "The client asked for an email notification to the operations team."
HANDOVER_QUOTE = "The email notification was handed over to the client's team."
TESTING_QUOTE = "The email notification reaches the operations team every time."
HANDED_OVER_SUMMARY = "the email notification was handed over"
TESTING_SUMMARY = "the notification reaches the team"

DOCUMENT_LINES = {
    MEETING_NOTE: ASK_QUOTE,
    HANDOVER: HANDOVER_QUOTE,
    TESTING_FEEDBACK: TESTING_QUOTE,
}
ONE_DOCUMENT_PER_RUN_SCRIPT = {
    extract_marker(MEETING_NOTE): several_requirements_answer(
        [(ASK, ASK_QUOTE)], "meeting notes"
    ),
    extract_marker(HANDOVER): handover_answer([(HANDED_OVER_SUMMARY, HANDOVER_QUOTE)]),
    extract_marker(TESTING_FEEDBACK): feedback_extraction_answer(
        [(TESTING_SUMMARY, "Passed", TESTING_QUOTE)]
    ),
    match_marker(): match_answer(1),
    observation_marker(): observation_answer_of([1]),
    examine_marker(): no_findings_answer(),
}


class RunResult(NamedTuple):
    """One finished run: the committed register it left, cells and citations."""

    cells: dict[int, dict[str, str]]
    citations: dict[int, dict[str, list[tuple[str, str]]]]


def test_testing_passing_moves_a_handed_over_row_to_done(tmp_path: Path) -> None:
    """The three states are distinct claims, not shades of one.

    Nobody has looked; we say we built it; testing confirmed it. A run that
    read a handover and left the row where it was would be a run doing nothing.
    """
    asked, handed_over, tested = drive_batches(
        tmp_path,
        "handed-over",
        [[MEETING_NOTE], [HANDOVER], [TESTING_FEEDBACK]],
        ONE_DOCUMENT_PER_RUN_SCRIPT,
    )

    assert asked.cells[1]["status"] == "No evidence yet"
    assert handed_over.cells[1]["status"] == "Handed over"
    assert tested.cells[1]["status"] == "Done"
    assert tested.cells[1]["what_testing_found"] == TESTING_SUMMARY


def drive_batches(
    tmp_path: Path,
    name_hint: str,
    batches: list[list[str]],
    answers: dict[str, Any],
) -> list[RunResult]:
    """One project run once per batch, approving everything each time.

    The files of a batch reach the folder only when that batch's run starts, so
    a document really does arrive after the register it lands on was committed.
    """
    results: list[RunResult] = []
    with temporary_project_folder(name_hint) as (folder, folder_path):
        script_path = tmp_path / "script.json"
        write_script(script_path, answers)

        with temporary_database() as database_url:
            application = ApplicationProcess(
                database_url=database_url,
                script_path=script_path,
                call_log_path=tmp_path / "model-calls.jsonl",
            )
            application.start()
            try:
                with application.client() as client:
                    project_id = client.post(
                        "/projects", json={"source_folder_path": folder_path}
                    ).json()["project_id"]
                    for batch in batches:
                        for source_file in batch:
                            write_document_stating(
                                folder,
                                source_file,
                                "10 March 2026",
                                [DOCUMENT_LINES[source_file]],
                            )
                        run_id = client.post(
                            "/runs", json={"project_id": project_id}
                        ).json()["run_id"]
                        wait_for_run_status(client, run_id, "needs review")
                        approve_every_decision_and_finish_review(client, run_id)
                        wait_for_run_status(client, run_id, "done")
                        results.append(_committed_register(database_url, project_id))
            finally:
                application.stop()
    return results


def _committed_register(database_url: str, project_id: str) -> RunResult:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            rows = (
                connection.execute(
                    text(
                        "SELECT id, row_number, " + ", ".join(CELL_NAMES) + " "
                        "FROM register_rows WHERE project_id = :project_id "
                        "AND is_committed ORDER BY row_number"
                    ),
                    {"project_id": project_id},
                )
                .mappings()
                .all()
            )
            cited = (
                connection.execute(
                    text(
                        "SELECT citations.register_row_id, citations.cell_name, "
                        "citations.source_file, citations.source_place "
                        "FROM citations JOIN register_rows "
                        "ON register_rows.id = citations.register_row_id "
                        "WHERE register_rows.project_id = :project_id "
                        "AND register_rows.is_committed "
                        "ORDER BY citations.source_file"
                    ),
                    {"project_id": project_id},
                )
                .mappings()
                .all()
            )
    finally:
        engine.dispose()

    number_of = {row["id"]: row["row_number"] for row in rows}
    citations: dict[int, dict[str, list[tuple[str, str]]]] = {}
    for citation in cited:
        row_number = number_of[citation["register_row_id"]]
        citations.setdefault(row_number, {}).setdefault(
            citation["cell_name"], []
        ).append((citation["source_file"], citation["source_place"]))
    return RunResult(
        cells={
            row["row_number"]: {name: row[name] for name in CELL_NAMES}
            for row in rows
        },
        citations=citations,
    )
