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
    match_answer,
    match_marker,
    no_findings_answer,
    requirement_extraction_answer,
    write_docx,
    write_pdf,
    write_text_file,
)


PDF_FILE = "testing-feedback.pdf"
DOCX_FILE = "client-requirements.docx"
TEXT_FILE = "call-note.txt"

PDF_QUOTE = "The list page opens but has no search box at all."
DOCX_QUOTE = "The portal must let staff export a record as a PDF."
TEXT_QUOTE = "The client asked for a weekly digest of new intake records."

PDF_REQUIREMENT = "a search box on the records list page"
DOCX_REQUIREMENT = "exporting one record as a PDF"
TEXT_REQUIREMENT = "a weekly digest of new intake records"

LAST_HEADING = "Open questions"
# Word keeps no page numbers and its headings live in styling rather than in
# the text, so a Word citation names the line the reader put the quote on:
# "Scope", its paragraph, "Open questions", then the quote.
DOCX_PLACE = "line 4"


def test_a_citation_names_only_a_place_the_reader_actually_produced(
    tmp_path: Path,
) -> None:
    """Every quote sits late in its document, so page 1 or the first heading is
    not an answer any of these citations may give."""
    with temporary_project_folder("citation-places") as (source_folder, source_folder_path):
        write_pdf(
            source_folder / PDF_FILE,
            [
                ["Testing feedback", "The intake form submits correctly."],
                ["The email notification reaches the operations team."],
                ["Records", PDF_QUOTE],
            ],
        )
        write_docx(
            source_folder / DOCX_FILE,
            [
                ("Scope", ["The provider will build the intake portal."]),
                (LAST_HEADING, [DOCX_QUOTE]),
            ],
        )
        write_text_file(
            source_folder / TEXT_FILE,
            [
                "Call with the operations lead.",
                "",
                "Nothing was settled in the first half of the call.",
                "",
                TEXT_QUOTE,
            ],
        )

        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                extract_marker(PDF_FILE): requirement_extraction_answer(
                    PDF_REQUIREMENT, PDF_QUOTE, document_type="testing feedback"
                ),
                extract_marker(DOCX_FILE): requirement_extraction_answer(
                    DOCX_REQUIREMENT,
                    DOCX_QUOTE,
                    document_type="client requirements document",
                ),
                extract_marker(TEXT_FILE): requirement_extraction_answer(
                    TEXT_REQUIREMENT, TEXT_QUOTE
                ),
                match_marker(): match_answer(3),
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
                    wait_for_run_status(client, run_id, "done")
                    export = client.get(f"/runs/{run_id}/export").json()
            finally:
                application.stop()

    place_by_file = {
        citation["source_file"]: citation["place"]
        for row in export["rows"]
        for citation in row["citations"]
        if citation["cell"] == "what_was_asked"
    }
    assert place_by_file[PDF_FILE] == "page 3"
    assert place_by_file[DOCX_FILE] == DOCX_PLACE
    assert place_by_file[TEXT_FILE] == "line 5"
