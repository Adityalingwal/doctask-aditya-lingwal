from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text

from tests.examine.rules_files import rules_that_always_apply
from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
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
    match_answer_existing_row,
    match_marker,
    match_marker_for_batch_with,
    no_findings_answer,
    write_meeting_note,
)
from tests.examine.answers import examine_answer, one_finding


FIRST_FILE = "meeting-note.md"
SECOND_FILE = "follow-up-note.md"
FIRST_REQUIREMENT = "an email to the operations team on intake form submit"
SECOND_REQUIREMENT = "a notification to operations when the intake form is sent"
COMMITTED_ROW_NUMBER = 1
PROPOSED_ROW_NUMBER = 2
# Match is certain the two are one ask. It still writes the sentence, because
# a confident match against a row already in the register is downgraded into
# the same possible-match decision an uncertain one raises.
CONFIDENT_MATCH_QUESTION = (
    f"This ask was raised in meeting notes ({FIRST_FILE}) — row "
    f"#{COMMITTED_ROW_NUMBER}, {FIRST_REQUIREMENT}. It is stated again in "
    f"{SECOND_FILE} as {SECOND_REQUIREMENT}. Is this the same ask?"
)


def test_approved_possible_match_merges_into_the_existing_row(
    tmp_path: Path,
) -> None:
    with temporary_project_folder("merging") as (source_folder, source_folder_path):
        first_quote = write_meeting_note(source_folder, FIRST_FILE, FIRST_REQUIREMENT)
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                # The batch-specific marker comes first: the second run's register
                # view repeats the first run's requirement, so the general Match
                # marker matches both prompts.
                match_marker_for_batch_with(SECOND_FILE): match_answer_existing_row(
                    COMMITTED_ROW_NUMBER, CONFIDENT_MATCH_QUESTION
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
                rules_config_path=rules_that_always_apply(tmp_path),
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

                    write_meeting_note(source_folder, SECOND_FILE, SECOND_REQUIREMENT)
                    second_run = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    at_review = wait_for_run_status(
                        client, second_run, "needs review"
                    )
                    merge_decisions = [
                        decision
                        for decision in at_review["decisions"]
                        if decision["kind"] == "possible match"
                    ]
                    approve_every_decision_and_finish_review(client, second_run)
                    wait_for_run_status(client, second_run, "done")
                    export = client.get(f"/projects/{project_id}/register").json()
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
    # The model's own sentence reaches the card unchanged — nothing composed
    # it from the row and the requirement after the fact.
    assert merge_decisions[0]["question"] == CONFIDENT_MATCH_QUESTION
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


def test_an_unsure_match_is_still_asked_about_rather_than_merged(
    tmp_path: Path,
) -> None:
    """D09: a confident 'existing row' answer is downgraded to this same gate.

    Rejecting it must leave the two requirements as two separate rows — the
    system never decides a possible match on its own, and never silently
    merges what it is unsure about.
    """
    with temporary_project_folder("unsure-match") as (source_folder, source_folder_path):
        first_quote = write_meeting_note(source_folder, FIRST_FILE, FIRST_REQUIREMENT)
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                match_marker_for_batch_with(SECOND_FILE): match_answer_existing_row(
                    COMMITTED_ROW_NUMBER, CONFIDENT_MATCH_QUESTION
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
                rules_config_path=rules_that_always_apply(tmp_path),
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

                    write_meeting_note(source_folder, SECOND_FILE, SECOND_REQUIREMENT)
                    second_run = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    at_review = wait_for_run_status(
                        client, second_run, "needs review"
                    )
                    match_decision = next(
                        decision
                        for decision in at_review["decisions"]
                        if decision["kind"] == "possible match"
                    )
                    for decision in at_review["decisions"]:
                        outcome = (
                            "rejected"
                            if decision["decision_id"] == match_decision["decision_id"]
                            else "approved"
                        )
                        client.post(
                            f"/runs/{second_run}/decisions",
                            json={
                                "decision_id": decision["decision_id"],
                                "outcome": outcome,
                            },
                        ).raise_for_status()
                    client.post(
                        f"/runs/{second_run}/finish-review",
                        json={"add_to_register": True},
                    ).raise_for_status()
                    wait_for_run_status(client, second_run, "done")
                    export = client.get(f"/projects/{project_id}/register").json()
            finally:
                application.stop()

            engine = create_engine(database_url)
            with engine.connect() as connection:
                proposal = connection.execute(
                    text(
                        "SELECT is_committed, merged_into_register_row_id FROM "
                        "register_rows WHERE proposed_by_run_id = :run_id"
                    ),
                    {"run_id": second_run},
                ).one()
            engine.dispose()

    assert match_decision["question"] == CONFIDENT_MATCH_QUESTION
    assert FIRST_REQUIREMENT in match_decision["question"]
    # A rejected match stays a row of its own — committed, never merged.
    assert proposal.is_committed is True
    assert proposal.merged_into_register_row_id is None
    assert [row["row_number"] for row in export["rows"]] == [
        COMMITTED_ROW_NUMBER,
        PROPOSED_ROW_NUMBER,
    ]


def test_a_finding_on_a_merged_proposal_reports_the_row_it_ended_up_on(
    tmp_path: Path,
) -> None:
    """A finding follows its row through the merge, and so must its number.

    Reporting the proposal's number while sitting under the committed row tells
    the Delivery Owner two different things about the same finding.
    """
    with temporary_project_folder("merging-with-finding") as (source_folder, source_folder_path):
        first_quote = write_meeting_note(source_folder, FIRST_FILE, FIRST_REQUIREMENT)
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                match_marker_for_batch_with(SECOND_FILE): match_answer_existing_row(
                    COMMITTED_ROW_NUMBER, CONFIDENT_MATCH_QUESTION
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
                rules_config_path=rules_that_always_apply(tmp_path),
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

                    write_meeting_note(source_folder, SECOND_FILE, SECOND_REQUIREMENT)
                    second_run = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    wait_for_run_status(client, second_run, "needs review")
                    approve_every_decision_and_finish_review(client, second_run)
                    wait_for_run_status(client, second_run, "done")
                    export = client.get(f"/projects/{project_id}/register").json()
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
