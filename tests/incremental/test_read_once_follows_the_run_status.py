from __future__ import annotations

import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision,
    approve_every_decision_and_finish_review,
    recorded_markers,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)
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
    write_meeting_note,
)
from tests.register.stored_register import documents_of_run


SOURCE_FILE = "meeting-note.md"
REQUIREMENT = "an email to the operations team on intake form submit"
TESTING_FILE = "testing-feedback.md"
TESTING_SUMMARY = "the email notification works"


@contextmanager
def _application_over_one_document(
    tmp_path: Path,
) -> Iterator[tuple[ApplicationProcess, str, str, Path]]:
    """One project holding one document, with the scripted answers it needs."""
    with temporary_project_folder("read-once") as (source_folder, source_folder_path):
        quote = write_meeting_note(source_folder, SOURCE_FILE, REQUIREMENT)
        script_path = tmp_path / "script.json"
        call_log_path = tmp_path / "model-calls.jsonl"
        write_script(
            script_path,
            {
                extract_marker(SOURCE_FILE): extraction_answer(REQUIREMENT, quote),
                match_marker(): match_answer(1),
                examine_marker(): no_findings_answer(),
            },
        )
        with temporary_database() as database_url:
            application = ApplicationProcess(
                database_url=database_url,
                script_path=script_path,
                call_log_path=call_log_path,
            )
            application.start()
            try:
                with application.client() as client:
                    project_id = client.post(
                        "/projects",
                        json={"source_folder_path": source_folder_path},
                    ).json()["project_id"]
                yield application, database_url, project_id, call_log_path
            finally:
                application.stop()


def test_a_document_read_by_a_done_run_is_counted_already_read(
    tmp_path: Path,
) -> None:
    with _application_over_one_document(tmp_path) as (
        application,
        database_url,
        project_id,
        call_log_path,
    ):
        with application.client() as client:
            first_run = client.post(
                "/runs", json={"project_id": project_id}
            ).json()["run_id"]
            wait_for_run_status(client, first_run, "needs review")
            approve_every_decision_and_finish_review(client, first_run)
            wait_for_run_status(client, first_run, "done")

            second_run = client.post(
                "/runs", json={"project_id": project_id}
            ).json()["run_id"]
            ended = wait_for_run_status(client, second_run, "no changes")
            second_batch = documents_of_run(database_url, second_run)

    assert second_batch == []
    already_read = [
        entry for entry in ended["skipped"] if entry["kind"] == "read before"
    ]
    assert [entry["file"] for entry in already_read] == [SOURCE_FILE]
    assert recorded_markers(call_log_path).count(extract_marker(SOURCE_FILE)) == 1


def test_a_document_read_only_by_a_discarded_run_is_read_again(
    tmp_path: Path,
) -> None:
    with _application_over_one_document(tmp_path) as (
        application,
        database_url,
        project_id,
        call_log_path,
    ):
        with application.client() as client:
            first_run = client.post(
                "/runs", json={"project_id": project_id}
            ).json()["run_id"]
            wait_for_run_status(client, first_run, "needs review")
            client.post(
                f"/runs/{first_run}/finish-review",
                json={"add_to_register": False},
            ).raise_for_status()
            wait_for_run_status(client, first_run, "discarded")

            # Nothing the discarded run read was added to the register, so its
            # document is not finished with — the next run reads it again.
            second_run = client.post(
                "/runs", json={"project_id": project_id}
            ).json()["run_id"]
            ended = wait_for_run_status(client, second_run, "needs review")
            second_batch = documents_of_run(database_url, second_run)

    assert second_batch == [SOURCE_FILE]
    assert ended["skipped"] == []
    assert recorded_markers(call_log_path).count(extract_marker(SOURCE_FILE)) == 2


def test_a_testing_document_read_only_by_a_discarded_run_is_read_again(
    tmp_path: Path,
) -> None:
    """A document holds no requirement, only observations — same rule.

    Requirement-bearing documents already follow their run's ending; before
    this test a discarded run's testing feedback was settled for ever by the
    no-requirements clause, and what it said was silently lost.
    """
    with temporary_project_folder("read-once-testing") as (
        source_folder,
        source_folder_path,
    ):
        waiting_folder = tmp_path / "not-yet-delivered"
        waiting_folder.mkdir()
        quote = write_meeting_note(source_folder, SOURCE_FILE, REQUIREMENT)
        testing_quote = write_meeting_note(
            waiting_folder, TESTING_FILE, TESTING_SUMMARY
        )
        script_path = tmp_path / "script.json"
        call_log_path = tmp_path / "model-calls.jsonl"
        write_script(
            script_path,
            {
                extract_marker(SOURCE_FILE): extraction_answer(REQUIREMENT, quote),
                extract_marker(TESTING_FILE): feedback_extraction_answer(
                    [(TESTING_SUMMARY, "Passed", testing_quote)]
                ),
                match_marker(): match_answer(1),
                observation_marker(): observation_answer_of([1]),
                examine_marker(): no_findings_answer(),
            },
        )
        with temporary_database() as database_url:
            application = ApplicationProcess(
                database_url=database_url,
                script_path=script_path,
                call_log_path=call_log_path,
            )
            application.start()
            try:
                with application.client() as client:
                    project_id = client.post(
                        "/projects",
                        json={"source_folder_path": source_folder_path},
                    ).json()["project_id"]

                    first_run = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    wait_for_run_status(client, first_run, "needs review")
                    approve_every_decision_and_finish_review(client, first_run)
                    wait_for_run_status(client, first_run, "done")

                    shutil.copy(
                        waiting_folder / TESTING_FILE,
                        source_folder / TESTING_FILE,
                    )
                    discarded_run = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    wait_for_run_status(client, discarded_run, "needs review")
                    approve_every_decision(client, discarded_run)
                    client.post(
                        f"/runs/{discarded_run}/finish-review",
                        json={"add_to_register": False},
                    ).raise_for_status()
                    wait_for_run_status(client, discarded_run, "discarded")

                    third_run = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    wait_for_run_status(client, third_run, "needs review")
                    third_batch = documents_of_run(database_url, third_run)

                    approve_every_decision_and_finish_review(client, third_run)
                    wait_for_run_status(client, third_run, "done")

                    fourth_run = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    ended = wait_for_run_status(client, fourth_run, "no changes")
            finally:
                application.stop()

    # The discarded run's testing document is read again; once a run carrying
    # it ends done, it is settled like any other document.
    assert third_batch == [TESTING_FILE]
    assert recorded_markers(call_log_path).count(extract_marker(TESTING_FILE)) == 2
    already_read = [
        entry for entry in ended["skipped"] if entry["kind"] == "read before"
    ]
    assert sorted(entry["file"] for entry in already_read) == [
        SOURCE_FILE,
        TESTING_FILE,
    ]
