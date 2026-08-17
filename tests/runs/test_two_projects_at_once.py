from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    logged_run_events,
    recorded_calls,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    wait_until,
    write_script,
)
from tests.documents.register_documents import (
    examine_marker_for_register_holding,
    extract_marker,
    extraction_answer,
    match_answer,
    match_marker_for_batch_with,
    write_meeting_note,
)
from tests.register.stored_register import documents_of_run, findings_of_run, stored_rows


ALPHA_FILE = "alpha-notes.md"
BETA_FILE = "beta-notes.md"
# Deliberately absent from both documents' words, so each string reaches the
# model only through the register row it became.
ALPHA_ROW = "ALPHA an email to the operations team on intake form submit"
BETA_ROW = "BETA a doctor-wise daily schedule screen for each dentist"
ALPHA_ISSUE = (
    "The ALPHA row rests on a meeting note; no client requirements document "
    "read for that project states it in writing."
)
BETA_ISSUE = (
    "The BETA row rests on a meeting note; no client requirements document "
    "read for that project states it in writing."
)
R1 = "R1"
FIRST_ROW = 1
WHAT_WAS_ASKED_CELL = 0
SOURCE_FILE_IN_CITATION = 1
# Each scripted call holds the client for this long, so two calls started
# within it of each other were in flight at the same moment.
MODEL_DELAY_SECONDS = 2.0


def test_two_projects_running_at_once_never_appear_in_each_others_work(
    tmp_path: Path,
) -> None:
    with temporary_project_folder("alpha") as (alpha_folder, alpha_folder_path):
        with temporary_project_folder("beta") as (beta_folder, beta_folder_path):
            alpha_quote = write_meeting_note(
                alpha_folder,
                ALPHA_FILE,
                "the operations team to be notified whenever the intake form is sent",
            )
            beta_quote = write_meeting_note(
                beta_folder,
                BETA_FILE,
                "each dentist to see their own appointments for the day",
            )

            script_path = tmp_path / "script.json"
            call_log_path = tmp_path / "model-calls.jsonl"
            log_path = tmp_path / "application.log"
            write_script(
                script_path,
                {
                    extract_marker(ALPHA_FILE): extraction_answer(ALPHA_ROW, alpha_quote),
                    extract_marker(BETA_FILE): extraction_answer(BETA_ROW, beta_quote),
                    match_marker_for_batch_with(ALPHA_FILE): match_answer(1),
                    match_marker_for_batch_with(BETA_FILE): match_answer(1),
                    examine_marker_for_register_holding(ALPHA_ROW): _one_finding(
                        ALPHA_ISSUE, ALPHA_ROW
                    ),
                    examine_marker_for_register_holding(BETA_ROW): _one_finding(
                        BETA_ISSUE, BETA_ROW
                    ),
                },
            )

            with temporary_database() as database_url:
                application = ApplicationProcess(
                    database_url=database_url,
                    script_path=script_path,
                    call_log_path=call_log_path,
                    delay_seconds=MODEL_DELAY_SECONDS,
                    log_path=log_path,
                )
                application.start()
                try:
                    with application.client() as client:
                        alpha_project = _project(client, "Alpha intake portal", alpha_folder_path)
                        beta_project = _project(client, "Beta dental clinic", beta_folder_path)

                        alpha_run = _start(client, alpha_project)
                        beta_run = _start(client, beta_project)
                        stages_at_one_moment = wait_until(
                            lambda: _stages_while_both_are_running(
                                client, alpha_run, beta_run
                            ),
                            "both runs report a stage while both are running",
                        )

                        alpha_at_review = wait_for_run_status(
                            client, alpha_run, "needs review"
                        )
                        beta_at_review = wait_for_run_status(
                            client, beta_run, "needs review"
                        )
                        approve_every_decision_and_finish_review(client, alpha_run)
                        approve_every_decision_and_finish_review(client, beta_run)
                        wait_for_run_status(client, alpha_run, "done")
                        wait_for_run_status(client, beta_run, "done")

                    alpha_rows = stored_rows(database_url, alpha_project)
                    beta_rows = stored_rows(database_url, beta_project)
                    alpha_findings = findings_of_run(database_url, alpha_run)
                    beta_findings = findings_of_run(database_url, beta_run)
                    alpha_documents = documents_of_run(database_url, alpha_run)
                    beta_documents = documents_of_run(database_url, beta_run)
                finally:
                    application.stop()

    assert stages_at_one_moment is not None
    assert _overlapping_calls(call_log_path) is not None

    assert alpha_documents == [ALPHA_FILE]
    assert beta_documents == [BETA_FILE]
    assert sorted(alpha_rows) == [FIRST_ROW]
    assert sorted(beta_rows) == [FIRST_ROW]
    assert alpha_rows[FIRST_ROW].cells[WHAT_WAS_ASKED_CELL] == ALPHA_ROW
    assert beta_rows[FIRST_ROW].cells[WHAT_WAS_ASKED_CELL] == BETA_ROW
    assert {
        citation[SOURCE_FILE_IN_CITATION]
        for citation in alpha_rows[FIRST_ROW].citations
    } == {ALPHA_FILE}
    assert {
        citation[SOURCE_FILE_IN_CITATION]
        for citation in beta_rows[FIRST_ROW].citations
    } == {BETA_FILE}

    _assert_one_finding(alpha_findings, ALPHA_ISSUE, alpha_project, ALPHA_ROW, BETA_ROW)
    _assert_one_finding(beta_findings, BETA_ISSUE, beta_project, BETA_ROW, ALPHA_ROW)

    for at_review in (alpha_at_review, beta_at_review):
        assert sorted(decision["kind"] for decision in at_review["decisions"]) == [
            "export",
            "finding",
        ]
    _assert_nothing_of_the_other_project(
        alpha_at_review["decisions"], BETA_ROW, BETA_FILE
    )
    _assert_nothing_of_the_other_project(
        beta_at_review["decisions"], ALPHA_ROW, ALPHA_FILE
    )

    events = logged_run_events(log_path)
    alpha_events = [event for event in events if event["run_id"] == alpha_run]
    beta_events = [event for event in events if event["run_id"] == beta_run]
    assert alpha_events and beta_events
    for event in alpha_events:
        assert BETA_ROW not in json.dumps(event)
        assert BETA_FILE not in json.dumps(event)
    for event in beta_events:
        assert ALPHA_ROW not in json.dumps(event)
        assert ALPHA_FILE not in json.dumps(event)


