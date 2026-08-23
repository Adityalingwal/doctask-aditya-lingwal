from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from psycopg import AsyncConnection
from sqlalchemy import create_engine, text

from app.database import build_connection_pool
from app.examine.read_findings import findings_of_run
from app.register.cells import (
    CELL_NAMES,
    IN_WRITING_NOT_KNOWN_YET,
    STATUS_REQUESTED,
    TESTING_NOT_KNOWN_YET,
)
from app.review.review_queue import APPROVED, FINDING_DECISION
from app.runs.statuses import DONE

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


def test_a_finding_raised_while_a_match_is_unanswered_names_the_row_it_will_join(
    tmp_path: Path,
) -> None:
    """Examine judges the candidate, so its finding names the candidate.

    The proposal waiting on the match answer is not a row of its own here
    (item 21), so nothing can raise a finding against a number that is about
    to be merged away. The same rule ran in both runs, so the register shows
    the newer run's answer and only that one.
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
                # Both runs are judged against the same one row, and both raise
                # the same rule against it — which is what makes the register's
                # "one finding per rule per row" visible here.
                examine_marker(): examine_answer(
                    [one_finding(rule_id="R1", row_number=COMMITTED_ROW_NUMBER)]
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
                    wait_for_run_status(client, second_run, "needs review")
                    approve_every_decision_and_finish_review(client, second_run)
                    wait_for_run_status(client, second_run, "done")
                    export = client.get(f"/projects/{project_id}/register").json()
                    status = client.get(f"/runs/{second_run}").json()
            finally:
                application.stop()

    exported_row = export["rows"][0]
    assert exported_row["row_number"] == COMMITTED_ROW_NUMBER
    # Two runs raised this rule against this row; the register shows the
    # newer answer, once.
    assert len(exported_row["findings"]) == 1
    assert exported_row["findings"][0]["row_number"] == COMMITTED_ROW_NUMBER
    assert exported_row["findings"][0]["raised_by_run"] == 2
    assert [
        finding["row_number"] for finding in export["examine"]["findings"]
    ] == [COMMITTED_ROW_NUMBER]
    assert [
        finding["row_number"] for finding in status["examine"]["findings"]
    ] == [COMMITTED_ROW_NUMBER]


def test_a_finding_stored_against_a_merged_proposal_reports_the_surviving_row(
) -> None:
    """A finding follows its row through the merge, and so must its number.

    Reporting the proposal's number while sitting under the committed row
    tells the Delivery Owner two different things about one finding.
    """
    reported = asyncio.run(_read_a_finding_left_on_a_merged_proposal())

    assert [finding["row_number"] for finding in reported] == [COMMITTED_ROW_NUMBER]


async def _read_a_finding_left_on_a_merged_proposal() -> list[dict[str, Any]]:
    with temporary_database() as database_url:
        pool = build_connection_pool(database_url)
        await pool.open(wait=True)
        try:
            async with pool.connection() as connection:
                run_id = await _seed_a_merged_proposal_with_a_finding(connection)
                return await findings_of_run(
                    connection, run_id, approved_only=True
                )
        finally:
            await pool.close()


async def _seed_a_merged_proposal_with_a_finding(
    connection: AsyncConnection,
) -> UUID:
    project_id, run_id = uuid4(), uuid4()
    await connection.execute(
        "INSERT INTO projects (id, name, source_folder_path) VALUES (%s, %s, %s)",
        (project_id, f"Merged {project_id}", f"sample-projects/merged-{project_id}"),
    )
    await connection.execute(
        "INSERT INTO runs (id, project_id, status) VALUES (%s, %s, %s)",
        (run_id, project_id, DONE),
    )
    survivor = await _insert_row(
        connection, project_id, run_id, COMMITTED_ROW_NUMBER, True, None
    )
    proposal = await _insert_row(
        connection, project_id, run_id, PROPOSED_ROW_NUMBER, False, survivor
    )
    decision_id = uuid4()
    question = f"Does row #{PROPOSED_ROW_NUMBER} break this rule?"
    await connection.execute(
        "INSERT INTO decisions (id, run_id, kind, question, outcome, decided_at) "
        "VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)",
        (decision_id, run_id, FINDING_DECISION, question, APPROVED),
    )
    await connection.execute(
        "INSERT INTO findings (id, run_id, register_row_id, rule_id, rule_text, "
        "issue, evidence, question, decision_key) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            uuid4(),
            run_id,
            proposal,
            "R1",
            "Anything built must have a written requirement.",
            "This row rests on a meeting note alone.",
            "Not known yet",
            question,
            decision_id,
        ),
    )
    return run_id


async def _insert_row(
    connection: AsyncConnection,
    project_id: UUID,
    run_id: UUID,
    row_number: int,
    is_committed: bool,
    merged_into: UUID | None,
) -> UUID:
    row_id = uuid4()
    await connection.execute(
        "INSERT INTO register_rows (id, project_id, "
        + ", ".join(CELL_NAMES)
        + ", fingerprint, row_number, proposed_by_run_id, is_committed, "
        "merged_into_register_row_id) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            row_id,
            project_id,
            f"Requirement {row_number}.",
            IN_WRITING_NOT_KNOWN_YET,
            TESTING_NOT_KNOWN_YET,
            STATUS_REQUESTED,
            f"fingerprint-{row_number}",
            row_number,
            run_id,
            is_committed,
            merged_into,
        ),
    )
    return row_id
