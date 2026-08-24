from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    wait_until,
    write_script,
)
from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    extraction_answer,
    match_answer,
    match_answer_of,
    match_marker,
    match_marker_against_an_empty_register,
    no_findings_answer,
    write_meeting_note,
)
from tests.register.stored_register import runs_of_project

ALREADY_THERE = "meeting-notes-10-mar.md"
ARRIVING = "meeting-notes-20-mar.md"
ARRIVING_LATER = "testing-feedback-25-mar.md"
UNSUPPORTED_ARRIVAL = "delivery-plan.csv"
FIRST_REQUIREMENT = "an email to the operations team on intake form submit"
SECOND_REQUIREMENT = "the same notification sent over WhatsApp"
THIRD_REQUIREMENT = "a search over old intake records"
# Short enough to keep the test quick, and still two polls inside one quiet
# period, which is the shape the shipped ten-and-thirty-second pair has.
POLL_SECONDS = 0.2
QUIET_SECONDS = 0.6
LONGER_THAN_A_QUIET_PERIOD = 3.0


@contextmanager
def _watched_project(
    tmp_path: Path,
) -> Iterator[tuple[ApplicationProcess, str, str, Path]]:
    with temporary_project_folder("watched") as (source_folder, source_folder_path):
        waiting_folder = tmp_path / "not-yet-delivered"
        waiting_folder.mkdir()

        first_quote = write_meeting_note(source_folder, ALREADY_THERE, FIRST_REQUIREMENT)
        second_quote = write_meeting_note(waiting_folder, ARRIVING, SECOND_REQUIREMENT)
        third_quote = write_meeting_note(waiting_folder, ARRIVING_LATER, THIRD_REQUIREMENT)

        watcher_config_path = tmp_path / "watcher.yaml"
        watcher_config_path.write_text(
            f"poll_seconds: {POLL_SECONDS}\nquiet_seconds: {QUIET_SECONDS}\n",
            encoding="utf-8",
        )
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                extract_marker(ALREADY_THERE): extraction_answer(
                    FIRST_REQUIREMENT, first_quote
                ),
                extract_marker(ARRIVING): extraction_answer(
                    SECOND_REQUIREMENT, second_quote
                ),
                extract_marker(ARRIVING_LATER): extraction_answer(
                    THIRD_REQUIREMENT, third_quote
                ),
                match_marker_against_an_empty_register(): match_answer(2),
                match_marker(): match_answer_of([None]),
                examine_marker(): no_findings_answer(),
            },
        )

        with temporary_database() as database_url:
            application = ApplicationProcess(
                database_url=database_url,
                script_path=script_path,
                call_log_path=tmp_path / "model-calls.jsonl",
                watcher_config_path=watcher_config_path,
            )
            application.start()
            try:
                with application.client() as client:
                    project_id = client.post(
                        "/projects",
                        json={"source_folder_path": source_folder_path},
                    ).json()["project_id"]
                yield application, database_url, project_id, source_folder
            finally:
                application.stop()


def _copy_in(source_folder: Path, file_name: str, requirement: str) -> None:
    write_meeting_note(source_folder, file_name, requirement)


def _let_the_watcher_see_the_folder() -> None:
    """Wait out one poll, so what is in the folder counts as already there.

    The watcher calls a file an arrival by comparing the folder against the way
    it last saw it, so a file written before it has ever looked is not one.
    """
    time.sleep(POLL_SECONDS * 5)


def _runs(database_url: str, project_id: str) -> list[tuple[str, str]]:
    return runs_of_project(database_url, project_id)


def _more_than_one_run(
    database_url: str,
    project_id: str,
) -> list[tuple[str, str]] | None:
    started = _runs(database_url, project_id)
    return started if len(started) > 1 else None


def test_the_watcher_starts_a_run_once_an_arriving_file_has_settled(
    tmp_path: Path,
) -> None:
    with _watched_project(tmp_path) as (
        application,
        database_url,
        project_id,
        source_folder,
    ):
        _let_the_watcher_see_the_folder()
        started_before_anything_arrived = _runs(database_url, project_id)
        _copy_in(source_folder, ARRIVING, SECOND_REQUIREMENT)
        started = wait_until(
            lambda: _runs(database_url, project_id),
            "the watcher starts a run for the file that arrived",
        )
        with application.client() as client:
            at_review = wait_for_run_status(
                client, started[0][0], "needs review"
            )

    # A folder that was simply already there is not an arrival: only the file
    # that turned up after the project was created starts a run.
    assert started_before_anything_arrived == []
    assert len(started) == 1
    assert [entry["file"] for entry in at_review["skipped"]] == []


