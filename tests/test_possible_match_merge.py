from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text

from conftest import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    temporary_database,
    wait_for_run_status,
    write_script,
)
from register_documents import (
    examine_marker,
    extract_marker,
    extraction_answer,
    match_answer,
    match_answer_existing_row,
    match_marker,
    match_marker_for_batch_with,
    no_findings_answer,
    write_meeting_note,
)
from examine_answers import examine_answer, one_finding


FIRST_FILE = "meeting-note.md"
SECOND_FILE = "follow-up-note.md"
FIRST_REQUIREMENT = "an email to the operations team on intake form submit"
SECOND_REQUIREMENT = "a notification to operations when the intake form is sent"
COMMITTED_ROW_NUMBER = 1
PROPOSED_ROW_NUMBER = 2


def test_approved_possible_match_merges_into_the_existing_row(
    tmp_path: Path,
) -> None:
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    first_quote = write_meeting_note(source_folder, FIRST_FILE, FIRST_REQUIREMENT)
    script_path = tmp_path / "script.json"
    write_script(
        script_path,
        {
            # The batch-specific marker comes first: the second run's register
            # view repeats the first run's requirement, so the general Match
            # marker matches both prompts.
            match_marker_for_batch_with(SECOND_FILE): match_answer_existing_row(
                COMMITTED_ROW_NUMBER
            ),
            match_marker(): match_answer(1),
            examine_marker(): no_findings_answer(),
            extract_marker(FIRST_FILE): extraction_answer(
                FIRST_REQUIREMENT, first_quote
            ),
            extract_marker(SECOND_FILE): extraction_answer(
                SECOND_REQUIREMENT,
                f"The client asked for {SECOND_REQUIREMENT}.",
            ),
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
                    json={
                        "name": "Merging intake portal",
                        "source_folder_path": str(source_folder),
                    },
                ).json()["project_id"]

                first_run = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                wait_for_run_status(client, first_run, "waiting for review")
                approve_every_decision_and_finish_review(client, first_run)
                wait_for_run_status(client, first_run, "done")

                write_meeting_note(source_folder, SECOND_FILE, SECOND_REQUIREMENT)
                second_run = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                at_review = wait_for_run_status(
                    client, second_run, "waiting for review"
                )
                merge_decisions = [
                    decision
                    for decision in at_review["decisions"]
                    if decision["kind"] == "possible match"
                ]
                approve_every_decision_and_finish_review(client, second_run)
                wait_for_run_status(client, second_run, "done")
                export = client.get(f"/runs/{second_run}/export").json()
        finally:
            application.stop()

        engine = create_engine(database_url)
        with engine.connect() as connection:
            proposals = connection.execute(
                text(
                    "SELECT is_committed, merged_into_register_row_id FROM "
                    "register_rows WHERE proposed_by_run_id = :run_id"
                ),
                {"run_id": second_run},
            ).all()
            committed_row_id = connection.execute(
                text(
                    "SELECT id FROM register_rows WHERE row_number = :row_number "
                    "AND is_committed"
                ),
                {"row_number": COMMITTED_ROW_NUMBER},
            ).scalar_one()
        engine.dispose()

    assert len(merge_decisions) == 1
    assert FIRST_REQUIREMENT in merge_decisions[0]["question"]
    # The register keeps one row for one requirement, and its evidence is both
    # documents rather than the second document's alone.
    assert [row["row_number"] for row in export["rows"]] == [COMMITTED_ROW_NUMBER]
    assert export["rows"][0]["cells"]["what_was_asked"] == FIRST_REQUIREMENT
    cited_files = {
        citation["source_file"] for citation in export["rows"][0]["citations"]
    }
    assert cited_files == {FIRST_FILE, SECOND_FILE}
    # The proposal is kept and marked, so the decision still points at what the
    # Delivery Owner was shown.
    assert [(row.is_committed, row.merged_into_register_row_id) for row in proposals] == [
        (False, committed_row_id)
    ]


def test_a_finding_on_a_merged_proposal_reports_the_row_it_ended_up_on(
    tmp_path: Path,
) -> None:
    """A finding follows its row through the merge, and so must its number.

    Reporting the proposal's number while sitting under the committed row tells
    the Delivery Owner two different things about the same finding.
    """
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    first_quote = write_meeting_note(source_folder, FIRST_FILE, FIRST_REQUIREMENT)
    script_path = tmp_path / "script.json"
    write_script(
        script_path,
        {
            match_marker_for_batch_with(SECOND_FILE): match_answer_existing_row(
                COMMITTED_ROW_NUMBER
            ),
            match_marker(): match_answer(1),
            extract_marker(FIRST_FILE): extraction_answer(
                FIRST_REQUIREMENT, first_quote
            ),
            extract_marker(SECOND_FILE): extraction_answer(
                SECOND_REQUIREMENT,
                f"The client asked for {SECOND_REQUIREMENT}.",
            ),
            # Only the second run's register holds the proposed row, so keying
            # on its requirement puts the finding on that run alone; the first
            # run falls through to the empty answer below.
            SECOND_REQUIREMENT: examine_answer(
                [one_finding(rule_id="R1", row_number=PROPOSED_ROW_NUMBER)]
            ),
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
                    "/projects",
                    json={
                        "name": "Merging intake portal with a finding",
                        "source_folder_path": str(source_folder),
                    },
                ).json()["project_id"]

                first_run = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                wait_for_run_status(client, first_run, "waiting for review")
                approve_every_decision_and_finish_review(client, first_run)
                wait_for_run_status(client, first_run, "done")

                write_meeting_note(source_folder, SECOND_FILE, SECOND_REQUIREMENT)
                second_run = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                wait_for_run_status(client, second_run, "waiting for review")
                approve_every_decision_and_finish_review(client, second_run)
                wait_for_run_status(client, second_run, "done")
                export = client.get(f"/runs/{second_run}/export").json()
                status = client.get(f"/runs/{second_run}").json()
        finally:
            application.stop()

    exported_row = export["rows"][0]
    assert exported_row["row_number"] == COMMITTED_ROW_NUMBER
    assert len(exported_row["findings"]) == 1
    # The finding sits under row 1, so every number it carries must say row 1.
    assert exported_row["findings"][0]["row_number"] == COMMITTED_ROW_NUMBER
    assert [
        finding["row_number"] for finding in export["examine"]["findings"]
    ] == [COMMITTED_ROW_NUMBER]
    assert [
        finding["row_number"] for finding in status["examine"]["findings"]
    ] == [COMMITTED_ROW_NUMBER]
