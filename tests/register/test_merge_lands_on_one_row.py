from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text

from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)
from tests.documents.register_documents import (
    several_requirements_answer,
    examine_marker,
    extract_marker,
    match_answer_within_batch,
    match_marker,
    no_findings_answer,
    write_document_stating,
)

from app.extract.answer import CLIENT_REQUIREMENTS_DOCUMENT, MEETING_NOTES
from app.register.cells import IN_WRITING_YES

MEETING_NOTE = "a-meeting-note.md"
REQUIREMENTS_FILE = "b-client-requirements.md"
RAISED_IN_THE_MEETING = "an email to the operations team when a form is submitted"
WRITTEN_DOWN = "email notification to the operations team on submission"
MEETING_DATE = "10 March 2026"
REQUIREMENTS_DATE = "8 March 2026"


def _batch_of_two(source_folder: Path) -> dict[str, dict]:
    """One ask stated twice, with the written statement dated the earlier of the two."""
    write_document_stating(
        source_folder, MEETING_NOTE, MEETING_DATE, [RAISED_IN_THE_MEETING]
    )
    write_document_stating(
        source_folder, REQUIREMENTS_FILE, REQUIREMENTS_DATE, [WRITTEN_DOWN]
    )
    return {
        extract_marker(MEETING_NOTE): several_requirements_answer(
            [(RAISED_IN_THE_MEETING, RAISED_IN_THE_MEETING)],
            MEETING_NOTES,
        ),
        extract_marker(REQUIREMENTS_FILE): several_requirements_answer(
            [(WRITTEN_DOWN, WRITTEN_DOWN)],
            CLIENT_REQUIREMENTS_DOCUMENT,
        ),
        examine_marker(): no_findings_answer(),
    }


def test_an_approved_merge_leaves_no_cell_denying_the_row_s_own_evidence(
    tmp_path: Path,
) -> None:
    """The surviving row must not say an ask is absent from a file it now cites.

    Match is unsure here, so both mentions become rows and a person is asked.
    Approving attaches the written statement's evidence to the meeting note's
    row — and that row was written saying the ask is not in the requirements
    document, and carrying the later of the two dates.
    """
    with temporary_project_folder("merge-cells") as (source_folder, source_folder_path):
        script_path = tmp_path / "script.json"
        answers = _batch_of_two(source_folder)
        # Read in file-name order, so the meeting note is requirement 0 and
        # creates the row the written statement is then merged into.
        answers[match_marker()] = match_answer_within_batch(
            [("new row", None, None), ("possible match", None, 0)]
        )
        write_script(script_path, answers)

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
                        "/projects", json={"source_folder_path": source_folder_path}
                    ).json()["project_id"]
                    run_id = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    at_review = wait_for_run_status(client, run_id, "needs review")
                    approve_every_decision_and_finish_review(client, run_id)
                    wait_for_run_status(client, run_id, "done")
                    export = client.get(f"/projects/{project_id}/register").json()
            finally:
                application.stop()

    merge_questions = [
        decision
        for decision in at_review["decisions"]
        if decision["kind"] == "possible match"
    ]
    assert len(merge_questions) == 1

    assert len(export["rows"]) == 1
    surviving = export["rows"][0]
    assert surviving["cells"]["what_was_asked"] == RAISED_IN_THE_MEETING
    assert surviving["cells"]["in_writing"] == IN_WRITING_YES
    # The cell that changed keeps exactly the citation supporting what it now
    # says, never the one that supported the sentence it no longer holds.
    written_down_evidence = [
        entry
        for entry in surviving["evidence"]
        if "Written down" in entry["cells"]
    ]
    assert [
        entry["source_line"].split(",")[0] for entry in written_down_evidence
    ] == [REQUIREMENTS_FILE]


def test_a_merge_into_a_row_that_is_itself_merged_leaves_no_two_hop_marker(
    tmp_path: Path,
) -> None:
    """Every merge marker points at the row that actually holds the evidence.

    Approved merges are settled in decision id order, which is a random uuid,
    so requirement 2's merge into requirement 1's row can be written before
    requirement 1's own merge. A marker left two hops from the surviving row is
    followed only once by the code that reports findings, which would report a
    finding against a row Commit never commits.
    """
    third_file = "c-follow-up.md"
    stated_again = "notify the operations team by email when a form arrives"

    with temporary_project_folder("merge-chain") as (source_folder, source_folder_path):
        script_path = tmp_path / "script.json"
        answers = _batch_of_two(source_folder)
        write_document_stating(source_folder, third_file, "12 March 2026", [stated_again])
        answers[extract_marker(third_file)] = several_requirements_answer(
            [(stated_again, stated_again)], MEETING_NOTES
        )
        answers[match_marker()] = match_answer_within_batch(
            [
                ("new row", None, None),
                ("possible match", None, 0),
                ("possible match", None, 1),
            ]
        )
        write_script(script_path, answers)

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
                        "/projects", json={"source_folder_path": source_folder_path}
                    ).json()["project_id"]
                    run_id = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    wait_for_run_status(client, run_id, "needs review")
                    approve_every_decision_and_finish_review(client, run_id)
                    wait_for_run_status(client, run_id, "done")
                    export = client.get(f"/projects/{project_id}/register").json()
            finally:
                application.stop()

            engine = create_engine(database_url)
            with engine.connect() as connection:
                two_hop = connection.execute(
                    text(
                        "SELECT count(*) FROM register_rows AS marked "
                        "JOIN register_rows AS pointed_at ON pointed_at.id = "
                        "marked.merged_into_register_row_id "
                        "WHERE pointed_at.merged_into_register_row_id IS NOT NULL"
                    )
                ).scalar_one()
            engine.dispose()

    assert two_hop == 0
    assert len(export["rows"]) == 1
    cited_files = {
        entry["source_line"].split(",")[0]
        for entry in export["rows"][0]["evidence"]
    }
    assert cited_files == {MEETING_NOTE, REQUIREMENTS_FILE, third_file}
