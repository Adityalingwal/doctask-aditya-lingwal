from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    extraction_answer,
    feedback_extraction_answer,
    match_answer,
    match_marker,
    match_marker_against_an_empty_register,
    no_findings_answer,
    observation_answer_of,
    observation_marker,
    write_document_stating,
    write_meeting_note,
)
from tests.examine.answers import examine_answer, one_finding
from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)


MEETING_FILE = "meeting-note.md"
TESTING_FILE = "testing-feedback.md"
REQUIREMENT = "an email to the operations team on intake form submit"
TESTING_SUMMARY = "the notification reaches the operations team"
TESTING_QUOTE = "The email notification reaches the operations team every time."
TESTING_DATE = "25 March 2026"
STATUS_BEFORE_TESTING = "Requested"
STATUS_AFTER_PASSED_TESTING = "Done"


@contextmanager
def _project(
    tmp_path: Path,
    examine: dict[str, Any],
) -> Iterator[tuple[ApplicationProcess, Path, str]]:
    """One application over a folder holding a meeting note, with nothing run yet.

    The testing feedback is scripted here but only written to the folder by the
    test that wants a second run to read it.
    """
    with temporary_project_folder("history-read") as (folder, source_folder_path):
        quote = write_meeting_note(folder, MEETING_FILE, REQUIREMENT)
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                extract_marker(MEETING_FILE): extraction_answer(REQUIREMENT, quote),
                extract_marker(TESTING_FILE): feedback_extraction_answer(
                    [(TESTING_SUMMARY, "Passed", TESTING_QUOTE)]
                ),
                match_marker(): match_answer(1),
                match_marker_against_an_empty_register(): match_answer(1),
                observation_marker(): observation_answer_of([1]),
                examine_marker(): examine,
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
                        "/projects",
                        json={"source_folder_path": source_folder_path},
                    ).json()["project_id"]
                yield application, folder, project_id
            finally:
                application.stop()


def _run_to_done(client: httpx.Client, project_id: str) -> str:
    run_id = client.post("/runs", json={"project_id": project_id}).json()["run_id"]
    wait_for_run_status(client, run_id, "needs review")
    approve_every_decision_and_finish_review(client, run_id)
    wait_for_run_status(client, run_id, "done")
    return run_id


