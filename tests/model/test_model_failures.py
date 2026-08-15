from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from tests.runs.application import (
    ApplicationProcess,
    model_call_failure,
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


ANY_DOCUMENT_MARKER = "File name: "
FIRST_FILE = "doc-1.md"
SECOND_FILE = "doc-2.md"
FIRST_REQUIREMENT = "an email to the operations team on intake form submit"
SECOND_REQUIREMENT = "the same notification sent over WhatsApp"
REFUSED_KEY_STATUS = 401


def _run_over_two_documents(
    tmp_path: Path,
    answers: dict[str, Any],
    reached_status: str,
) -> tuple[dict[str, Any], list[str]]:
    with temporary_project_folder("model-failures") as (source_folder, source_folder_path):
        write_meeting_note(source_folder, FIRST_FILE, FIRST_REQUIREMENT)
        write_meeting_note(source_folder, SECOND_FILE, SECOND_REQUIREMENT)
        script_path = tmp_path / "script.json"
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
                        "/projects",
                        json={"source_folder_path": source_folder_path},
                    ).json()["project_id"]
                    run_id = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    run = wait_for_run_status(client, run_id, reached_status)
            finally:
                application.stop()

            engine = create_engine(database_url)
            with engine.connect() as connection:
                proposed = (
                    connection.execute(
                        text(
                            "SELECT what_was_asked FROM register_rows "
                            "WHERE proposed_by_run_id = :run_id"
                        ),
                        {"run_id": run_id},
                    )
                    .scalars()
                    .all()
                )
            engine.dispose()
    return run, list(proposed)


def test_a_refused_key_fails_the_run_instead_of_skipping_every_document(
    tmp_path: Path,
) -> None:
    failed, proposed = _run_over_two_documents(
        tmp_path,
        {
            ANY_DOCUMENT_MARKER: model_call_failure(
                "Incorrect API key provided", REFUSED_KEY_STATUS
            )
        },
        "failed",
    )

    # A wrong key is not a document problem: nothing is skipped and no empty
    # register is exported in place of the explanation.
    assert proposed == []
    assert failed["skipped"] == []
    assert failed["exported"] is False
    assert "check the OpenRouter key in your environment variables" in (
        failed["failure_reason"]
    )
    assert "HTTP 401" in failed["failure_reason"]
    assert "This run will not restart by itself." in failed["failure_reason"]


def test_a_timed_out_document_is_skipped_while_the_batch_continues(
    tmp_path: Path,
) -> None:
    quote = f"The client asked for {SECOND_REQUIREMENT}."
    at_review, proposed = _run_over_two_documents(
        tmp_path,
        {
            extract_marker(FIRST_FILE): model_call_failure(
                "Request timed out after 120 seconds"
            ),
            extract_marker(SECOND_FILE): extraction_answer(
                SECOND_REQUIREMENT, quote
            ),
            match_marker(): match_answer(1),
            examine_marker(): no_findings_answer(),
        },
        "needs review",
    )

    assert proposed == [SECOND_REQUIREMENT]
    skipped_documents = [
        entry for entry in at_review["skipped"] if entry["kind"] == "document"
    ]
    assert len(skipped_documents) == 1
    assert skipped_documents[0]["file"] == FIRST_FILE
    assert skipped_documents[0]["reason"] == "The model call failed for this file."
    assert at_review["failure_reason"] is None
