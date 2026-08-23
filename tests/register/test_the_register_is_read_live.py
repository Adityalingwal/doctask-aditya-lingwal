from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

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
    extraction_answer,
    match_answer,
    match_marker,
    no_findings_answer,
    write_meeting_note,
)
from app.register.cells import COLUMN_HEADINGS
from tests.register.stored_register import stored_rows


SOURCE_FILE = "meeting-note.md"
REQUIREMENT = "an email to the operations team on intake form submit"
EMPTY_REGISTER_LINE = "Nothing has been added to this register yet."


@contextmanager
def _application(
    tmp_path: Path,
) -> Iterator[tuple[ApplicationProcess, str, str]]:
    with temporary_project_folder("live-register") as (source_folder, source_folder_path):
        quote = write_meeting_note(source_folder, SOURCE_FILE, REQUIREMENT)
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                extract_marker(SOURCE_FILE): extraction_answer(REQUIREMENT, quote),
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
                yield application, database_url, project_id
            finally:
                application.stop()


def _run_to_done(client, project_id: str) -> str:
    run_id = client.post("/runs", json={"project_id": project_id}).json()["run_id"]
    wait_for_run_status(client, run_id, "needs review")
    approve_every_decision_and_finish_review(client, run_id)
    wait_for_run_status(client, run_id, "done")
    return run_id


def test_the_register_read_returns_exactly_what_register_rows_holds(
    tmp_path: Path,
) -> None:
    with _application(tmp_path) as (application, database_url, project_id):
        with application.client() as client:
            _run_to_done(client, project_id)
            answered = client.get(f"/projects/{project_id}/register")
        stored = stored_rows(database_url, project_id)

    assert answered.status_code == 200
    register = answered.json()
    # One truth: no run sits between the read and the register.
    assert "run_id" not in register
    assert {row["row_number"] for row in register["rows"]} == set(stored)
    for row in register["rows"]:
        stored_row = stored[row["row_number"]]
        assert (
            tuple(row["cells"][name] for name in register["columns"])
            == stored_row.cells
        )
        assert row["fingerprint"] == stored_row.fingerprint
        # The per-row `citations` list left the JSON once the screen read
        # `evidence` instead; a populated row is where re-adding it would show.
        assert "citations" not in row
        # The evidence a reader is shown is the stored citations grouped by the
        # words themselves, so what it names must be exactly what is stored.
        assert sorted(
            (COLUMN_HEADINGS[cell], entry["quote"], entry["absence"])
            for entry in row["evidence"]
            for cell in _cells_of(entry, stored_row)
        ) == sorted(
            (COLUMN_HEADINGS[cell], source_words, absence_statement)
            for cell, _file, _place, source_words, absence_statement
            in stored_row.citations
        )


def test_a_project_with_no_committed_rows_answers_the_empty_state_not_an_error(
    tmp_path: Path,
) -> None:
    with _application(tmp_path) as (application, _database_url, project_id):
        with application.client() as client:
            as_json = client.get(f"/projects/{project_id}/register")
            as_markdown = client.get(
                f"/projects/{project_id}/register", params={"format": "markdown"}
            )

    assert as_json.status_code == 200
    register = as_json.json()
    assert register["rows"] == []
    assert register["exported_at"] is None
    assert register["rules"] is None
    # The old aggregate block left the JSON once the screen read `evidence`,
    # `findings` and `rules` instead (S16).
    assert "examine" not in register
    assert all("citations" not in row for row in register["rows"])

    assert as_markdown.status_code == 200
    assert EMPTY_REGISTER_LINE in as_markdown.text


def test_markdown_and_json_carry_the_same_register_content(tmp_path: Path) -> None:
    with _application(tmp_path) as (application, _database_url, project_id):
        with application.client() as client:
            _run_to_done(client, project_id)
            register = client.get(f"/projects/{project_id}/register").json()
            markdown = client.get(
                f"/projects/{project_id}/register", params={"format": "markdown"}
            ).text

    assert [row["cells"]["what_was_asked"] for row in register["rows"]] == [
        REQUIREMENT
    ]
    assert REQUIREMENT in markdown
    assert register["project"]["name"] in markdown
    assert f"Last updated {register['exported_at']}." in markdown
    for rule in register["rules"]["rules"]:
        assert rule["text"] in markdown


def test_the_register_timestamp_is_the_newest_done_runs_finished_at(
    tmp_path: Path,
) -> None:
    with _application(tmp_path) as (application, database_url, project_id):
        with application.client() as client:
            run_id = _run_to_done(client, project_id)
            register = client.get(f"/projects/{project_id}/register").json()

        engine = create_engine(database_url)
        with engine.connect() as connection:
            finished_at = connection.execute(
                text("SELECT finished_at FROM runs WHERE id = :run_id"),
                {"run_id": run_id},
            ).scalar_one()
        engine.dispose()

    assert register["exported_at"] == finished_at.isoformat()


def _cells_of(entry: dict[str, Any], stored_row: Any) -> list[str]:
    """The stored column keys behind one evidence entry's headings."""
    by_heading = {heading: cell for cell, heading in COLUMN_HEADINGS.items()}
    return [by_heading[heading] for heading in entry["cells"]]
