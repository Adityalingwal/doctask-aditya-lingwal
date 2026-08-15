from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from app.ingest.read_docx import read_docx
from app.ingest.read_source_document import read_source_document
from app.ingest.unreadable_document import DocumentUnreadable
from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    recorded_markers,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)
from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    match_answer,
    match_marker,
    no_findings_answer,
    requirement_extraction_answer,
    write_corrupt_docx,
    write_corrupt_pdf,
    write_docx,
    write_encrypted_pdf,
    write_meeting_note,
    write_pdf,
    write_pdf_with_unparseable_content,
    write_pdf_without_a_text_layer,
    write_text_file,
)


OVERSIZED_PDF = "requirements-bundle.pdf"
ENCRYPTED_PDF = "signed-scope.pdf"
SCANNED_PDF = "testing-feedback-scan.pdf"
MARKDOWN_FILE = "meeting-note.md"
DOCX_FILE = "client-requirements.docx"
TEXT_FILE = "call-note.txt"
PDF_FILE = "testing-feedback.pdf"
SPREADSHEET_FILE = "budget.xlsx"
PAGE_LIMIT = 20

MARKDOWN_REQUIREMENT = "an email to the operations team on intake form submit"
DOCX_REQUIREMENT = "a records list page with a search box"
TEXT_REQUIREMENT = "a weekly digest of new intake records"
PDF_REQUIREMENT = "the same notification sent over WhatsApp"

DOCX_QUOTE = "The portal must offer a records list page with a search box."
TEXT_QUOTE = "The client asked for a weekly digest of new intake records."
PDF_QUOTE = "The client asked for the same notification sent over WhatsApp."


def test_a_pdf_longer_than_the_page_limit_is_never_read(tmp_path: Path) -> None:
    with temporary_project_folder("oversized-bundle") as (source_folder, source_folder_path):
        write_pdf(
            source_folder / OVERSIZED_PDF,
            [[f"Page {number} of the bundled requirements."] for number in range(1, 22)],
        )
        script_path = tmp_path / "script.json"
        write_script(script_path, {})
        call_log_path = tmp_path / "model-calls.jsonl"

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
                        json={"source_folder_path": source_folder_path},
                    ).json()["project_id"]
                    run_id = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    ended = wait_for_run_status(client, run_id, "no changes")
            finally:
                application.stop()

    skipped = _skipped_entry(ended, OVERSIZED_PDF)
    assert skipped["reason"] == "21 pages — this system reads up to 20 pages."
    # Never read means never extracted and never paid for.
    assert recorded_markers(call_log_path) == []


def test_an_encrypted_pdf_is_skipped_with_the_reason_and_the_batch_continues(
    tmp_path: Path,
) -> None:
    with temporary_project_folder("locked-scope") as (source_folder, source_folder_path):
        quote = write_meeting_note(source_folder, MARKDOWN_FILE, MARKDOWN_REQUIREMENT)
        write_encrypted_pdf(
            source_folder / ENCRYPTED_PDF,
            [["The signed scope of work for the intake portal."]],
        )
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                extract_marker(MARKDOWN_FILE): requirement_extraction_answer(
                    MARKDOWN_REQUIREMENT, quote
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
                        json={"source_folder_path": source_folder_path},
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

            read_files = _documents_in(database_url)

    skipped = _skipped_entry(finished, ENCRYPTED_PDF)
    assert skipped["reason"] == (
        "This PDF is password-protected. Add an unprotected copy instead."
    )
    # Not an empty document row that later stages would read as "said nothing".
    assert read_files == [MARKDOWN_FILE]
    assert [row["cells"]["what_was_asked"] for row in export["rows"]] == [
        MARKDOWN_REQUIREMENT
    ]


def test_a_scanned_pdf_is_skipped_with_its_own_reason_rather_than_read_as_empty(
    tmp_path: Path,
) -> None:
    with temporary_project_folder("scanned-feedback-sheet") as (source_folder, source_folder_path):
        write_pdf_without_a_text_layer(source_folder / SCANNED_PDF)
        script_path = tmp_path / "script.json"
        write_script(script_path, {})
        call_log_path = tmp_path / "model-calls.jsonl"

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
                        json={"source_folder_path": source_folder_path},
                    ).json()["project_id"]
                    run_id = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    ended = wait_for_run_status(client, run_id, "no changes")
            finally:
                application.stop()

            read_files = _documents_in(database_url)

    skipped = _skipped_entry(ended, SCANNED_PDF)
    assert skipped["reason"] == (
        "This PDF is scanned images, not text. Supply a text version."
    )
    assert read_files == []
    assert recorded_markers(call_log_path) == []


