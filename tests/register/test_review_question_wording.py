from __future__ import annotations

from pathlib import Path

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
    feedback_extraction_answer,
    match_answer,
    match_marker,
    no_findings_answer,
    observation_answer_of,
    observation_marker,
    write_document_stating,
    write_meeting_note,
)
from tests.examine.answers import examine_answer, one_finding


# Never-do tests for the review question's new wording (handoff/brief-folder-
# is-a-project-and-register-moves.md, section 2.5). Written and run against
# `main` at `a436393` before any implementation, per that brief's protocol.

SOURCE_FILE = "meeting-note.md"
REQUIREMENT = "an email to the operations team on intake form submit"
NEW_WORDING = "Add this run's changes to the register?"


def test_the_review_question_asks_to_add_the_runs_changes_not_to_export(
    tmp_path: Path,
) -> None:
    with temporary_project_folder("review-wording") as (source_folder, folder_path):
        quote = write_meeting_note(source_folder, SOURCE_FILE, REQUIREMENT)
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                match_marker(): match_answer(1),
                examine_marker(): no_findings_answer(),
                extract_marker(SOURCE_FILE): extraction_answer(REQUIREMENT, quote),
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
                        "/projects", json={"source_folder_path": folder_path}
                    ).json()["project_id"]
                    run_id = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    waiting = wait_for_run_status(client, run_id, "needs review")
                    # The wording is what the person read on the button, so
                    # it is read back from the decision the press wrote.
                    client.post(
                        f"/runs/{run_id}/finish-review",
                        json={"add_to_register": True},
                    ).raise_for_status()
                    finished = client.get(f"/runs/{run_id}").json()
            finally:
                application.stop()

        assert waiting["decisions"] == []
        export_decision = next(
            decision
            for decision in finished["decisions"]
            if decision["kind"] == "export"
        )
        assert export_decision["question"] == NEW_WORDING


def test_a_rules_only_run_reaches_review_with_the_same_question(
    tmp_path: Path,
) -> None:
    """The zero-proposed-rows case: a run that only re-examines the register
    under changed rules — no new document, no match decision — must still
    record this exact question when it ends, because it still commits merges
    and findings with no human approval otherwise."""
    with temporary_project_folder("rules-only-review-wording") as (
        source_folder,
        folder_path,
    ):
        quote = write_meeting_note(source_folder, SOURCE_FILE, REQUIREMENT)
        rules_config_path = tmp_path / "rules.yaml"
        rules_config_path.write_text(
            "rules:\n  - id: R1\n    text: \"Anything built must be written "
            "down.\"\n",
            encoding="utf-8",
        )
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                match_marker(): match_answer(1),
                examine_marker(): no_findings_answer(),
                extract_marker(SOURCE_FILE): extraction_answer(REQUIREMENT, quote),
            },
        )
        with temporary_database() as database_url:
            application = ApplicationProcess(
                database_url=database_url,
                script_path=script_path,
                call_log_path=tmp_path / "model-calls.jsonl",
                rules_config_path=rules_config_path,
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

                    # No new document arrives; only the rules change, so the
                    # next run re-examines the whole register with an empty
                    # batch (app/graph/register_graph.py's examine_changed_rules
                    # path) and proposes no row at all.
                    rules_config_path.write_text(
                        "rules:\n  - id: R1\n    text: \"Anything built must be "
                        "written down.\"\n  - id: R9\n    text: \"Every "
                        "requirement names the person who asked for it.\"\n",
                        encoding="utf-8",
                    )
                    second_run = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    waiting = wait_for_run_status(client, second_run, "needs review")
                    client.post(
                        f"/runs/{second_run}/finish-review",
                        json={"add_to_register": True},
                    ).raise_for_status()
                    finished = client.get(f"/runs/{second_run}").json()
            finally:
                application.stop()

        # No decision at all while it waits — no match and no finding raised
        # this run — is the check that this really is the zero-proposed-rows
        # case, and the gate the press writes carries the same wording there.
        assert waiting["decisions"] == []
        assert [decision["kind"] for decision in finished["decisions"]] == ["export"]
        assert finished["decisions"][0]["question"] == NEW_WORDING


# The three shapes a person reads, locked 2026-08-23. Every line but the
# finding's issue is built by the backend, so each is written out here whole:
# a shape that drifts by one character fails, which is the point.
ROW_ASK = "an email to the operations team on intake form submit"
FEEDBACK_FILE = "testing-feedback-12-aug.md"
REQUIREMENTS_FILE = "client-requirements-v1.md"
FIRST_FINDING_QUOTE = "The notification email arrived every time we submitted."
SECOND_FINDING_QUOTE = "The subject line matched the wording we agreed."
FIRST_VERDICT = "the notification email arrived on every submit"
SECOND_VERDICT = "the subject line matched what was agreed"
UNRELATED_QUOTE = "Testing also asked for an SMS summary after each chat."
UNRELATED_ASK = "an SMS summary after each chat"
RULE_TEXT = "Every written requirement must have a testing outcome."
ISSUE_LINE = (
    "testing-feedback-12-aug.md was read, and it says nothing about this "
    "requirement."
)


def test_an_observation_match_shows_one_block_per_quote_under_one_question(
    tmp_path: Path,
) -> None:
    """Two observations on one row are one decision carrying two quote blocks.

    Stitching them into one paragraph showed a person a sentence nobody wrote
    (item 42); each keeps its own source line and its own words.
    """
    with temporary_project_folder("observation-wording") as (
        source_folder,
        folder_path,
    ):
        quote = write_meeting_note(source_folder, SOURCE_FILE, ROW_ASK)
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                extract_marker(SOURCE_FILE): extraction_answer(ROW_ASK, quote),
                extract_marker(FEEDBACK_FILE): feedback_extraction_answer(
                    [
                        (FIRST_VERDICT, "Passed", FIRST_FINDING_QUOTE),
                        (SECOND_VERDICT, "Passed", SECOND_FINDING_QUOTE),
                    ]
                ),
                observation_marker(): observation_answer_of([1, 1]),
                match_marker(): match_answer(1),
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
                        FEEDBACK_FILE,
                        "12 August 2026",
                        [FIRST_FINDING_QUOTE, SECOND_FINDING_QUOTE],
                    )
                    second_run = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    waiting = wait_for_run_status(client, second_run, "needs review")
            finally:
                application.stop()

    decision = _one_decision_of_kind(waiting, "observation match")
    assert decision["question"] == (
        "Register row 1\n"
        f"What was asked: {ROW_ASK}\n"
        "Written down: Not known yet\n"
        "What testing found: Not known yet\n"
        "Status: Requested\n"
        "\n"
        f'{FEEDBACK_FILE}, under "Discussion", says:\n'
        f'"{FIRST_FINDING_QUOTE}"\n'
        "\n"
        f'{FEEDBACK_FILE}, under "Discussion", says:\n'
        f'"{SECOND_FINDING_QUOTE}"\n'
        "\n"
        "Is this about row 1?\n"
        "\n"
        f"Approve → Row 1 changes: What testing found: {FIRST_VERDICT} "
        f"{SECOND_VERDICT}  Status: Done\n"
        "Reject → Row 1 stays as it is."
    )
    # The parts the screen and an MCP caller lay out, beside the whole text.
    assert [quote_block["quote"] for quote_block in decision["quotes"]] == [
        FIRST_FINDING_QUOTE,
        SECOND_FINDING_QUOTE,
    ]
    assert decision["row"]["label"] == "Register row 1"
    # Only the cells that change, and no old value beside them.
    assert decision["if_approved"] == [
        {"cell": "What testing found", "value": f"{FIRST_VERDICT} {SECOND_VERDICT}"},
        {"cell": "Status", "value": "Done"},
    ]
    assert decision["if_rejected"] == "Row 1 stays as it is."


