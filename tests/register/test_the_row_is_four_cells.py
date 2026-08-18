from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    match_answer,
    match_marker,
    no_findings_answer,
    write_document_stating,
)
from tests.register.stored_register import extraction_of_document
from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)


SOURCE_FILE = "meeting-notes-10-mar.md"
REQUIREMENT = "an email to the operations team on intake form submit"
REQUIREMENT_QUOTE = (
    "The client asked for an email to the operations team on intake form submit."
)
BLOCKER_SUMMARY = "the WhatsApp notification is waiting on the client's credentials"
BLOCKER_QUOTE = (
    "We cannot proceed with the WhatsApp notification until the client sends "
    "the API credentials."
)
FOUR_CELLS = ["what_was_asked", "in_writing", "what_testing_found", "status"]


def test_a_committed_row_has_exactly_the_four_cells_and_no_more(
    tmp_path: Path,
) -> None:
    finished = _one_run_stating_a_blocker(tmp_path)
    export = finished["export"]

    # `columns` is a JSON array and keeps its order; the cells of a row are a
    # JSON object, which PostgreSQL stores unordered, so they are compared as
    # the set of names the row carries.
    assert export["columns"] == FOUR_CELLS
    for row in export["rows"]:
        assert set(row["cells"]) == set(FOUR_CELLS)
    assert {citation["cell"] for row in export["rows"] for citation in row["citations"]} <= set(
        FOUR_CELLS
    )


def test_the_export_and_the_screen_both_read_written_down_not_in_writing(
    tmp_path: Path,
) -> None:
    """The stored column stays `in_writing`; only the heading a reader sees moves.

    Renaming the column too would cost a migration for a word, so the JSON
    record still keys the cell the way the database does.
    """
    finished = _one_run_stating_a_blocker(tmp_path)

    assert "in_writing" in finished["export"]["rows"][0]["cells"]
    assert "Written down?" in finished["markdown"]
    assert "In writing?" not in finished["markdown"]


def test_a_document_stating_a_blocker_produces_no_blocker_anywhere(
    tmp_path: Path,
) -> None:
    """The list left the answer model, so the model is never asked for one.

    A blocker sentence is not extracted and then discarded — asking for
    something nothing can use is how a schema starts lying about what the
    system does.
    """
    finished = _one_run_stating_a_blocker(tmp_path)

    assert finished["extraction"].get("blockers", []) == []
    everything_shown = json.dumps(
        [finished["export"], finished["run"]["not_used"], finished["run"]["examine"]]
    )
    assert BLOCKER_SUMMARY not in everything_shown
    assert "WhatsApp" not in everything_shown
    assert finished["run"]["examine"]["findings"] == []


def _one_run_stating_a_blocker(tmp_path: Path) -> dict[str, Any]:
    """One run over a document that states an ask and stops work on another."""
    with temporary_project_folder("four-cells") as (folder, folder_path):
        write_document_stating(
            folder,
            SOURCE_FILE,
            "10 March 2026",
            [REQUIREMENT_QUOTE, BLOCKER_QUOTE],
        )
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                extract_marker(SOURCE_FILE): {
                    "document_type": "meeting notes",
                    "document_date": {
                        "value": "10 March 2026",
                        "quote": "**Date:** 10 March 2026",
                    },
                    "requirements": [
                        {"summary": REQUIREMENT, "quote": REQUIREMENT_QUOTE}
                    ],
                    "testing_observations": [],
                    "delivery_evidence": [],
                    # Sent even though the answer model no longer holds this
                    # list: an old or over-eager reply must reach no cell.
                    "blockers": [
                        {"summary": BLOCKER_SUMMARY, "quote": BLOCKER_QUOTE}
                    ],
                    "embedded_instructions": [],
                },
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
                        "/projects", json={"source_folder_path": folder_path}
                    ).json()["project_id"]
                    run_id = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    at_review = wait_for_run_status(client, run_id, "needs review")
                    approve_every_decision_and_finish_review(client, run_id)
                    wait_for_run_status(client, run_id, "done")
                    export = client.get(f"/projects/{project_id}/register").json()
                    markdown = client.get(
                        f"/projects/{project_id}/register", params={"format": "markdown"}
                    ).text
            finally:
                application.stop()

            return {
                "run": at_review,
                "export": export,
                "markdown": markdown,
                "extraction": extraction_of_document(
                    database_url, run_id, SOURCE_FILE
                ),
            }
