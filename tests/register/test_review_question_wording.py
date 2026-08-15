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
    match_answer,
    match_marker,
    no_findings_answer,
    write_meeting_note,
)


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
            finally:
                application.stop()

        export_decision = next(
            decision
            for decision in waiting["decisions"]
            if decision["kind"] == "export"
        )
        assert export_decision["question"] == NEW_WORDING


def test_a_rules_only_run_reaches_review_with_the_same_question(
    tmp_path: Path,
) -> None:
    """The zero-proposed-rows case: a run that only re-examines the register
    under changed rules — no new document, no match decision — must still
    raise this exact question, because it still commits merges and findings
    with no human approval otherwise."""
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
            finally:
                application.stop()

        # Only the export decision — no match or finding raised this run —
        # is the check that this really is the zero-proposed-rows case.
        assert [decision["kind"] for decision in waiting["decisions"]] == ["export"]
        assert waiting["decisions"][0]["question"] == NEW_WORDING
