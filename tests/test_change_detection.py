from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text

from conftest import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    model_call_failure,
    temporary_database,
    wait_for_run_status,
    write_script,
)
from register_documents import (
    extract_marker,
    extraction_answer,
    match_answer,
    match_marker,
    write_meeting_note,
)


READ_FILE = "doc-1.md"
UNREAD_FILE = "doc-2.md"
READ_REQUIREMENT = "an email to the operations team on intake form submit"
UNREAD_REQUIREMENT = "the same notification sent over WhatsApp"


def test_a_document_skipped_by_extract_is_read_again_by_the_next_run(
    tmp_path: Path,
) -> None:
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    read_quote = write_meeting_note(source_folder, READ_FILE, READ_REQUIREMENT)
    write_meeting_note(source_folder, UNREAD_FILE, UNREAD_REQUIREMENT)
    script_path = tmp_path / "script.json"
    write_script(
        script_path,
        {
            extract_marker(UNREAD_FILE): model_call_failure(
                "Request timed out after 120 seconds"
            ),
            extract_marker(READ_FILE): extraction_answer(
                READ_REQUIREMENT, read_quote
            ),
            match_marker(): match_answer(1),
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
                        "name": "Half-read intake portal",
                        "source_folder_path": str(source_folder),
                    },
                ).json()["project_id"]

                exporting_run = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                wait_for_run_status(client, exporting_run, "waiting for review")
                approve_every_decision_and_finish_review(client, exporting_run)
                exported = wait_for_run_status(client, exporting_run, "done")

                second_run = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                ended = wait_for_run_status(
                    client, second_run, "ended without changes"
                )
        finally:
            application.stop()

        engine = create_engine(database_url)
        with engine.connect() as connection:
            second_batch = (
                connection.execute(
                    text(
                        "SELECT source_path FROM documents WHERE run_id = :run_id"
                    ),
                    {"run_id": second_run},
                )
                .scalars()
                .all()
            )
        engine.dispose()

    assert exported["exported"] is True
    # The document Extract could not read is not "already read", however well
    # the run that held it finished; the one that was read is not read twice.
    assert list(second_batch) == [UNREAD_FILE]
    skipped_files = [entry for entry in ended["skipped"] if entry["kind"] == "file"]
    assert [entry["file"] for entry in skipped_files] == [READ_FILE]
    assert "read it and exported the register" in skipped_files[0]["reason"]
