from __future__ import annotations

from pathlib import Path

import httpx

from conftest import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    logged_run_events,
    model_call_failure,
    recorded_markers,
    temporary_database,
    wait_for_run_status,
    wait_until,
    write_script,
)
from register_documents import (
    examine_marker,
    extract_marker,
    extraction_answer,
    match_answer,
    match_marker,
    no_findings_answer,
    write_meeting_note,
)
from stored_register import documents_of_run, runs_of_project, stored_rows


FIRST_FILE = "first-notes.md"
SECOND_FILE = "second-notes.md"
FIRST_ROW = "an email to the operations team on intake form submit"
SECOND_ROW = "a search over old intake records"
MODEL_DELAY_SECONDS = 2.0
TIMES_ASKED_AGAIN = 3


def test_a_second_run_on_one_project_waits_while_the_first_holds_the_lock(
    tmp_path: Path,
) -> None:
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    quote = write_meeting_note(source_folder, FIRST_FILE, FIRST_ROW)
    script_path = tmp_path / "script.json"
    call_log_path = tmp_path / "model-calls.jsonl"
    write_script(
        script_path,
        {
            extract_marker(FIRST_FILE): extraction_answer(FIRST_ROW, quote),
            match_marker(): match_answer(1),
            examine_marker(): no_findings_answer(),
        },
    )

    with temporary_database() as database_url:
        application = ApplicationProcess(
            database_url=database_url,
            script_path=script_path,
            call_log_path=call_log_path,
            delay_seconds=MODEL_DELAY_SECONDS,
        )
        application.start()
        try:
            with application.client() as client:
                project_id = _project(client, "Queued intake portal", source_folder)
                running_run = _start(client, project_id)
                # The first document's call is in flight, so the run holds its
                # project's lock while the second run is asked for.
                wait_until(
                    lambda: recorded_markers(call_log_path),
                    "the first run has reached the model",
                )
                queued = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()
                while_running = runs_of_project(database_url, project_id)

                at_review = wait_for_run_status(
                    client, running_run, "waiting for review"
                )
                asked_again = [
                    client.post("/runs", json={"project_id": project_id}).json()
                    for _ in range(TIMES_ASKED_AGAIN)
                ]
                while_at_review = runs_of_project(database_url, project_id)

                approve_every_decision_and_finish_review(client, running_run)
                wait_for_run_status(client, running_run, "done")
                wait_for_run_status(
                    client, queued["run_id"], "ended without changes"
                )
                after_both = runs_of_project(database_url, project_id)
        finally:
            application.stop()

    assert queued["status"] == "waiting"
    assert queued["run_id"] != running_run
    assert while_running == [(running_run, "running"), (queued["run_id"], "waiting")]
    assert at_review["status"] == "waiting for review"
    # However often a run is asked for, the same one waiting run comes back.
    assert asked_again == [
        {"run_id": queued["run_id"], "status": "waiting"}
    ] * TIMES_ASKED_AGAIN
    assert while_at_review == [
        (running_run, "waiting for review"),
        (queued["run_id"], "waiting"),
    ]
    assert after_both == [
        (running_run, "done"),
        (queued["run_id"], "ended without changes"),
    ]


def test_a_queued_run_forms_its_batch_when_it_starts_not_when_it_was_queued(
    tmp_path: Path,
) -> None:
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    first_quote = write_meeting_note(source_folder, FIRST_FILE, FIRST_ROW)
    script_path = tmp_path / "script.json"
    log_path = tmp_path / "application.log"
    write_script(
        script_path,
        {
            extract_marker(FIRST_FILE): extraction_answer(FIRST_ROW, first_quote),
            extract_marker(SECOND_FILE): extraction_answer(
                SECOND_ROW, f"The client asked for {SECOND_ROW}."
            ),
            match_marker(): match_answer(1),
            examine_marker(): no_findings_answer(),
        },
    )

    with temporary_database() as database_url:
        application = ApplicationProcess(
            database_url=database_url,
            script_path=script_path,
            call_log_path=tmp_path / "model-calls.jsonl",
            log_path=log_path,
        )
        application.start()
        try:
            with application.client() as client:
                project_id = _project(client, "Batch-at-start portal", source_folder)
                first_run = _start(client, project_id)
                wait_for_run_status(client, first_run, "waiting for review")
                queued_run = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]

                # Arrives while the second run is already queued and the first
                # still holds the lock, so it can only belong to the queued run.
                write_meeting_note(source_folder, SECOND_FILE, SECOND_ROW)

                approve_every_decision_and_finish_review(client, first_run)
                wait_for_run_status(client, first_run, "done")
                wait_for_run_status(client, queued_run, "waiting for review")
                approve_every_decision_and_finish_review(client, queued_run)
                wait_for_run_status(client, queued_run, "done")

            first_documents = documents_of_run(database_url, first_run)
            queued_documents = documents_of_run(database_url, queued_run)
            register = stored_rows(database_url, project_id)
        finally:
            application.stop()

    assert first_documents == [FIRST_FILE]
    assert queued_documents == [SECOND_FILE]
    assert [row.cells[0] for row in register.values()] == [FIRST_ROW, SECOND_ROW]
    # Nobody started the queued run: the run ahead of it ending did.
    assert any(
        event["event"] == "queued_run_started" and event["run_id"] == queued_run
        for event in logged_run_events(log_path)
    )


def test_a_waiting_run_still_starts_when_the_run_ahead_of_it_fails(
    tmp_path: Path,
) -> None:
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    quote = write_meeting_note(source_folder, FIRST_FILE, FIRST_ROW)
    script_path = tmp_path / "script.json"
    call_log_path = tmp_path / "model-calls.jsonl"
    write_script(
        script_path,
        {
            extract_marker(FIRST_FILE): extraction_answer(FIRST_ROW, quote),
            match_marker(): model_call_failure(
                "the provider closed the connection before answering"
            ),
        },
    )

    with temporary_database() as database_url:
        application = ApplicationProcess(
            database_url=database_url,
            script_path=script_path,
            call_log_path=call_log_path,
            delay_seconds=MODEL_DELAY_SECONDS,
        )
        application.start()
        try:
            with application.client() as client:
                project_id = _project(client, "Failing intake portal", source_folder)
                failing_run = _start(client, project_id)
                wait_until(
                    lambda: recorded_markers(call_log_path),
                    "the failing run has reached the model",
                )
                queued_run = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]

                wait_for_run_status(client, failing_run, "failed")
                queued_failed = wait_for_run_status(client, queued_run, "failed")
            after_both = runs_of_project(database_url, project_id)
            queued_documents = documents_of_run(database_url, queued_run)
        finally:
            application.stop()

    assert after_both == [(failing_run, "failed"), (queued_run, "failed")]
    # The waiting run was not lost with the one ahead of it: it started, read
    # the batch that run left unread, and failed on its own account.
    assert queued_documents == [FIRST_FILE]
    assert queued_failed["failure_reason"] is not None


def _project(client: httpx.Client, name: str, source_folder: Path) -> str:
    return client.post(
        "/projects",
        json={"name": name, "source_folder_path": str(source_folder)},
    ).json()["project_id"]


def _start(client: httpx.Client, project_id: str) -> str:
    return client.post("/runs", json={"project_id": project_id}).json()["run_id"]
