from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text

from conftest import (
    ApplicationProcess,
    recorded_markers,
    temporary_database,
    wait_until,
    write_script,
)
from register_documents import (
    examine_marker,
    extract_marker,
    extraction_answer,
    match_answer,
    match_marker,
    no_findings_answer,
    write_meeting_note,
)


DOCUMENTS = {
    "doc-1.md": "an email to the operations team on intake form submit",
    "doc-2.md": "the same notification sent over WhatsApp",
    "doc-3.md": "search over old intake records",
}
MODEL_DELAY_SECONDS = 2.0


def test_killed_run_resumes_without_repeating_extraction(tmp_path: Path) -> None:
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    script_path = tmp_path / "script.json"
    call_log_path = tmp_path / "model-calls.jsonl"

    answers = {
        match_marker(): match_answer(len(DOCUMENTS)),
        examine_marker(): no_findings_answer(),
    }
    for source_file, requirement in DOCUMENTS.items():
        quote = write_meeting_note(source_folder, source_file, requirement)
        answers[extract_marker(source_file)] = extraction_answer(requirement, quote)
    write_script(script_path, answers)

    with temporary_database() as database_url:
        application = ApplicationProcess(
            database_url=database_url,
            script_path=script_path,
            call_log_path=call_log_path,
            delay_seconds=MODEL_DELAY_SECONDS,
        )
        application.start()
        try:
            with application.client() as client:
                project_id = client.post(
                    "/projects",
                    json={
                        "name": "Killed run intake portal",
                        "source_folder_path": str(source_folder),
                    },
                ).json()["project_id"]
                run_id = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]

                # The third document's call is in flight and its answer has not
                # arrived, so the kill lands inside Extract with two documents
                # already checkpointed.
                wait_until(
                    lambda: len(recorded_markers(call_log_path)) >= len(DOCUMENTS),
                    "the model has been asked about every document",
                )
            markers_before_kill = recorded_markers(call_log_path)
            application.kill()

            application.start()
            with application.client() as client:
                wait_until(
                    lambda: client.get(f"/runs/{run_id}").json()["status"]
                    == "waiting for review",
                    "the resumed run reaches Review",
                )
        finally:
            application.stop()

        markers_after_resume = recorded_markers(call_log_path)
        engine = create_engine(database_url)
        with engine.connect() as connection:
            document_count = connection.execute(
                text("SELECT count(*) FROM documents WHERE run_id = :run_id"),
                {"run_id": run_id},
            ).scalar_one()
            proposed = connection.execute(
                text(
                    "SELECT what_was_asked FROM register_rows "
                    "WHERE proposed_by_run_id = :run_id"
                ),
                {"run_id": run_id},
            ).scalars().all()
        engine.dispose()

    assert markers_before_kill[: len(DOCUMENTS)] == [
        extract_marker("doc-1.md"),
        extract_marker("doc-2.md"),
        extract_marker("doc-3.md"),
    ]
    # The two documents whose extraction was checkpointed are never sent again.
    assert markers_after_resume.count(extract_marker("doc-1.md")) == 1
    assert markers_after_resume.count(extract_marker("doc-2.md")) == 1
    # Ingest is not repeated either: the run continued rather than restarting.
    assert document_count == len(DOCUMENTS)
    assert sorted(proposed) == sorted(DOCUMENTS.values())
