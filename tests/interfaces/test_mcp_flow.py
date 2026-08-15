from __future__ import annotations

from pathlib import Path

from tests.runs.application import (
    ApplicationProcess,
    temporary_database,
    wait_until,
    write_script,
)
from tests.interfaces.mcp_client import call_tool
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
WAITING_FOR_REVIEW = "needs review"
DONE = "done"


def _status_of(base_url: str, run_id: str, status: str) -> dict | None:
    reported = call_tool(base_url, "get_run_status", {"run_id": run_id})
    return reported.payload if reported.payload["status"] == status else None


def test_a_machine_drives_a_whole_run_through_the_mcp_tools(tmp_path: Path) -> None:
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
            base_url = application.base_url
            created = call_tool(
                base_url,
                "create_project",
                {
                    "name": "Machine-driven intake portal",
                    "source_folder_path": str(source_folder),
                },
            )
            started = call_tool(
                base_url, "start_run", {"project_id": created.payload["project_id"]}
            )
            run_id = started.payload["run_id"]
            at_review = wait_until(
                lambda: _status_of(base_url, run_id, WAITING_FOR_REVIEW),
                "the run reports it is needs review",
            )
            export_decision = next(
                decision
                for decision in at_review["decisions"]
                if decision["kind"] == "export"
            )
            answered = call_tool(
                base_url,
                "submit_decision",
                {
                    "run_id": run_id,
                    "decision_id": export_decision["decision_id"],
                    "outcome": "approved",
                },
            )
            finished = call_tool(base_url, "finish_review", {"run_id": run_id})
            committed = wait_until(
                lambda: _status_of(base_url, run_id, DONE),
                "the run reports it is done",
            )
            exported = call_tool(
                base_url,
                "get_export",
                {"run_id": run_id, "export_format": "json"},
            )
            as_markdown = call_tool(
                base_url,
                "get_export",
                {"run_id": run_id, "export_format": "markdown"},
            )
        finally:
            application.stop()

    assert started.payload["status"] == "running"
    assert at_review["examine"]["rows_examined"] == 1
    assert answered.payload == {
        "decision_id": export_decision["decision_id"],
        "outcome": "approved",
    }
    assert finished.payload == {"run_id": run_id, "status": "review finished"}
    assert committed["exported"] is True
    assert [row["cells"]["what_was_asked"] for row in exported.payload["rows"]] == [
        REQUIREMENT
    ]
    assert exported.payload["run_id"] == run_id
    assert REQUIREMENT in as_markdown.payload