def _of_kind(entries: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [entry for entry in entries if entry["kind"] == kind]


def test_a_rows_birth_is_one_row_created_entry_naming_its_document(
    tmp_path: Path,
) -> None:
    with _project(tmp_path, no_findings_answer()) as (application, _folder, project_id):
        with application.client() as client:
            _run_to_done(client, project_id)
            answered = client.get(f"/projects/{project_id}/history")

    assert answered.status_code == 200
    entries = answered.json()["entries"]
    # The audit table holds one cell-change row per cell of a new row. A
    # reader is shown the birth once, folded in the core function, so the
    # four writes never reach any surface as four separate changes.
    assert [entry["kind"] for entry in entries] == ["row created"]
    created = entries[0]
    assert created["row_number"] == 1
    assert created["what_was_asked"] == REQUIREMENT
    assert created["run_number"] == 1
    assert created["source_file"] == MEETING_FILE
    assert created["changed_at"] is not None


def test_a_status_move_is_a_cell_change_entry_with_old_and_new_and_newest_first(
    tmp_path: Path,
) -> None:
    with _project(tmp_path, no_findings_answer()) as (application, folder, project_id):
        with application.client() as client:
            _run_to_done(client, project_id)
            write_document_stating(folder, TESTING_FILE, TESTING_DATE, [TESTING_QUOTE])
            _run_to_done(client, project_id)
            entries = client.get(f"/projects/{project_id}/history").json()["entries"]

    status_move = next(
        entry
        for entry in _of_kind(entries, "cell change")
        if entry["cell"] == "status"
    )
    assert status_move["row_number"] == 1
    assert status_move["old_value"] == STATUS_BEFORE_TESTING
    assert status_move["new_value"] == STATUS_AFTER_PASSED_TESTING
    assert status_move["run_number"] == 2

    # Newest first: the second run's changes stand above the birth the first
    # run recorded, and the birth is still the last thing in the list.
    born = next(entry for entry in entries if entry["kind"] == "row created")
    assert entries.index(status_move) < entries.index(born)
    assert entries[-1] is born
    assert born["run_number"] == 1
    # One run commits in one transaction, so its entries share a timestamp and
    # are ordered by row number and then cell name — never by chance.
    assert [entry["cell"] for entry in _of_kind(entries, "cell change")] == [
        "status",
        "what_testing_found",
    ]


def test_an_approved_finding_shows_as_a_finding_attached_entry(tmp_path: Path) -> None:
    finding = one_finding()
    with _project(tmp_path, examine_answer([finding])) as (
        application,
        _folder,
        project_id,
    ):
        with application.client() as client:
            _run_to_done(client, project_id)
            entries = client.get(f"/projects/{project_id}/history").json()["entries"]

    attached = _of_kind(entries, "finding attached")
    assert len(attached) == 1
    assert attached[0]["detail"] == f"{finding['rule_id']} — {finding['issue']}"
    assert attached[0]["row_number"] == 1
    assert attached[0]["run_number"] == 1
    # An attachment moved no cell and came from no document, so it claims
    # neither rather than naming one it does not have.
    assert "cell" not in attached[0]
    assert "source_file" not in attached[0]


def test_an_empty_history_answers_two_hundred_with_no_entries(tmp_path: Path) -> None:
    with _project(tmp_path, no_findings_answer()) as (application, _folder, project_id):
        with application.client() as client:
            answered = client.get(f"/projects/{project_id}/history")

    assert answered.status_code == 200
    assert answered.json() == {"entries": []}


def test_an_unknown_project_is_refused_by_name(tmp_path: Path) -> None:
    unknown_project_id = str(uuid4())
    with _project(tmp_path, no_findings_answer()) as (
        application,
        _folder,
        _project_id,
    ):
        with application.client() as client:
            history = client.get(f"/projects/{unknown_project_id}/history")
            register = client.get(f"/projects/{unknown_project_id}/register")

    # One refusal, worded once in core, whichever read asked for the project.
    assert history.status_code == 404
    assert history.status_code == register.status_code
    assert history.json()["detail"] == register.json()["detail"]
    assert f"no project has id {unknown_project_id}" in history.json()["detail"]


def test_the_register_document_carries_no_history(tmp_path: Path) -> None:
    """History is a read of its own; the exported register does not grow a key.

    This passes before the history read exists as well as after — it guards
    the decision that the register document is left untouched, so it is a
    lock rather than a detector for this branch's work.
    """
    with _project(tmp_path, no_findings_answer()) as (application, _folder, project_id):
        with application.client() as client:
            _run_to_done(client, project_id)
            register = client.get(f"/projects/{project_id}/register").json()

    assert register["rows"] != []
    assert "history" not in register
    assert "entries" not in register


def test_two_findings_attached_to_one_row_in_one_run_keep_one_order(
    tmp_path: Path,
) -> None:
    """Two attachments tie on time, row and cell; the entry id settles them.

    No honest test can force PostgreSQL to flip a tied order on demand, so
    this drives the two-attachment state the review named and pins that
    repeated reads agree; the determinism itself rests on the ordering's
    final `audit.id` key, stated in `read_history.py` rather than provoked.
    """
    first = one_finding()
    second = one_finding(
        rule_id="R4",
        issue="No testing outcome has been read for this requirement.",
        evidence="Not known yet",
        question="Row 1 has no testing outcome read yet. Keep this finding?",
    )
    with _project(tmp_path, examine_answer([first, second])) as (
        application,
        _folder,
        project_id,
    ):
        with application.client() as client:
            _run_to_done(client, project_id)
            reads = [
                client.get(f"/projects/{project_id}/history").json()["entries"]
                for _ in range(3)
            ]

    attached = _of_kind(reads[0], "finding attached")
    assert len(attached) == 2
    assert {entry["detail"] for entry in attached} == {
        f"{first['rule_id']} — {first['issue']}",
        f"{second['rule_id']} — {second['issue']}",
    }
    assert reads[1] == reads[0]
    assert reads[2] == reads[0]