def test_the_watcher_does_not_start_a_second_run_while_one_is_active(
    tmp_path: Path,
) -> None:
    with _watched_project(tmp_path) as (
        application,
        database_url,
        project_id,
        source_folder,
    ):
        _let_the_watcher_see_the_folder()
        _copy_in(source_folder, ARRIVING, SECOND_REQUIREMENT)
        started = wait_until(
            lambda: _runs(database_url, project_id),
            "the watcher starts the first run",
        )
        first_run = started[0][0]
        with application.client() as client:
            wait_for_run_status(client, first_run, "needs review")
            _copy_in(source_folder, ARRIVING_LATER, THIRD_REQUIREMENT)
            # Several quiet periods pass with that run still holding the
            # project, and the watcher must start nothing behind it.
            time.sleep(LONGER_THAN_A_QUIET_PERIOD)
            while_active = _runs(database_url, project_id)

            approve_every_decision_and_finish_review(client, first_run)
            wait_for_run_status(client, first_run, "done")
            after_release = wait_until(
                lambda: _more_than_one_run(database_url, project_id),
                "the watcher starts the run the file that arrived during review "
                "was waiting for",
            )
            wait_for_run_status(client, after_release[1][0], "needs review")

    assert [status for _, status in while_active] == ["needs review"]
    assert len(after_release) == 2


def test_a_manual_run_serves_the_arrival_before_the_watcher_starts_one(
    tmp_path: Path,
) -> None:
    """Never-do: one arrival must not leave a second `no changes` run."""
    with _watched_project(tmp_path) as (
        application,
        database_url,
        project_id,
        source_folder,
    ):
        _let_the_watcher_see_the_folder()
        _copy_in(source_folder, ARRIVING, SECOND_REQUIREMENT)
        with application.client() as client:
            manual_run = client.post(
                "/runs", json={"project_id": project_id}
            ).json()["run_id"]
            wait_for_run_status(client, manual_run, "needs review")
            approve_every_decision_and_finish_review(client, manual_run)
            wait_for_run_status(client, manual_run, "done")
            time.sleep(LONGER_THAN_A_QUIET_PERIOD)
        after_the_watcher_settles = _runs(database_url, project_id)

    assert after_the_watcher_settles == [(manual_run, "done")]


def test_a_queued_run_serves_an_arrival_without_a_watcher_duplicate(
    tmp_path: Path,
) -> None:
    """A file collected by the waiting run must not earn a third run."""
    with _watched_project(tmp_path) as (
        application,
        database_url,
        project_id,
        source_folder,
    ):
        _let_the_watcher_see_the_folder()
        _copy_in(source_folder, ARRIVING, SECOND_REQUIREMENT)
        first_run = wait_until(
            lambda: _runs(database_url, project_id),
            "the watcher starts the first run",
        )[0][0]
        with application.client() as client:
            wait_for_run_status(client, first_run, "needs review")
            _copy_in(source_folder, ARRIVING_LATER, THIRD_REQUIREMENT)
            queued_run = client.post(
                "/runs", json={"project_id": project_id}
            ).json()
            assert queued_run["status"] == "queued"

            approve_every_decision_and_finish_review(client, first_run)
            wait_for_run_status(client, first_run, "done")
            wait_for_run_status(client, queued_run["run_id"], "needs review")
            approve_every_decision_and_finish_review(client, queued_run["run_id"])
            wait_for_run_status(client, queued_run["run_id"], "done")
            time.sleep(LONGER_THAN_A_QUIET_PERIOD)
        after_the_watcher_settles = _runs(database_url, project_id)

    assert after_the_watcher_settles == [
        (first_run, "done"),
        (queued_run["run_id"], "done"),
    ]


def test_an_unsupported_arrival_still_gets_one_watcher_run_and_reason(
    tmp_path: Path,
) -> None:
    """Duplicate suppression must not suppress the first honest refusal."""
    with _watched_project(tmp_path) as (
        application,
        database_url,
        project_id,
        source_folder,
    ):
        # This case is about the unsupported arrival alone. Remove the fixture
        # document before the watcher's first sight so it cannot become an
        # unrelated model-driven batch in the same run.
        (source_folder / ALREADY_THERE).unlink()
        _let_the_watcher_see_the_folder()
        (source_folder / UNSUPPORTED_ARRIVAL).write_text(
            "feature,owner\nbarcode scanning,warehouse\n", encoding="utf-8"
        )
        started = wait_until(
            lambda: _runs(database_url, project_id),
            "the watcher starts one run for the unsupported arrival",
        )
        with application.client() as client:
            ended = wait_for_run_status(client, started[0][0], "no changes")
            time.sleep(LONGER_THAN_A_QUIET_PERIOD)
        after_the_watcher_settles = _runs(database_url, project_id)

    unsupported = [
        entry for entry in ended["skipped"] if entry["file"] == UNSUPPORTED_ARRIVAL
    ]
    assert len(unsupported) == 1
    assert unsupported[0]["kind"] == "not read"
    assert after_the_watcher_settles == [(started[0][0], "no changes")]
