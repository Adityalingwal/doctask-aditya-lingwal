from __future__ import annotations

from pathlib import Path

from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    extraction_answer,
    feedback_extraction_answer,
    match_answer,
    match_answer_existing_row,
    match_marker,
    match_marker_for_batch_with,
    observation_answer_of,
    observation_marker,
    several_requirements_answer,
    write_document_stating,
    write_meeting_note,
)
from tests.examine.answers import examine_answer, one_finding
from tests.examine.rules_files import rules_that_always_apply
from tests.interfaces.mcp_client import call_tool
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
REQUIREMENTS_FILE = "client-requirements-v1.md"
FEEDBACK_FILE = "testing-feedback-12-aug.md"
FIRST_ASK = "an email to the operations team on intake form submit"
SECOND_ASK = "a search over old intake records"
RESTATED_QUOTE = "The operations email must go out on every submit."
FEEDBACK_QUOTE = "The search returned every old record we looked for."
FEEDBACK_VERDICT = "the search returned every old record"
ISSUE_LINE = (
    "testing-feedback-12-aug.md was read, and it says nothing about this "
    "requirement."
)


def test_decisions_come_back_ordered_by_row_then_kind_from_both_doors(
    tmp_path: Path,
) -> None:
    """One order, fixed in the read (S23), so no surface has to sort.

    Row 1 raises a possible match, row 2 an observation match, and row 1 also
    a finding — so an order by row alone and an order by kind alone give
    different answers, and only the locked pair gives this one.
    """
    with temporary_project_folder("decision-order") as (source_folder, folder_path):
        first_quote = write_meeting_note(source_folder, FIRST_NOTE, FIRST_ASK)
        second_quote = write_meeting_note(source_folder, SECOND_NOTE, SECOND_ASK)
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                extract_marker(FIRST_NOTE): extraction_answer(FIRST_ASK, first_quote),
                extract_marker(SECOND_NOTE): extraction_answer(
                    SECOND_ASK, second_quote
                ),
                extract_marker(REQUIREMENTS_FILE): several_requirements_answer(
                    [(FIRST_ASK, RESTATED_QUOTE)], "client requirements document"
                ),
                extract_marker(FEEDBACK_FILE): feedback_extraction_answer(
                    [(FEEDBACK_VERDICT, "Passed", FEEDBACK_QUOTE)]
                ),
                match_marker_for_batch_with(
                    REQUIREMENTS_FILE
                ): match_answer_existing_row(1),
                match_marker(): match_answer(2),
                observation_marker(): observation_answer_of([2]),
                examine_marker(): examine_answer(
                    [
                        one_finding(
                            rule_id="R4",
                            row_number=1,
                            issue=ISSUE_LINE,
                            evidence="Not mentioned",
                        )
                    ]
                ),
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
                        REQUIREMENTS_FILE,
                        "12 March 2026",
                        [RESTATED_QUOTE],
                    )
                    write_document_stating(
                        source_folder,
                        FEEDBACK_FILE,
                        "12 August 2026",
                        [FEEDBACK_QUOTE],
                    )
                    second_run = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    over_http = wait_for_run_status(client, second_run, "needs review")
                    through_mcp = call_tool(
                        application.base_url,
                        "get_run_status",
                        {"run_id": second_run},
                    ).payload
            finally:
                application.stop()

    ordered = [
        (decision["row_number"], decision["kind"])
        for decision in over_http["decisions"]
    ]
    assert ordered == [(1, "possible match"), (1, "finding"), (2, "observation match")]
    # The screen never re-sorts, so the second door has to agree exactly.
    assert over_http["decisions"] == through_mcp["decisions"]
