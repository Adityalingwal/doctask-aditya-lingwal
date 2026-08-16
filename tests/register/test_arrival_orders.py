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
    match_answer_existing_row,
    match_answer_within_batch,
    match_marker,
    match_marker_against_an_empty_register,
    match_marker_for_batch_with,
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
REQUIREMENTS = "client-requirements-12-mar.md"
HANDOVER = "handover-summary-30-mar.md"
FIRST_TESTING = "testing-feedback-05-apr.md"
TESTING_FEEDBACK = "testing-feedback-25-mar.md"

ASK = "an email notification to the operations team on submit"
ASK_QUOTE = "The client asked for an email notification to the operations team."
WRITTEN_ASK = "an email to the operations team on every intake form submit"
WRITTEN_QUOTE = "An email notification to the operations team on every submit."
HANDOVER_QUOTE = "The email notification was handed over to the client's team."
TESTING_QUOTE = "The email notification reaches the operations team every time."
DEFECT_QUOTE = "The email notification goes to the wrong address."
HANDED_OVER_SUMMARY = "the email notification was handed over"
TESTING_SUMMARY = "the notification reaches the team"
DEFECT_SUMMARY = "the notification goes to the wrong address"

DOCUMENT_LINES = {
    MEETING_NOTE: ASK_QUOTE,
    REQUIREMENTS: WRITTEN_QUOTE,
    HANDOVER: HANDOVER_QUOTE,
    FIRST_TESTING: DEFECT_QUOTE,
    TESTING_FEEDBACK: TESTING_QUOTE,
}
EXTRACT_ANSWERS = {
    extract_marker(MEETING_NOTE): several_requirements_answer(
        [(ASK, ASK_QUOTE)], "meeting notes"
    ),
    extract_marker(REQUIREMENTS): several_requirements_answer(
        [(WRITTEN_ASK, WRITTEN_QUOTE)], "client requirements document"
    ),
    extract_marker(HANDOVER): handover_answer(
        [(HANDED_OVER_SUMMARY, HANDOVER_QUOTE)]
    ),
    extract_marker(FIRST_TESTING): feedback_extraction_answer(
        [(DEFECT_SUMMARY, "Defect", DEFECT_QUOTE)]
    ),
    extract_marker(TESTING_FEEDBACK): feedback_extraction_answer(
        [(TESTING_SUMMARY, "Passed", TESTING_QUOTE)]
    ),
}
ONE_DOCUMENT_PER_RUN_SCRIPT = EXTRACT_ANSWERS | {
    match_marker(): match_answer(1),
    observation_marker(): observation_answer_of([1]),
    examine_marker(): no_findings_answer(),
}
# The whole workflow, one document per run: the requirements document arrives
# after the row it restates is already committed, so Match answers it against
# the register rather than against the batch.
FOUR_RUNS_SCRIPT = EXTRACT_ANSWERS | {
    match_marker_against_an_empty_register(): match_answer(1),
    match_marker_for_batch_with(REQUIREMENTS): match_answer_existing_row(1),
    observation_marker(): observation_answer_of([1]),
    examine_marker(): no_findings_answer(),
}
# The same four documents arriving in two pairs.
TWO_PAIRED_RUNS_SCRIPT = EXTRACT_ANSWERS | {
    match_marker_against_an_empty_register(): match_answer_within_batch(
        [("new row", None, None), ("existing row", None, 0)]
    ),
    observation_marker(): observation_answer_of([1, 1]),
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


def test_the_handover_citation_survives_the_move_to_done(tmp_path: Path) -> None:
    """`Done` is built out of two claims, and both stay behind the cell.

    The handover says the work exists and testing says it behaves as asked.
    Replacing the citation would leave the register unable to show that a
    handover ever arrived.
    """
    _, handed_over, tested = drive_batches(
        tmp_path,
        "handover-citation",
        [[MEETING_NOTE], [HANDOVER], [TESTING_FEEDBACK]],
        ONE_DOCUMENT_PER_RUN_SCRIPT,
    )

    assert _cited_files(handed_over, 1, "status") == {HANDOVER}
    assert _cited_files(tested, 1, "status") == {HANDOVER, TESTING_FEEDBACK}


def test_a_superseded_testing_verdict_loses_its_citation(tmp_path: Path) -> None:
    """A verdict the cell no longer holds proves something the cell denies."""
    _, _, defective, passed = drive_batches(
        tmp_path,
        "superseded-verdict",
        [[MEETING_NOTE], [HANDOVER], [FIRST_TESTING], [TESTING_FEEDBACK]],
        ONE_DOCUMENT_PER_RUN_SCRIPT,
    )

    assert defective.cells[1]["status"] == "Partial"
    assert _cited_files(defective, 1, "status") == {HANDOVER, FIRST_TESTING}
    assert passed.cells[1]["status"] == "Done"
    assert _cited_files(passed, 1, "status") == {HANDOVER, TESTING_FEEDBACK}
    assert _cited_files(passed, 1, "what_testing_found") == {TESTING_FEEDBACK}


def test_one_document_per_run_and_the_paired_order_end_with_the_same_citations(
    tmp_path: Path,
) -> None:
    """The register must not depend on how the files were dropped in."""
    one_per_run = drive_batches(
        tmp_path,
        "one-per-run",
        [[MEETING_NOTE], [REQUIREMENTS], [HANDOVER], [TESTING_FEEDBACK]],
        FOUR_RUNS_SCRIPT,
    )[-1]
    in_pairs = drive_batches(
        tmp_path,
        "in-pairs",
        [[MEETING_NOTE, REQUIREMENTS], [HANDOVER, TESTING_FEEDBACK]],
        TWO_PAIRED_RUNS_SCRIPT,
    )[-1]

    assert one_per_run.cells == in_pairs.cells
    for row_number, cells in one_per_run.cells.items():
        for cell_name in cells:
            assert _cited_files(one_per_run, row_number, cell_name) == _cited_files(
                in_pairs, row_number, cell_name
            ), cell_name
    assert _cited_files(one_per_run, 1, "status") == {HANDOVER, TESTING_FEEDBACK}


def _cited_files(result: RunResult, row_number: int, cell_name: str) -> set[str]:
    return {
        source_file
        for source_file, _ in result.citations.get(row_number, {}).get(cell_name, [])
    }


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
