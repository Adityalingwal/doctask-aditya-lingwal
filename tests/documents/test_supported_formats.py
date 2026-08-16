from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, text

from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    match_answer,
    match_marker,
    no_findings_answer,
    requirement_extraction_answer,
    write_meeting_note,
    write_pdf,
)
from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    recorded_markers,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)


MARKDOWN_FILE = "meeting-note.md"
PDF_FILE = "testing-feedback.pdf"
WORD_FILE = "client-requirements.docx"
PLAIN_TEXT_FILE = "call-note.txt"

MARKDOWN_REQUIREMENT = "an email to the operations team on intake form submit"
PDF_REQUIREMENT = "the same notification sent over WhatsApp"
PDF_QUOTE = "The client asked for the same notification sent over WhatsApp."
# write_meeting_note puts its quote under this heading, and nothing else in the
# file is a heading below it.
MARKDOWN_PLACE = "Discussion"
UNSUPPORTED_FORMAT = "Not a format this system reads. It reads .md and .pdf."


@pytest.fixture(scope="module")
def one_run_over_four_extensions(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[dict[str, Any]]:
    """One run over a folder holding all four extensions the system once read."""
    yield from _drive_one_run(tmp_path_factory.mktemp("supported-formats"))


def test_a_docx_file_is_skipped_with_a_reason_naming_the_supported_formats(
    one_run_over_four_extensions: dict[str, Any],
) -> None:
    finished = one_run_over_four_extensions

    assert _skipped_reason(finished["run"], WORD_FILE) == UNSUPPORTED_FORMAT
    assert WORD_FILE not in finished["documents_read"]
    assert extract_marker(WORD_FILE) not in finished["markers"]


def test_a_txt_file_is_skipped_with_a_reason_naming_the_supported_formats(
    one_run_over_four_extensions: dict[str, Any],
) -> None:
    finished = one_run_over_four_extensions

    assert _skipped_reason(finished["run"], PLAIN_TEXT_FILE) == UNSUPPORTED_FORMAT
    assert PLAIN_TEXT_FILE not in finished["documents_read"]
    assert extract_marker(PLAIN_TEXT_FILE) not in finished["markers"]


def test_a_markdown_file_still_reads_and_still_cites_its_nearest_heading(
    one_run_over_four_extensions: dict[str, Any],
) -> None:
    """`.md` and `.txt` shared one reader, so dropping `.txt` can break `.md`."""
    finished = one_run_over_four_extensions

    assert finished["documents_read"] == sorted([MARKDOWN_FILE, PDF_FILE])
    places = _citation_places(finished["export"])
    assert places[MARKDOWN_FILE] == MARKDOWN_PLACE
    assert places[PDF_FILE] == "page 1"


def _drive_one_run(tmp_path: Path) -> Iterator[dict[str, Any]]:
    with temporary_project_folder("supported-formats") as (folder, folder_path):
        markdown_quote = write_meeting_note(
            folder, MARKDOWN_FILE, MARKDOWN_REQUIREMENT
        )
        write_pdf(folder / PDF_FILE, [["Testing feedback", PDF_QUOTE]])
        # Real content in both dropped formats: the gate is the accepted list,
        # never whether the bytes happen to be readable.
        (folder / WORD_FILE).write_bytes(b"PK\x03\x04 a real Word package starts so")
        (folder / PLAIN_TEXT_FILE).write_text(
            "Call with the operations lead.\n", encoding="utf-8"
        )

        script_path = tmp_path / "script.json"
        call_log_path = tmp_path / "model-calls.jsonl"
        write_script(
            script_path,
            {
                extract_marker(MARKDOWN_FILE): requirement_extraction_answer(
                    MARKDOWN_REQUIREMENT, markdown_quote
                ),
                extract_marker(PDF_FILE): requirement_extraction_answer(
                    PDF_REQUIREMENT, PDF_QUOTE
                ),
                match_marker(): match_answer(2),
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
                        "/projects", json={"source_folder_path": folder_path}
                    ).json()["project_id"]
                    run_id = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    wait_for_run_status(client, run_id, "needs review")
                    approve_every_decision_and_finish_review(client, run_id)
                    finished = wait_for_run_status(client, run_id, "done")
                    export = client.get(f"/runs/{run_id}/export").json()
            finally:
                application.stop()

            yield {
                "run": finished,
                "export": export,
                "documents_read": _documents_in(database_url),
                "markers": recorded_markers(call_log_path),
            }


def _skipped_reason(run: dict[str, Any], source_file: str) -> str:
    entries = [entry for entry in run["skipped"] if entry.get("file") == source_file]
    assert len(entries) == 1, f"expected one skip for {source_file}, got {entries}"
    return entries[0]["reason"]


def _citation_places(export: dict[str, Any]) -> dict[str, str]:
    places: dict[str, str] = {}
    for row in export["rows"]:
        for citation in row["citations"]:
            places[citation["source_file"]] = citation["place"]
    return places


def _documents_in(database_url: str) -> list[str]:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return list(
                connection.execute(
                    text("SELECT source_path FROM documents ORDER BY source_path")
                )
                .scalars()
                .all()
            )
    finally:
        engine.dispose()
