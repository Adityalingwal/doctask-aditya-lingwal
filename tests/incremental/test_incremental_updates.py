from __future__ import annotations

import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx

from tests.runs.application import (
    ApplicationProcess,
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
    match_answer,
    match_answer_of,
    match_marker,
    match_marker_against_an_empty_register,
    no_findings_answer,
    write_meeting_note,
)
from tests.register.stored_register import documents_of_run, stored_rows

FIRST_FILE = "meeting-notes-10-mar.md"
SECOND_FILE = "meeting-notes-20-mar.md"
FIRST_REQUIREMENT = "an email to the operations team on intake form submit"
SECOND_REQUIREMENT = "the same notification sent over WhatsApp"
UNTOUCHED_ROW = 1
NEW_ROW_NUMBER = 2


@contextmanager
def _project_of_two_documents(
    tmp_path: Path,
) -> Iterator[tuple[ApplicationProcess, str, str, Path, Path, Path]]:
    """One project whose second document is written but not yet in its folder.

    Both documents are written up front so the script can be told what Extract
    will answer for each; only the first is in the watched folder to begin with,
    so the second run really is a second run over one arriving document.
    """
    with temporary_project_folder("two-documents") as (source_folder, source_folder_path):
        waiting_folder = tmp_path / "not-yet-delivered"
        waiting_folder.mkdir()

        first_quote = write_meeting_note(source_folder, FIRST_FILE, FIRST_REQUIREMENT)
        second_quote = write_meeting_note(waiting_folder, SECOND_FILE, SECOND_REQUIREMENT)

        script_path = tmp_path / "script.json"
        call_log_path = tmp_path / "model-calls.jsonl"
        write_script(
            script_path,
            {
                extract_marker(FIRST_FILE): extraction_answer(
                    FIRST_REQUIREMENT, first_quote
                ),
                extract_marker(SECOND_FILE): extraction_answer(
                    SECOND_REQUIREMENT, second_quote
                ),
                match_marker_against_an_empty_register(): match_answer(1),
                match_marker(): match_answer_of([None]),
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
                    yield (
                        application,
                        database_url,
                        project_id,
                        source_folder,
                        waiting_folder,
                        call_log_path,
                    )
            finally:
                application.stop()


def _exported_run(client: httpx.Client, project_id: str) -> str:
    run_id = client.post("/runs", json={"project_id": project_id}).json()["run_id"]
    wait_for_run_status(client, run_id, "needs review")
    approve_every_decision_and_finish_review(client, run_id)
    wait_for_run_status(client, run_id, "done")
    return run_id


def test_a_second_run_leaves_a_row_the_new_document_did_not_touch_byte_identical(
    tmp_path: Path,
) -> None:
    with _project_of_two_documents(tmp_path) as (
        application,
        database_url,
        project_id,
        source_folder,
        waiting_folder,
        _,
    ):
        with application.client() as client:
            _exported_run(client, project_id)
            after_first_run = stored_rows(database_url, project_id)

            shutil.copy(waiting_folder / SECOND_FILE, source_folder / SECOND_FILE)
            _exported_run(client, project_id)
            after_second_run = stored_rows(database_url, project_id)

    assert set(after_first_run) == {UNTOUCHED_ROW}
    assert set(after_second_run) == {UNTOUCHED_ROW, NEW_ROW_NUMBER}
    # Not "looks the same": the stored cells, the citations and the fingerprint
    # the first run wrote come back out of the second run unchanged.
    assert after_second_run[UNTOUCHED_ROW] == after_first_run[UNTOUCHED_ROW]


def test_a_file_that_did_not_change_is_not_read_or_paid_for_again(
    tmp_path: Path,
) -> None:
    with _project_of_two_documents(tmp_path) as (
        application,
        database_url,
        project_id,
        source_folder,
        waiting_folder,
        call_log_path,
    ):
        with application.client() as client:
            _exported_run(client, project_id)
            shutil.copy(waiting_folder / SECOND_FILE, source_folder / SECOND_FILE)
            second_run = _exported_run(client, project_id)
            second_batch = documents_of_run(database_url, second_run)

    assert second_batch == [SECOND_FILE]
    markers = recorded_markers(call_log_path)
    assert markers.count(extract_marker(FIRST_FILE)) == 1
    assert markers.count(extract_marker(SECOND_FILE)) == 1


def test_removing_a_watched_file_does_not_delete_the_rows_it_produced(
    tmp_path: Path,
) -> None:
    with _project_of_two_documents(tmp_path) as (
        application,
        database_url,
        project_id,
        source_folder,
        waiting_folder,
        _,
    ):
        with application.client() as client:
            _exported_run(client, project_id)
            after_first_run = stored_rows(database_url, project_id)

            (source_folder / FIRST_FILE).unlink()
            shutil.copy(waiting_folder / SECOND_FILE, source_folder / SECOND_FILE)
            second_run = _exported_run(client, project_id)
            after_second_run = stored_rows(database_url, project_id)
            export = client.get(f"/runs/{second_run}/export").json()

    assert after_second_run[UNTOUCHED_ROW] == after_first_run[UNTOUCHED_ROW]
    assert [row["row_number"] for row in export["rows"]] == [
        UNTOUCHED_ROW,
        NEW_ROW_NUMBER,
    ]


def test_a_second_run_proposal_reaches_the_register_only_after_the_export_gate(
    tmp_path: Path,
) -> None:
    with _project_of_two_documents(tmp_path) as (
        application,
        database_url,
        project_id,
        source_folder,
        waiting_folder,
        _,
    ):
        with application.client() as client:
            _exported_run(client, project_id)
            after_first_run = stored_rows(database_url, project_id)

            shutil.copy(waiting_folder / SECOND_FILE, source_folder / SECOND_FILE)
            second_run = client.post(
                "/runs", json={"project_id": project_id}
            ).json()["run_id"]
            at_review = wait_for_run_status(client, second_run, "needs review")
            # The proposal is waiting, and the register has not moved for it.
            while_waiting = stored_rows(database_url, project_id)

            export_decision = next(
                decision
                for decision in at_review["decisions"]
                if decision["kind"] == "export"
            )
            client.post(
                f"/runs/{second_run}/decisions",
                json={
                    "decision_id": export_decision["decision_id"],
                    "outcome": "rejected",
                },
            ).raise_for_status()
            client.post(f"/runs/{second_run}/finish-review").raise_for_status()
            wait_for_run_status(client, second_run, "discarded")
            after_rejection = stored_rows(database_url, project_id)

    assert while_waiting == after_first_run
    assert after_rejection == after_first_run


def test_a_changed_rules_file_re_examines_the_register_without_reading_a_document(
    tmp_path: Path,
) -> None:
    with temporary_project_folder("re-examined") as (source_folder, source_folder_path):
        quote = write_meeting_note(source_folder, FIRST_FILE, FIRST_REQUIREMENT)
        rules_config_path = tmp_path / "rules.yaml"
        rules_config_path.write_text(
            "rules:\n  - id: R1\n    text: \"Anything built must be written down.\"\n",
            encoding="utf-8",
        )
        script_path = tmp_path / "script.json"
        call_log_path = tmp_path / "model-calls.jsonl"
        write_script(
            script_path,
            {
                extract_marker(FIRST_FILE): extraction_answer(FIRST_REQUIREMENT, quote),
                match_marker(): match_answer(1),
                examine_marker(): no_findings_answer(),
            },
        )

        with temporary_database() as database_url:
            application = ApplicationProcess(
                database_url=database_url,
                script_path=script_path,
                call_log_path=call_log_path,
                rules_config_path=rules_config_path,
            )
            application.start()
            try:
                with application.client() as client:
                    project_id = client.post(
                        "/projects",
                        json={"source_folder_path": source_folder_path},
                    ).json()["project_id"]
                    _exported_run(client, project_id)
                    after_first_run = stored_rows(database_url, project_id)

                    rules_config_path.write_text(
                        "rules:\n  - id: R1\n    text: \"Anything built must be "
                        "written down.\"\n  - id: R9\n    text: \"Every requirement "
                        "names the person who asked for it.\"\n",
                        encoding="utf-8",
                    )
                    rules_run = _exported_run(client, project_id)
                    after_rules_run = stored_rows(database_url, project_id)
                    rules_run_batch = documents_of_run(database_url, rules_run)
                    examined = client.get(f"/runs/{rules_run}").json()["examine"]

                    unchanged_run = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    ended = wait_for_run_status(
                        client, unchanged_run, "no changes"
                    )
            finally:
                application.stop()

    markers = recorded_markers(call_log_path)
    # The rules-only run examined the register without reading or matching
    # anything: one Extract call and one Match call in total, both the first
    # run's, and a second Examine call for the changed rules.
    assert markers.count(extract_marker(FIRST_FILE)) == 1
    assert markers.count(match_marker()) == 1
    assert markers.count(examine_marker()) == 2
    assert rules_run_batch == []
    assert examined["rows_examined"] == 1
    assert [rule["id"] for rule in examined["rules"]] == ["R1", "R9"]
    assert after_rules_run[UNTOUCHED_ROW] == after_first_run[UNTOUCHED_ROW]
    assert ended["ended_early_reason"] == (
        "Nothing was read — all 1 file was skipped. See the Skipped tab for why."
    )
