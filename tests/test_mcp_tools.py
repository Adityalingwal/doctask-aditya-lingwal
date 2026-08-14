from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text

from tests.runs.application import (
    ApplicationProcess,
    temporary_database,
    wait_until,
    write_script,
)
from tests.interfaces.mcp_client import call_tool, tool_names
from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    extraction_answer,
    match_answer,
    match_marker,
    no_findings_answer,
    write_meeting_note,
)


SOURCE_FILE = "meeting-note.md"
REQUIREMENT = "an email to the operations team on intake form submit"
LOCKED_TOOLS = [
    "create_project",
    "finish_review",
    "get_export",
    "get_run_status",
    "start_run",
    "submit_decision",
]


@contextmanager
def _application(tmp_path: Path) -> Iterator[tuple[ApplicationProcess, str, Path]]:
    """One application process on a database of its own, and nothing run yet."""
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    quote = write_meeting_note(source_folder, SOURCE_FILE, REQUIREMENT)
    script_path = tmp_path / "script.json"
    write_script(
        script_path,
        {
            match_marker(): match_answer(1),
            examine_marker(): no_findings_answer(),
            extract_marker(SOURCE_FILE): extraction_answer(REQUIREMENT, quote),
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
            yield application, database_url, source_folder
        finally:
            application.stop()


def _run_at_review(
    application: ApplicationProcess,
    project_name: str,
    source_folder: Path,
) -> str:
    """One run driven through the API until it is parked at Review."""
    with application.client() as client:
        project_id = client.post(
            "/projects",
            json={"name": project_name, "source_folder_path": str(source_folder)},
        ).json()["project_id"]
        run_id = client.post("/runs", json={"project_id": project_id}).json()["run_id"]
        wait_until(
            lambda: client.get(f"/runs/{run_id}").json()["status"]
            == "waiting for review",
            "the run reaches Review",
        )
    return run_id


def test_a_tool_and_its_endpoint_answer_one_operation_identically(
    tmp_path: Path,
) -> None:
    with _application(tmp_path) as (application, _database_url, source_folder):
        run_id = _run_at_review(
            application, "Both doors intake portal", source_folder
        )
        missing_folder = str(tmp_path / "not-a-folder")

        with application.client() as client:
            over_http = client.get(f"/runs/{run_id}").json()
            refused_over_http = client.post(
                "/projects",
                json={"name": "Missing folder", "source_folder_path": missing_folder},
            )

        through_mcp = call_tool(
            application.base_url, "get_run_status", {"run_id": run_id}
        )
        refused_through_mcp = call_tool(
            application.base_url,
            "create_project",
            {"name": "Missing folder", "source_folder_path": missing_folder},
        )

    assert through_mcp.refused is False
    assert through_mcp.payload == over_http
    assert refused_over_http.status_code == 400
    assert refused_through_mcp.refused is True
    assert refused_over_http.json()["detail"] in refused_through_mcp.text


def test_neither_door_creates_a_project_with_an_empty_name_or_folder(
    tmp_path: Path,
) -> None:
    """An empty path is the one the folder check cannot catch.

    `Path("")` resolves to the project root, which is a real directory, so the
    call succeeds and the project watches the whole repository — every
    supported file in it read as a client document on the next run.
    """
    with _application(tmp_path) as (application, database_url, _source_folder):
        with application.client() as client:
            refused_over_http = client.post(
                "/projects", json={"name": "", "source_folder_path": ""}
            )

        refused_through_mcp = call_tool(
            application.base_url,
            "create_project",
            {"name": "", "source_folder_path": ""},
        )

        engine = create_engine(database_url)
        with engine.connect() as connection:
            folders = (
                connection.execute(text("SELECT source_folder_path FROM projects"))
                .scalars()
                .all()
            )
        engine.dispose()

    assert refused_over_http.status_code == 400
    assert refused_through_mcp.refused is True
    # One refusal, worded once in core, whichever door asked for it.
    assert refused_over_http.json()["detail"] in refused_through_mcp.text
    assert "" not in folders


def test_no_tool_finishes_a_review_or_exports_what_nobody_approved(
    tmp_path: Path,
) -> None:
    with _application(tmp_path) as (application, database_url, source_folder):
        run_id = _run_at_review(
            application, "Ungated intake portal", source_folder
        )

        finishing = call_tool(application.base_url, "finish_review", {"run_id": run_id})
        exporting = call_tool(
            application.base_url, "get_export", {"run_id": run_id, "export_format": "json"}
        )

        engine = create_engine(database_url)
        with engine.connect() as connection:
            run = connection.execute(
                text(
                    "SELECT status, export_json, review_finished_at FROM runs "
                    "WHERE id = :run_id"
                ),
                {"run_id": run_id},
            ).one()
        engine.dispose()

    assert finishing.refused is True
    assert exporting.refused is True
    assert run.status == "waiting for review"
    assert run.export_json is None
    assert run.review_finished_at is None


def test_a_tool_reports_only_the_run_state_the_database_holds(tmp_path: Path) -> None:
    with _application(tmp_path) as (application, database_url, source_folder):
        run_id = _run_at_review(
            application, "Read-back intake portal", source_folder
        )
        waiting = call_tool(application.base_url, "get_run_status", {"run_id": run_id})
        export_decision = next(
            decision
            for decision in waiting.payload["decisions"]
            if decision["kind"] == "export"
        )
        answered = call_tool(
            application.base_url,
            "submit_decision",
            {
                "run_id": run_id,
                "decision_id": export_decision["decision_id"],
                "outcome": "approved",
            },
        )
        after_answer = call_tool(
            application.base_url, "get_run_status", {"run_id": run_id}
        )

        engine = create_engine(database_url)
        with engine.connect() as connection:
            run = connection.execute(
                text(
                    "SELECT status, current_stage, export_json FROM runs "
                    "WHERE id = :run_id"
                ),
                {"run_id": run_id},
            ).one()
            outcomes = dict(
                connection.execute(
                    text("SELECT id, outcome FROM decisions WHERE run_id = :run_id"),
                    {"run_id": run_id},
                ).all()
            )
        engine.dispose()

    assert answered.refused is False
    assert after_answer.payload["status"] == run.status
    assert after_answer.payload["stage"] == run.current_stage
    assert after_answer.payload["exported"] is (run.export_json is not None)
    assert {
        decision["decision_id"]: decision["outcome"]
        for decision in after_answer.payload["decisions"]
    } == {str(decision_id): outcome for decision_id, outcome in outcomes.items()}


def test_a_core_refusal_reaches_a_tool_caller_with_its_cause_and_its_fix(
    tmp_path: Path,
) -> None:
    unknown_project_id = str(uuid4())
    unknown_run_id = str(uuid4())
    with _application(tmp_path) as (application, _database_url, _source_folder):
        unknown_project = call_tool(
            application.base_url, "start_run", {"project_id": unknown_project_id}
        )
        unknown_run = call_tool(
            application.base_url, "get_run_status", {"run_id": unknown_run_id}
        )
        unusable_format = call_tool(
            application.base_url,
            "get_export",
            {"run_id": unknown_run_id, "export_format": "spreadsheet"},
        )

    assert unknown_project.refused is True
    assert f"no project has id {unknown_project_id}" in unknown_project.text
    assert "POST /projects" in unknown_project.text

    assert unknown_run.refused is True
    assert f"no run has id {unknown_run_id}" in unknown_run.text
    assert "POST /runs" in unknown_run.text

    assert unusable_format.refused is True
    assert "'spreadsheet' is not an export format" in unusable_format.text
    assert "json or markdown" in unusable_format.text


def test_the_server_offers_only_the_six_locked_tools(tmp_path: Path) -> None:
    with _application(tmp_path) as (application, _database_url, _source_folder):
        offered = tool_names(application.base_url)

    assert offered == LOCKED_TOOLS
