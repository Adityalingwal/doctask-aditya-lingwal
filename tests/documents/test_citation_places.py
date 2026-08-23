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
    write_document_stating,
    write_pdf,
)


PDF_FILE = "meeting-notes.pdf"
MARKDOWN_FILE = "client-requirements.md"

PDF_QUOTE = "The client asked for a search box on the records list page."
MARKDOWN_QUOTE = "The portal must let staff export a record as a PDF."

PDF_REQUIREMENT = "a search box on the records list page"
MARKDOWN_REQUIREMENT = "exporting one record as a PDF"

# write_document_stating puts every statement under this heading, and the
# quote sits well below the file's first heading.
MARKDOWN_PLACE = "Discussion"


def test_a_citation_names_only_a_place_the_reader_actually_produced(
    tmp_path: Path,
) -> None:
    """Every quote sits late in its document, so page 1 or the first heading is
    not an answer any of these citations may give."""
    with temporary_project_folder("citation-places") as (source_folder, source_folder_path):
        write_pdf(
            source_folder / PDF_FILE,
            [
                ["Meeting notes", "The operations lead walked us through intake."],
                ["The second half of the call covered the records list page."],
                ["Records", PDF_QUOTE],
            ],
        )
        write_document_stating(
            source_folder,
            MARKDOWN_FILE,
            "10 March 2026",
            ["Nothing was settled in the first half of the call.", MARKDOWN_QUOTE],
        )

        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                extract_marker(PDF_FILE): requirement_extraction_answer(
                    PDF_REQUIREMENT, PDF_QUOTE
                ),
                extract_marker(MARKDOWN_FILE): requirement_extraction_answer(
                    MARKDOWN_REQUIREMENT,
                    MARKDOWN_QUOTE,
                    document_type="client requirements document",
                ),
                match_marker(): match_answer(2),
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
                    export = client.get(f"/projects/{project_id}/register").json()
            finally:
                application.stop()

    # The place is read back through the one line every surface prints it in
    # (`app/ingest/source_line.py`): a PDF names a page, Markdown a heading.
    source_lines = {
        entry["source_line"].split(",")[0]: entry["source_line"]
        for row in export["rows"]
        for entry in row["evidence"]
        if "What was asked" in entry["cells"]
    }
    assert source_lines[PDF_FILE] == f"{PDF_FILE}, page 3"
    assert source_lines[MARKDOWN_FILE] == (
        f'{MARKDOWN_FILE}, under "{MARKDOWN_PLACE}"'
    )
