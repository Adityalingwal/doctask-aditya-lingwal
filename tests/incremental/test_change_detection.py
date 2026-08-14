from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    model_call_failure,
    recorded_markers,
    temporary_database,
    wait_for_run_status,
    write_script,
)
from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    extraction_answer,
    extraction_answer_without_requirements,
    match_answer,
    match_marker,
    no_findings_answer,
    unrelated_extraction_answer,
    write_meeting_note,
)
from tests.register.stored_register import stored_rows


READ_FILE = "doc-1.md"
UNREAD_FILE = "doc-2.md"
UNRELATED_FILE = "travel-note.md"
SILENT_FILE = "doc-3.md"
READ_REQUIREMENT = "an email to the operations team on intake form submit"
UNREAD_REQUIREMENT = "the same notification sent over WhatsApp"
UNRELATED_REQUIREMENT = "a window seat on the Tuesday flight"
# Written directly rather than through write_meeting_note, whose fabricated
# text embeds the file name in its own heading — exactly what a rename test
# must not have, since the whole point is identical content under a new name.
RENAME_REQUIREMENT = "a shared calendar view for the whole team"
RENAME_QUOTE = f"The client asked for {RENAME_REQUIREMENT}."
RENAME_CONTENT = (
    "# Intake portal — calendar note\n\n"
    "**Date:** 10 March 2026\n\n"
    "## Discussion\n\n"
    f"{RENAME_QUOTE}\n"
)
ORIGINAL_NAME = "calendar-note.md"
RENAMED_NAME = "calendar-note-v2.md"


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
    assert "read it and finished with what it said" in skipped_files[0]["reason"]


def test_an_edited_document_is_never_sent_to_the_model_again(tmp_path: Path) -> None:
    """L1: a document is read once, by name — editing it does not reopen it."""
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    quote = write_meeting_note(source_folder, READ_FILE, READ_REQUIREMENT)
    script_path = tmp_path / "script.json"
    call_log_path = tmp_path / "model-calls.jsonl"
    write_script(
        script_path,
        {
            extract_marker(READ_FILE): extraction_answer(READ_REQUIREMENT, quote),
            match_marker(): match_answer(1),
            examine_marker(): no_findings_answer(),
        },
    )

    with temporary_database() as database_url:
        application = ApplicationProcess(
            database_url=database_url,
            script_path=script_path,
            call_log_path=call_log_path,
        )
        application.start()
        try:
            with application.client() as client:
                project_id = client.post(
                    "/projects",
                    json={
                        "name": "Edited intake portal",
                        "source_folder_path": str(source_folder),
                    },
                ).json()["project_id"]

                first_run = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                wait_for_run_status(client, first_run, "waiting for review")
                approve_every_decision_and_finish_review(client, first_run)
                wait_for_run_status(client, first_run, "done")

                # Edited and re-saved under the same name: the words changed,
                # the file did not move.
                write_meeting_note(
                    source_folder, READ_FILE, "a completely different ask"
                )
                second_run = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                ended = wait_for_run_status(
                    client, second_run, "ended without changes"
                )
        finally:
            application.stop()

    assert recorded_markers(call_log_path).count(extract_marker(READ_FILE)) == 1
    skipped_files = [entry for entry in ended["skipped"] if entry["kind"] == "file"]
    assert [entry["file"] for entry in skipped_files] == [READ_FILE]
    assert "new name" in skipped_files[0]["reason"]