def test_a_finding_wraps_the_models_issue_line_and_writes_every_other_line(
    tmp_path: Path,
) -> None:
    """The rule, the row, the question and both answers are the backend's.

    Only the issue line is the model's, because only the rule can say what
    breaking it looks like (S27).
    """
    rules_config_path = tmp_path / "rules.yaml"
    rules_config_path.write_text(
        f'rules:\n  - id: R4\n    text: "{RULE_TEXT}"\n', encoding="utf-8"
    )
    with temporary_project_folder("finding-wording") as (source_folder, folder_path):
        quote = write_meeting_note(source_folder, SOURCE_FILE, ROW_ASK)
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                extract_marker(SOURCE_FILE): extraction_answer(ROW_ASK, quote),
                extract_marker(FEEDBACK_FILE): feedback_extraction_answer(
                    [(UNRELATED_ASK, "Change request", UNRELATED_QUOTE)]
                ),
                observation_marker(): observation_answer_of([None]),
                match_marker(): match_answer(1),
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
                rules_config_path=rules_config_path,
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
                        FEEDBACK_FILE,
                        "12 August 2026",
                        [UNRELATED_QUOTE],
                    )
                    second_run = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    waiting = wait_for_run_status(client, second_run, "needs review")
                    skipped = waiting["skipped"]
            finally:
                application.stop()

    decision = _one_decision_of_kind(waiting, "finding")
    assert decision["question"] == (
        "Register row 1\n"
        f"What was asked: {ROW_ASK}\n"
        "Written down: Not known yet\n"
        "What testing found: Not mentioned\n"
        "Status: Requested\n"
        "\n"
        f"Rule: {RULE_TEXT}\n"
        "\n"
        f"{ISSUE_LINE}\n"
        "\n"
        "Does row 1 break this rule?\n"
        "\n"
        "Approve → The finding is added to row 1.\n"
        "Reject → The finding is not added."
    )
    assert decision["rule_text"] == RULE_TEXT
    assert decision["issue"] == ISSUE_LINE
    assert decision["quotes"] == []
    assert decision["if_approved"] == []
    assert decision["if_rejected"] == "The finding is not added."

    # The observation that reached no row is shown as itself, with the place
    # it was actually found (S12's first shape).
    not_attached = [entry for entry in skipped if entry["kind"] == "not attached"]
    assert len(not_attached) == 1
    assert not_attached[0]["summary"] == UNRELATED_ASK
    assert not_attached[0]["source_line"] == (
        f'{FEEDBACK_FILE}, under "Discussion"'
    )
    assert not_attached[0]["reason"] == (
        "This is not about any requirement in the register."
    )


