from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from tests.runs.application import (
    PROJECT_ROOT,
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    temporary_database,
    wait_for_run_status,
    write_script,
)
from tests.documents.register_documents import (
    dated_extraction_answer,
    examine_marker,
    extract_marker,
    match_answer,
    match_answer_of,
    match_marker,
    match_marker_against_an_empty_register,
    no_findings_answer,
)
from tests.register.stored_register import documents_of_run, stored_rows

from app.extract.answer import (
    CLIENT_REQUIREMENTS_DOCUMENT,
    MEETING_NOTES,
    TESTING_FEEDBACK,
)

INTAKE_PORTAL = PROJECT_ROOT / "sample-projects" / "intake-portal"
NORTHSIDE_DENTAL = PROJECT_ROOT / "sample-projects" / "northside-dental"


def _copy_corpus_file(corpus: Path, source_folder: Path, file_name: str) -> None:
    shutil.copy(corpus / file_name, source_folder / file_name)


def _two_runs_over(
    tmp_path: Path,
    project_name: str,
    corpus: Path,
    first_batch: list[str],
    second_batch: list[str],
    answers: dict[str, dict],
) -> tuple[dict[int, Any], dict[int, Any], list[str]]:
    """Run one corpus project twice, and report the register after each run."""
    source_folder = tmp_path / "corpus"
    source_folder.mkdir()
    for file_name in first_batch:
        _copy_corpus_file(corpus, source_folder, file_name)

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
                    "/projects",
                    json={
                        "name": project_name,
                        "source_folder_path": str(source_folder),
                    },
                ).json()["project_id"]
                _exported_run(client, project_id)
                after_first_run = stored_rows(database_url, project_id)

                for file_name in second_batch:
                    _copy_corpus_file(corpus, source_folder, file_name)
                second_run = _exported_run(client, project_id)
                after_second_run = stored_rows(database_url, project_id)
                read_again = documents_of_run(database_url, second_run)
        finally:
            application.stop()
    return after_first_run, after_second_run, read_again


def _exported_run(client: Any, project_id: str) -> str:
    run_id = client.post("/runs", json={"project_id": project_id}).json()["run_id"]
    wait_for_run_status(client, run_id, "needs review")
    approve_every_decision_and_finish_review(client, run_id)
    wait_for_run_status(client, run_id, "done")
    return run_id


def test_a_second_run_over_the_intake_portal_corpus_touches_only_what_arrived(
    tmp_path: Path,
) -> None:
    meeting_notes = "meeting-notes-10-mar.md"
    requirements = "client-requirements-v1.md"
    after_first_run, after_second_run, read_again = _two_runs_over(
        tmp_path,
        "Intake portal corpus",
        INTAKE_PORTAL,
        [meeting_notes],
        [requirements],
        {
            match_marker_against_an_empty_register(): match_answer(3),
            extract_marker(meeting_notes): _meeting_notes_answer(),
            extract_marker(requirements): _written_scope_answer(),
            match_marker(): match_answer_of([None, 1, None]),
            examine_marker(): no_findings_answer(),
        },
    )

    assert read_again == [requirements]
    assert sorted(after_first_run) == [1, 2, 3]
    assert sorted(after_second_run) == [1, 2, 3, 4, 6]
    # The WhatsApp and search rows are what the arriving document says nothing
    # about, and they come back out of the second run unchanged to the byte.
    assert after_second_run[2] == after_first_run[2]
    assert after_second_run[3] == after_first_run[3]
    # Row 1 gained the written evidence the approved merge moved onto it, and
    # its seven cells and their fingerprint still did not move.
    assert after_second_run[1].cells == after_first_run[1].cells
    assert after_second_run[1].fingerprint == after_first_run[1].fingerprint
    assert len(after_second_run[1].citations) > len(after_first_run[1].citations)