def test_a_renamed_document_is_never_read_as_a_new_one(tmp_path: Path) -> None:
    """L1: a document is read once, by content — renaming it does not reopen it."""
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    (source_folder / ORIGINAL_NAME).write_text(RENAME_CONTENT, encoding="utf-8")
    script_path = tmp_path / "script.json"
    call_log_path = tmp_path / "model-calls.jsonl"
    write_script(
        script_path,
        {
            extract_marker(ORIGINAL_NAME): extraction_answer(
                RENAME_REQUIREMENT, RENAME_QUOTE
            ),
            match_marker(): match_answer(1),
            examine_marker(): no_findings_answer(),
        },
    )

    with temporary_database() as database_url:
        application = ApplicationProcess(
            database_url=database_url,
            script_path=script_path,
            call_log_path=call_log_path,
        )
        application.start()
        try:
            with application.client() as client:
                project_id = client.post(
                    "/projects",
                    json={
                        "name": "Renamed intake portal",
                        "source_folder_path": str(source_folder),
                    },
                ).json()["project_id"]

                first_run = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                wait_for_run_status(client, first_run, "waiting for review")
                approve_every_decision_and_finish_review(client, first_run)
                wait_for_run_status(client, first_run, "done")
                after_first_run = stored_rows(database_url, project_id)

                (source_folder / ORIGINAL_NAME).unlink()
                (source_folder / RENAMED_NAME).write_text(
                    RENAME_CONTENT, encoding="utf-8"
                )
                second_run = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                ended = wait_for_run_status(
                    client, second_run, "ended without changes"
                )
                after_second_run = stored_rows(database_url, project_id)
        finally:
            application.stop()

    assert recorded_markers(call_log_path).count(extract_marker(ORIGINAL_NAME)) == 1
    skipped_files = [entry for entry in ended["skipped"] if entry["kind"] == "file"]
    assert [entry["file"] for entry in skipped_files] == [RENAMED_NAME]
    assert "different name" in skipped_files[0]["reason"]
    # No second set of rows: the register is exactly what the first run wrote.
    assert after_second_run == after_first_run


def test_a_deleted_document_never_removes_a_row(tmp_path: Path) -> None:
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    quote = write_meeting_note(source_folder, READ_FILE, READ_REQUIREMENT)
    script_path = tmp_path / "script.json"
    write_script(
        script_path,
        {
            extract_marker(READ_FILE): extraction_answer(READ_REQUIREMENT, quote),
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
                    "/projects",
                    json={
                        "name": "Deleted-file intake portal",
                        "source_folder_path": str(source_folder),
                    },
                ).json()["project_id"]

                first_run = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                wait_for_run_status(client, first_run, "waiting for review")
                approve_every_decision_and_finish_review(client, first_run)
                wait_for_run_status(client, first_run, "done")
                after_first_run = stored_rows(database_url, project_id)

                (source_folder / READ_FILE).unlink()
                second_run = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                wait_for_run_status(client, second_run, "ended without changes")
                after_second_run = stored_rows(database_url, project_id)
        finally:
            application.stop()

    # Deleting the file removes nothing from the register: every row it
    # supplied comes back exactly as the first run wrote it.
    assert after_second_run == after_first_run


def test_an_unchanged_unrelated_document_is_not_sent_to_the_model_twice(
    tmp_path: Path,
) -> None:
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    quote = write_meeting_note(source_folder, UNRELATED_FILE, UNRELATED_REQUIREMENT)

    markers = _markers_from_two_runs_over(
        tmp_path,
        source_folder,
        UNRELATED_FILE,
        unrelated_extraction_answer(UNRELATED_REQUIREMENT, quote),
        "Intake portal with a stray file",
    )

    # A run holding only an unrelated document never exports, so an export can
    # never be what settles this document. Reading it again would buy the same
    # answer a second time, and every run after that.
    assert markers.count(extract_marker(UNRELATED_FILE)) == 1


def test_an_unchanged_document_that_asked_for_nothing_is_not_sent_twice(
    tmp_path: Path,
) -> None:
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    write_meeting_note(source_folder, SILENT_FILE, "a schedule the team already keeps")

    markers = _markers_from_two_runs_over(
        tmp_path,
        source_folder,
        SILENT_FILE,
        extraction_answer_without_requirements(),
        "Intake portal with a note asking for nothing",
    )

    assert markers.count(extract_marker(SILENT_FILE)) == 1


def _markers_from_two_runs_over(
    tmp_path: Path,
    source_folder: Path,
    source_file: str,
    extraction: dict[str, Any],
    project_name: str,
) -> list[str]:
    """Run twice over one file nobody touched, and report every model call."""
    script_path = tmp_path / "script.json"
    call_log_path = tmp_path / "model-calls.jsonl"
    write_script(script_path, {extract_marker(source_file): extraction})

    with temporary_database() as database_url:
        application = ApplicationProcess(
            database_url=database_url,
            script_path=script_path,
            call_log_path=call_log_path,
        )
        application.start()
        try:
            with application.client() as client:
                project_id = client.post(
                    "/projects",
                    json={
                        "name": project_name,
                        "source_folder_path": str(source_folder),
                    },
                ).json()["project_id"]
                for _ in range(2):
                    run_id = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    wait_for_run_status(client, run_id, "ended without changes")
        finally:
            application.stop()

    return recorded_markers(call_log_path)