def _one_finding(issue: str, row: str) -> dict[str, Any]:
    return {
        "findings": [
            {
                "rule_id": R1,
                "row_number": FIRST_ROW,
                "issue": issue,
                "evidence": f"Row #{FIRST_ROW} cites a meeting note only.",
                # Match and Examine both write their own question now, so the
                # row's own words reach the stored sentence through the model
                # rather than through anything the code composes.
                "question": (
                    "Anything built must have a written requirement. Row "
                    f"#{FIRST_ROW} — {row} — rests on a meeting note alone. "
                    f"Attach this finding to row #{FIRST_ROW}?"
                ),
            }
        ]
    }


def _project(client: httpx.Client, name: str, source_folder_path: str) -> str:
    return client.post(
        "/projects",
        json={"source_folder_path": source_folder_path},
    ).json()["project_id"]


def _start(client: httpx.Client, project_id: str) -> str:
    return client.post("/runs", json={"project_id": project_id}).json()["run_id"]


def _stages_while_both_are_running(
    client: httpx.Client,
    alpha_run: str,
    beta_run: str,
) -> tuple[str, str] | None:
    """The stage each run is in, read while both are still running.

    A run is 'running' from the moment its row is written, so the stage is what
    says work is actually under way in both at once.
    """
    alpha = client.get(f"/runs/{alpha_run}").json()
    beta = client.get(f"/runs/{beta_run}").json()
    if alpha["status"] != "running" or beta["status"] != "running":
        return None
    if alpha["stage"] is None or beta["stage"] is None:
        return None
    return alpha["stage"], beta["stage"]


def _overlapping_calls(call_log_path: Path) -> tuple[str, str] | None:
    """Two model calls, one per project, that were in flight at the same time.

    Each call holds the scripted client for the configured delay, so two calls
    started less than that apart were genuinely overlapping rather than one
    following the other.
    """
    calls = recorded_calls(call_log_path)
    alpha_calls = [call for call in calls if _belongs_to(call["marker"], ALPHA_FILE, ALPHA_ROW)]
    beta_calls = [call for call in calls if _belongs_to(call["marker"], BETA_FILE, BETA_ROW)]
    for alpha in alpha_calls:
        for beta in beta_calls:
            apart = abs((alpha["asked_at"] - beta["asked_at"]).total_seconds())
            if apart < MODEL_DELAY_SECONDS:
                return alpha["marker"], beta["marker"]
    return None


def _belongs_to(marker: str, source_file: str, row: str) -> bool:
    return source_file in marker or row in marker


def _assert_one_finding(
    findings: list[tuple[Any, ...]],
    issue: str,
    project_id: str,
    own_row: str,
    other_row: str,
) -> None:
    assert len(findings) == 1
    rule_id, found_issue, question, project_of_row, row_number = findings[0]
    assert (rule_id, found_issue, project_of_row, row_number) == (
        R1,
        issue,
        project_id,
        FIRST_ROW,
    )
    assert own_row in question
    assert other_row not in question


def _assert_nothing_of_the_other_project(
    decisions: list[dict[str, Any]],
    other_row: str,
    other_file: str,
) -> None:
    for decision in decisions:
        assert other_row not in decision["question"]
        assert other_file not in decision["question"]
