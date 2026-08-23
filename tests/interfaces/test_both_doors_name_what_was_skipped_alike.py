from __future__ import annotations

from pathlib import Path

from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    extraction_answer,
    match_answer,
    match_marker,
    no_findings_answer,
    unrelated_extraction_answer,
    write_meeting_note,
)
from tests.interfaces.mcp_client import call_tool
from tests.runs.application import (
    ApplicationProcess,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)


SCOPE_FILE = "12-march-scope.md"
UNRELATED_FILE = "clinic-staff-leave-policy.md"
REQUIREMENT = "an email to the operations team on intake form submit"
UNRELATED_ASK = "a window seat on the Tuesday flight"


def test_both_doors_call_the_list_not_used_and_report_the_same_entries(
    tmp_path: Path,
) -> None:
    """One name for one list, whichever door asks — and one answer behind both."""
    with temporary_project_folder("not-used-doors") as (source_folder, folder_path):
        quote = write_meeting_note(source_folder, SCOPE_FILE, REQUIREMENT)
        write_meeting_note(source_folder, UNRELATED_FILE, UNRELATED_ASK)
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                extract_marker(SCOPE_FILE): extraction_answer(REQUIREMENT, quote),
                extract_marker(UNRELATED_FILE): unrelated_extraction_answer(),
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
                    over_http = wait_for_run_status(client, run_id, "needs review")
                through_mcp = call_tool(
                    application.base_url, "get_run_status", {"run_id": run_id}
                ).payload
            finally:
                application.stop()

    assert "skipped" not in over_http
    assert "skipped" not in through_mcp
    assert over_http["not_used"] == through_mcp["not_used"]
    assert [entry["kind"] for entry in over_http["not_used"]] == ["not read"]
    assert over_http == through_mcp
