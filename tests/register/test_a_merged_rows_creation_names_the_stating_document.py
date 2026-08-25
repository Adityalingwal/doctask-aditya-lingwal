from __future__ import annotations

from pathlib import Path

from app.extract.answer import CLIENT_REQUIREMENTS_DOCUMENT, MEETING_NOTES
from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    match_answer_within_batch,
    match_marker,
    no_findings_answer,
    several_requirements_answer,
    write_document_stating,
)
from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)


MEETING_NOTE = "a-meeting-note.md"
REQUIREMENTS_FILE = "b-client-requirements.md"
RAISED_IN_THE_MEETING = "an email to the operations team when a form is submitted"
WRITTEN_DOWN = "email notification to the operations team on submission"
ROW_CREATED = "row created"


def test_a_row_two_documents_state_is_created_under_the_one_that_stated_it_first(
    tmp_path: Path,
) -> None:
    """The creation entry names the document whose words the row carries.

    Match is confident here, so one ask stated in a meeting note and again in
    the requirements document becomes one row holding two `what was asked`
    citations. The row's wording is the meeting note's, because that document
    comes first in the workflow — and the history has to name that same
    document rather than whichever citation the database happened to return
    last.
    """
    with temporary_project_folder("merged-creation") as (folder, source_folder_path):
        write_document_stating(
            folder, MEETING_NOTE, "10 March 2026", [RAISED_IN_THE_MEETING]
        )
        write_document_stating(
            folder, REQUIREMENTS_FILE, "8 March 2026", [WRITTEN_DOWN]
        )
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                extract_marker(MEETING_NOTE): several_requirements_answer(
                    [(RAISED_IN_THE_MEETING, RAISED_IN_THE_MEETING)],
                    MEETING_NOTES,
                ),
                extract_marker(REQUIREMENTS_FILE): several_requirements_answer(
                    [(WRITTEN_DOWN, WRITTEN_DOWN)],
                    CLIENT_REQUIREMENTS_DOCUMENT,
                ),
                # The meeting note is read first, so the written statement is
                # confidently the same ask as requirement 0 and no question is
                # raised: both land on one row.
                match_marker(): match_answer_within_batch(
                    [("new row", None, None), ("existing row", None, 0)]
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
                        "/projects", json={"source_folder_path": source_folder_path}
                    ).json()["project_id"]
                    run_id = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    wait_for_run_status(client, run_id, "needs review")
                    approve_every_decision_and_finish_review(client, run_id)
                    wait_for_run_status(client, run_id, "done")
                    history = client.get(f"/projects/{project_id}/history").json()
            finally:
                application.stop()

    created = [entry for entry in history["entries"] if entry["kind"] == ROW_CREATED]
    assert len(created) == 1
    assert created[0]["what_was_asked"] == RAISED_IN_THE_MEETING
    assert created[0]["source_file"] == MEETING_NOTE
