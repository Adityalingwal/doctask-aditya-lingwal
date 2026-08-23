from __future__ import annotations

import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx

from tests.examine.rules_files import rules_that_always_apply
from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision,
    approve_every_decision_and_finish_review,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)
from tests.documents.register_documents import (
    examine_marker,
    examine_marker_for_register_holding,
    extract_marker,
    extraction_answer,
    match_answer,
    match_answer_of,
    match_marker,
    match_marker_against_an_empty_register,
    no_findings_answer,
    write_meeting_note,
)
from tests.examine.answers import R1_ISSUE, examine_answer, one_finding

FIRST_FILE = "meeting-notes-10-mar.md"
SECOND_FILE = "meeting-notes-20-mar.md"
FIRST_REQUIREMENT = "an email to the operations team on intake form submit"
SECOND_REQUIREMENT = "the same notification sent over WhatsApp"
COMMITTED_ROW = 1


@contextmanager
def _committed_row_and_a_second_document(
    tmp_path: Path,
) -> Iterator[tuple[ApplicationProcess, str, Path, Path]]:
    """A project whose second run will raise a finding against committed row 1."""
    with temporary_project_folder("finding-follows-ending") as (
        source_folder,
        source_folder_path,
    ):
        waiting_folder = tmp_path / "not-yet-delivered"
        waiting_folder.mkdir()

        first_quote = write_meeting_note(source_folder, FIRST_FILE, FIRST_REQUIREMENT)
        second_quote = write_meeting_note(
            waiting_folder, SECOND_FILE, SECOND_REQUIREMENT
        )

        script_path = tmp_path / "script.json"
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
                # The scripted client answers the first marker found in the
                # prompt, in insertion order: only the second run's Examine
                # sees a register holding the second requirement, so only it
                # raises the finding — the first run commits a clean row.
                examine_marker_for_register_holding(
                    SECOND_REQUIREMENT
                ): examine_answer([one_finding(row_number=COMMITTED_ROW)]),
                examine_marker(): no_findings_answer(),
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
                        "/projects",
                        json={"source_folder_path": source_folder_path},
                    ).json()["project_id"]
                yield application, project_id, source_folder, waiting_folder
            finally:
                application.stop()


def _first_run_to_done(client: httpx.Client, project_id: str) -> None:
    run_id = client.post("/runs", json={"project_id": project_id}).json()["run_id"]
    wait_for_run_status(client, run_id, "needs review")
    approve_every_decision_and_finish_review(client, run_id)
    wait_for_run_status(client, run_id, "done")


def _second_run_at_review_with_its_finding_approved(
    client: httpx.Client,
    project_id: str,
    source_folder: Path,
    waiting_folder: Path,
) -> str:
    shutil.copy(waiting_folder / SECOND_FILE, source_folder / SECOND_FILE)
    run_id = client.post("/runs", json={"project_id": project_id}).json()["run_id"]
    wait_for_run_status(client, run_id, "needs review")
    approve_every_decision(client, run_id)
    return run_id


def _register_findings(client: httpx.Client, project_id: str) -> list[str]:
    register = client.get(f"/projects/{project_id}/register").json()
    return [
        finding["issue"] for row in register["rows"] for finding in row["findings"]
    ]


def test_a_finding_approved_while_its_run_is_at_review_stays_out_of_the_register(
    tmp_path: Path,
) -> None:
    with _committed_row_and_a_second_document(tmp_path) as (
        application,
        project_id,
        source_folder,
        waiting_folder,
    ):
        with application.client() as client:
            _first_run_to_done(client, project_id)
            second_run = _second_run_at_review_with_its_finding_approved(
                client, project_id, source_folder, waiting_folder
            )
            while_at_review = _register_findings(client, project_id)

            client.post(
                f"/runs/{second_run}/finish-review",
                json={"add_to_register": True},
            ).raise_for_status()
            wait_for_run_status(client, second_run, "done")
            after_done = _register_findings(client, project_id)

    # The press is the gate: nothing the run proposed — row or finding —
    # reaches the register before it, everything approved reaches it after.
    assert while_at_review == []
    assert after_done == [R1_ISSUE]


def test_a_discarded_runs_approved_finding_never_reaches_the_register(
    tmp_path: Path,
) -> None:
    with _committed_row_and_a_second_document(tmp_path) as (
        application,
        project_id,
        source_folder,
        waiting_folder,
    ):
        with application.client() as client:
            _first_run_to_done(client, project_id)
            second_run = _second_run_at_review_with_its_finding_approved(
                client, project_id, source_folder, waiting_folder
            )

            client.post(
                f"/runs/{second_run}/finish-review",
                json={"add_to_register": False},
            ).raise_for_status()
            wait_for_run_status(client, second_run, "discarded")
            after_discard = _register_findings(client, project_id)

    # Discarding a run leaves the register unchanged — its finding too.
    assert after_discard == []