def test_a_second_run_over_the_northside_dental_corpus_touches_only_what_arrived(
    tmp_path: Path,
) -> None:
    meeting_notes = "meeting-notes-05-jun.md"
    requirements = "client-requirements-v1.docx"
    testing_feedback = "testing-feedback-15-jul.pdf"
    after_first_run, after_second_run, read_again = _two_runs_over(
        tmp_path,
        "Northside Dental corpus",
        NORTHSIDE_DENTAL,
        [meeting_notes],
        [requirements, testing_feedback],
        {
            match_marker_against_an_empty_register(): match_answer(3),
            extract_marker(meeting_notes): dated_extraction_answer(
                [
                    (
                        "online appointment booking on the clinic website",
                        "The clinic asked for online appointment booking on the "
                        "clinic website, so a patient can pick a slot without "
                        "telephoning reception.",
                    ),
                    (
                        "an SMS reminder to the patient before the appointment",
                        "The clinic also asked for an SMS reminder to the patient "
                        "before the appointment",
                    ),
                    (
                        "a doctor-wise daily schedule screen",
                        "The clinic asked for a doctor-wise daily schedule screen, "
                        "so each dentist can see their own list for the day.",
                    ),
                ],
                MEETING_NOTES,
                "5 June 2026",
            ),
            extract_marker(requirements): dated_extraction_answer(
                [
                    (
                        "online booking from the clinic website",
                        "A patient must be able to book an appointment from the "
                        "clinic website without telephoning reception.",
                    ),
                    (
                        "an email reminder before the appointment",
                        "The system must send the patient an email reminder "
                        "before the appointment.",
                    ),
                    (
                        "a doctor-wise daily list for each dentist",
                        "Each dentist must see a doctor-wise list of their own "
                        "appointments for the day.",
                    ),
                    (
                        "a cancel or reschedule link on every confirmation",
                        "Every booking confirmation must carry a link the patient "
                        "can use to cancel or reschedule the appointment.",
                    ),
                ],
                CLIENT_REQUIREMENTS_DOCUMENT,
                "10 June 2026",
            ),
            extract_marker(testing_feedback): _testing_feedback_answer(),
            match_marker(): match_answer_of([1, None, 3, None]),
            examine_marker(): no_findings_answer(),
        },
    )

    assert read_again == [requirements, testing_feedback]
    assert sorted(after_first_run) == [1, 2, 3]
    assert sorted(after_second_run) == [1, 2, 3, 5, 7]
    # The SMS reminder row is the one nothing that arrived asked about.
    assert after_second_run[2] == after_first_run[2]
    for merged_into in (1, 3):
        assert after_second_run[merged_into].cells == after_first_run[merged_into].cells
        assert (
            after_second_run[merged_into].fingerprint
            == after_first_run[merged_into].fingerprint
        )


def _meeting_notes_answer() -> dict[str, Any]:
    return dated_extraction_answer(
        [
            (
                "a notification to the operations team on intake form submit",
                "The client asked for the operations team to receive a "
                "notification whenever a visitor submits the intake form.",
            ),
            (
                "the same notification sent over WhatsApp",
                "They also want the same notification sent over WhatsApp, so "
                "staff can respond while away from their desks.",
            ),
            (
                "a search over old intake records",
                "The client also asked to search old intake records from the "
                "portal.",
            ),
        ],
        MEETING_NOTES,
        "10 March 2026",
    )


def _written_scope_answer() -> dict[str, Any]:
    return dated_extraction_answer(
        [
            (
                "an intake form that validates every required field",
                "An intake form that validates every required field before it "
                "submits.",
            ),
            (
                "an email notification to the operations team on submit",
                "An email notification to the operations team whenever a "
                "visitor submits the intake form.",
            ),
            (
                "a records list page over every intake record",
                "A records list page showing every intake record the portal has "
                "taken.",
            ),
        ],
        CLIENT_REQUIREMENTS_DOCUMENT,
        "12 March 2026",
    )


def _testing_feedback_answer() -> dict[str, Any]:
    """The testing document reports what it found and asks for nothing new."""
    return dated_extraction_answer([], TESTING_FEEDBACK, "15 July 2026") | {
        "testing_observations": [
            {
                "summary": "online booking saved every test appointment",
                "label": "Passed",
                "quote": (
                    "Online booking works. Every test appointment was saved "
                    "against the dentist we chose."
                ),
            },
            {
                "summary": "the daily schedule screen opens on the wrong day",
                "label": "Defect",
                "quote": "The daily schedule screen shows the wrong day.",
            },
        ]
    }