def test_only_the_extensions_the_config_accepts_reach_a_reader(
    tmp_path: Path,
) -> None:
    with temporary_project_folder("four-formats") as (source_folder, source_folder_path):
        markdown_quote = write_meeting_note(
            source_folder, MARKDOWN_FILE, MARKDOWN_REQUIREMENT
        )
        write_docx(
            source_folder / DOCX_FILE,
            [("Scope", ["The provider will build the intake portal."])],
            table_rows=[["Requirement", "Detail"], ["Records list", DOCX_QUOTE]],
        )
        write_text_file(
            source_folder / TEXT_FILE,
            ["Call with the operations lead.", "", TEXT_QUOTE],
        )
        write_pdf(source_folder / PDF_FILE, [["Testing feedback", PDF_QUOTE]])
        # A real PDF wearing an extension the config does not accept: the gate is
        # the configured list, not what the bytes turn out to be.
        write_pdf(source_folder / SPREADSHEET_FILE, [["Budget for the intake portal."]])

        script_path = tmp_path / "script.json"
        call_log_path = tmp_path / "model-calls.jsonl"
        write_script(
            script_path,
            {
                extract_marker(MARKDOWN_FILE): requirement_extraction_answer(
                    MARKDOWN_REQUIREMENT, markdown_quote
                ),
                extract_marker(DOCX_FILE): requirement_extraction_answer(
                    DOCX_REQUIREMENT,
                    DOCX_QUOTE,
                    document_type="client requirements document",
                ),
                extract_marker(TEXT_FILE): requirement_extraction_answer(
                    TEXT_REQUIREMENT, TEXT_QUOTE
                ),
                extract_marker(PDF_FILE): requirement_extraction_answer(
                    PDF_REQUIREMENT, PDF_QUOTE
                ),
                match_marker(): match_answer(4),
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
                        json={"source_folder_path": source_folder_path},
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

            read_files = _documents_in(database_url)

    assert read_files == sorted([MARKDOWN_FILE, DOCX_FILE, TEXT_FILE, PDF_FILE])
    assert extract_marker(SPREADSHEET_FILE) not in recorded_markers(call_log_path)
    skipped = _skipped_entry(finished, SPREADSHEET_FILE)
    assert skipped["reason"] == (
        "Not a format this system reads. It reads .md, .pdf, .docx and .txt."
    )
    assert sorted(row["cells"]["what_was_asked"] for row in export["rows"]) == sorted(
        [MARKDOWN_REQUIREMENT, DOCX_REQUIREMENT, TEXT_REQUIREMENT, PDF_REQUIREMENT]
    )


def test_a_docx_reader_never_adds_words_the_document_does_not_contain(
    tmp_path: Path,
) -> None:
    """Whatever the reader hands over becomes both the model's evidence and the
    words a citation quotes back, so it may hold only the document's own text."""
    path = tmp_path / DOCX_FILE
    heading = "Out of scope"
    paragraph = "The provider will build the intake portal."
    table_rows = [["Requirement", "Detail"], ["Records list", DOCX_QUOTE]]
    write_docx(path, [(heading, [paragraph])], table_rows=table_rows)

    document_text = read_docx(path)

    written = {heading, paragraph, *(cell for row in table_rows for cell in row)}
    assert [line for line in document_text.splitlines() if line.strip()] != []
    for line in document_text.splitlines():
        assert line in written or not line.strip(), (
            f"the reader produced {line!r}, which is not in the document"
        )


def test_a_corrupt_docx_is_skipped_with_a_reason_naming_the_cause(
    tmp_path: Path,
) -> None:
    path = tmp_path / DOCX_FILE
    write_corrupt_docx(path)

    with pytest.raises(DocumentUnreadable) as unreadable:
        read_source_document(path, PAGE_LIMIT)

    assert str(unreadable.value) == (
        "This Word file could not be opened — it is damaged, or not a .docx."
    )


def test_a_corrupt_pdf_is_skipped_with_its_reason_and_the_batch_continues(
    tmp_path: Path,
) -> None:
    with temporary_project_folder("truncated-pdf") as (source_folder, source_folder_path):
        quote = write_meeting_note(source_folder, MARKDOWN_FILE, MARKDOWN_REQUIREMENT)
        write_corrupt_pdf(source_folder / PDF_FILE)
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                extract_marker(MARKDOWN_FILE): requirement_extraction_answer(
                    MARKDOWN_REQUIREMENT, quote
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
                        json={"source_folder_path": source_folder_path},
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

            read_files = _documents_in(database_url)

    skipped = _skipped_entry(finished, PDF_FILE)
    assert skipped["reason"] == "This PDF could not be opened — it is damaged, or not a PDF."
    # One damaged file loses its own document, never the rest of the batch.
    assert read_files == [MARKDOWN_FILE]
    assert [row["cells"]["what_was_asked"] for row in export["rows"]] == [
        MARKDOWN_REQUIREMENT
    ]


def test_a_pdf_that_cannot_be_parsed_is_skipped_and_the_batch_continues(
    tmp_path: Path,
) -> None:
    """A PDF sound enough for pypdf to count its pages, but whose content
    stream pdfplumber cannot parse — the gap `read_pdf` left unguarded."""
    with temporary_project_folder("unparseable-pdf") as (source_folder, source_folder_path):
        quote = write_meeting_note(source_folder, MARKDOWN_FILE, MARKDOWN_REQUIREMENT)
        write_pdf_with_unparseable_content(source_folder / PDF_FILE)
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                extract_marker(MARKDOWN_FILE): requirement_extraction_answer(
                    MARKDOWN_REQUIREMENT, quote
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
                        json={"source_folder_path": source_folder_path},
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

            read_files = _documents_in(database_url)

    skipped = _skipped_entry(finished, PDF_FILE)
    assert skipped["reason"] == (
        "This PDF's content could not be read — it is damaged. Supply a working copy."
    )
    # One unparseable file loses its own document, never the rest of the batch.
    assert read_files == [MARKDOWN_FILE]
    assert [row["cells"]["what_was_asked"] for row in export["rows"]] == [
        MARKDOWN_REQUIREMENT
    ]


def _skipped_entry(run: dict, source_file: str) -> dict:
    entries = [entry for entry in run["skipped"] if entry.get("file") == source_file]
    assert len(entries) == 1, f"expected one skip for {source_file}, got {entries}"
    return entries[0]


def _documents_in(database_url: str) -> list[str]:
    engine = create_engine(database_url)
    with engine.connect() as connection:
        read_files = (
            connection.execute(
                text("SELECT source_path FROM documents ORDER BY source_path")
            )
            .scalars()
            .all()
        )
    engine.dispose()
    return list(read_files)
