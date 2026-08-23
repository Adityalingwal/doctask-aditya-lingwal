from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    extraction_answer,
    feedback_extraction_answer,
    match_answer,
    match_marker,
    no_findings_answer,
    observation_answer_of,
    observation_marker,
    write_document_stating,
    write_meeting_note,
)
from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)


FIRST_NOTE = "meeting-notes-10-mar.md"
SECOND_NOTE = "meeting-notes-20-mar.md"
FEEDBACK_FILE = "testing-feedback-12-aug.md"
TESTED_ASK = "an email to the operations team on intake form submit"
SILENT_ASK = "a search over old intake records"
FEEDBACK_QUOTE = "The operations email arrived on every submit we tried."
FEEDBACK_VERDICT = "the operations email arrived on every submit"


def test_two_cells_resting_on_one_quote_are_one_piece_of_evidence(
    tmp_path: Path,
) -> None:
    """The same sentence shown twice left a reader counting quotes (item 33).

    A passing testing report moves `What testing found` and `Status` off one
    quote, so the entry names both cells and shows the words once. A document
    that was read and said nothing carries its absence sentence and no quote
    at all, in the place its own evidence arrived.
    """
    rows = _register_after_a_testing_report(tmp_path)

    tested = rows[0]["evidence"]
    assert [entry["cells"] for entry in tested] == [
        ["What was asked"],
        ["What testing found", "Status"],
    ]
    assert tested[0]["source_line"] == f'{FIRST_NOTE}, under "Discussion"'
    assert tested[0]["quote"] == f"The client asked for {TESTED_ASK}."
    assert tested[0]["absence"] is None
    assert tested[1]["source_line"] == f'{FEEDBACK_FILE}, under "Discussion"'
    assert tested[1]["quote"] == FEEDBACK_QUOTE
    assert tested[1]["absence"] is None


def test_a_document_read_and_silent_carries_its_sentence_and_no_quote(
    tmp_path: Path,
) -> None:
    rows = _register_after_a_testing_report(tmp_path)

    silent = rows[1]["evidence"]
    assert [entry["cells"] for entry in silent] == [
        ["What was asked"],
        ["What testing found"],
    ]
    # There is no place to name behind a silence, so none is invented.
    assert silent[1]["source_line"] is None
    assert silent[1]["quote"] is None
    assert silent[1]["absence"] == (
        f"{FEEDBACK_FILE} was read, and it does not mention this ask."
    )


def _register_after_a_testing_report(tmp_path: Path) -> list[dict[str, Any]]:
    """Two rows from one batch, then a report that speaks about only one."""
    with temporary_project_folder("evidence-order") as (source_folder, folder_path):
        tested_quote = write_meeting_note(source_folder, FIRST_NOTE, TESTED_ASK)
        write_meeting_note(source_folder, SECOND_NOTE, SILENT_ASK)
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                extract_marker(FIRST_NOTE): extraction_answer(
                    TESTED_ASK, tested_quote
                ),
                extract_marker(SECOND_NOTE): extraction_answer(
                    SILENT_ASK, f"The client asked for {SILENT_ASK}."
                ),
                extract_marker(FEEDBACK_FILE): feedback_extraction_answer(
                    [(FEEDBACK_VERDICT, "Passed", FEEDBACK_QUOTE)]
                ),
                observation_marker(): observation_answer_of([1]),
                match_marker(): match_answer(2),
                examine_marker(): no_findings_answer(),
            },
        )
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
                    first_run = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    wait_for_run_status(client, first_run, "needs review")
                    approve_every_decision_and_finish_review(client, first_run)
                    wait_for_run_status(client, first_run, "done")

                    write_document_stating(
                        source_folder,
                        FEEDBACK_FILE,
                        "12 August 2026",
                        [FEEDBACK_QUOTE],
                    )
                    second_run = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    wait_for_run_status(client, second_run, "needs review")
                    approve_every_decision_and_finish_review(client, second_run)
                    wait_for_run_status(client, second_run, "done")
                    register = client.get(
                        f"/projects/{project_id}/register"
                    ).json()
            finally:
                application.stop()
    return register["rows"]


def test_groups_of_one_moment_follow_column_order_by_their_earliest_cell() -> None:
    """A testing quote also supporting Status sorts as column three, not four.

    The citations arrive ordered by cell name, so the group's first-seen cell
    is the alphabetical one (`status`); ordering on it would put a
    delivery-only Status group ahead of the testing group it followed.
    """
    from datetime import datetime

    from app.register.export_register import _evidence_of_row

    one_moment = datetime(2026, 8, 23, 12, 0, 0)
    delivery_only = {
        "cell": "status",
        "source_file": "handover-summary.md",
        "place": "What was handed over",
        "source_words": "We built it.",
        "absence_statement": None,
        "created_at": one_moment,
    }
    testing_status_half = dict(
        delivery_only,
        source_file="testing-feedback-12-aug.md",
        place="What we found",
        source_words="It worked.",
    )
    testing_verdict_half = dict(testing_status_half, cell="what_testing_found")

    # Alphabetical arrival: status citations first, the testing cell last.
    evidence = _evidence_of_row(
        [delivery_only, testing_status_half, testing_verdict_half]
    )

    assert [entry["cells"] for entry in evidence] == [
        ["What testing found", "Status"],
        ["Status"],
    ]