def _one_decision_of_kind(run: dict, kind: str) -> dict:
    matching = [
        decision for decision in run["decisions"] if decision["kind"] == kind
    ]
    assert len(matching) == 1
    return matching[0]


SECOND_FEEDBACK_FILE = "testing-feedback-19-aug.md"
LATER_FINDING_QUOTE = "The email arrived again on every submit we tried this week."
LATER_VERDICT = "the notification email still arrived on every submit"


def test_the_approve_line_names_only_the_cells_commit_will_actually_write(
    tmp_path: Path,
) -> None:
    """A row already `Done` gets a second passing report: Status is not promised.

    Commit skips a cell whose value has not changed, so a line promising
    `Status: Done` on a row that is already Done would show a change that
    never happens — the promise and the write must come from one comparison.
    """
    with temporary_project_folder("approve-line-only-changes") as (
        source_folder,
        folder_path,
    ):
        quote = write_meeting_note(source_folder, SOURCE_FILE, ROW_ASK)
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                extract_marker(SOURCE_FILE): extraction_answer(ROW_ASK, quote),
                extract_marker(FEEDBACK_FILE): feedback_extraction_answer(
                    [(FIRST_VERDICT, "Passed", FIRST_FINDING_QUOTE)]
                ),
                extract_marker(SECOND_FEEDBACK_FILE): feedback_extraction_answer(
                    [(LATER_VERDICT, "Passed", LATER_FINDING_QUOTE)]
                ),
                observation_marker(): observation_answer_of([1]),
                match_marker(): match_answer(1),
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
                        "/projects", json={"source_folder_path": folder_path}
                    ).json()["project_id"]
                    for feedback_file, feedback_quote in (
                        (None, None),
                        (FEEDBACK_FILE, FIRST_FINDING_QUOTE),
                    ):
                        if feedback_file is not None:
                            write_document_stating(
                                source_folder,
                                feedback_file,
                                "12 August 2026",
                                [feedback_quote],
                            )
                        run_id = client.post(
                            "/runs", json={"project_id": project_id}
                        ).json()["run_id"]
                        wait_for_run_status(client, run_id, "needs review")
                        approve_every_decision_and_finish_review(client, run_id)
                        wait_for_run_status(client, run_id, "done")

                    write_document_stating(
                        source_folder,
                        SECOND_FEEDBACK_FILE,
                        "19 August 2026",
                        [LATER_FINDING_QUOTE],
                    )
                    third_run = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    waiting = wait_for_run_status(client, third_run, "needs review")
            finally:
                application.stop()

    decision = _one_decision_of_kind(waiting, "observation match")
    assert decision["if_approved"] == [
        {"cell": "What testing found", "value": LATER_VERDICT},
    ]
    assert decision["question"].endswith(
        f"Approve → Row 1 changes: What testing found: {LATER_VERDICT}\n"
        "Reject → Row 1 stays as it is."
    )


def test_a_quote_spanning_two_paragraphs_stays_one_block_of_the_decision_text() -> None:
    """A blank line inside a quote must not shift the blocks a reader counts.

    The screen cuts the stored text at blank lines to lay the card out, so a
    quote keeping its own blank line would push the question and the
    Approve/Reject lines one block off. The words stay; the gap goes. The
    committed citation is untouched by this — it is not built here.
    """
    from app.review.decision_text import possible_match_text, quote_block

    block = quote_block(
        "client-requirements-v1.md",
        "Requirements",
        "The bot must hand off to a person.\n\nWe tried three times.",
    )
    assert block["quote"] == (
        "The bot must hand off to a person.\nWe tried three times."
    )

    built = possible_match_text(
        row_number=2,
        row_label="Register row 2",
        cells={
            "What was asked": "A support bot.",
            "Written down": "Not known yet",
            "What testing found": "Not known yet",
            "Status": "Requested",
        },
        quote=block,
        if_approved=[{"cell": "Written down", "value": "Yes"}],
        proposed_in_writing="Yes",
    )
    blocks = built.question.split("\n\n")
    # Row block · quote block · question · Approve/Reject — and the quote's
    # own words hold no blank line, so the count cannot drift.
    assert len(blocks) == 4
    assert blocks[2] == "Is this the same ask as row 2?"
    assert built.parts["quotes"] == [block]
