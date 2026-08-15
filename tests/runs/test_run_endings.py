from __future__ import annotations

from pathlib import Path

from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    temporary_database,
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


SOURCE_FILE = "meeting-note.md"
REQUIREMENT = "an email to the operations team on intake form submit"


def test_a_run_with_nothing_new_ends_without_changes(tmp_path: Path) -> None:
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
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
                    "/projects",
                    json={
                        "name": "Unchanged intake portal",
                        "source_folder_path": str(source_folder),
                    },
                ).json()["project_id"]

                exporting_run = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                wait_for_run_status(client, exporting_run, "needs review")
                approve_every_decision_and_finish_review(client, exporting_run)
                wait_for_run_status(client, exporting_run, "done")

                unchanged_run = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                ended = wait_for_run_status(
                    client, unchanged_run, "no changes"
                )
                # The lock is a run in an active status, so a project whose run
                # reports no changes must take another run straight away.
                after_ending = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()
        finally:
            application.stop()

    assert "no new document" in ended["ended_early_reason"]
    assert ended["exported"] is False
    assert ended["failure_reason"] is None
    assert after_ending["status"] == "running"
