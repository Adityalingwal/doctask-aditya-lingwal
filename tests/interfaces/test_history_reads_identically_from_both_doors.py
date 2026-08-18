from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    extraction_answer,
    match_answer,
    match_marker,
    no_findings_answer,
    write_meeting_note,
)
from tests.interfaces.mcp_client import call_tool
from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)


SOURCE_FILE = "meeting-note.md"
REQUIREMENT = "an email to the operations team on intake form submit"


@contextmanager
def _application(tmp_path: Path) -> Iterator[tuple[ApplicationProcess, str]]:
    with temporary_project_folder("both-doors-history") as (
        source_folder,
        source_folder_path,
    ):
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
                yield application, source_folder_path
            finally:
                application.stop()


def test_the_http_door_and_the_get_history_tool_answer_byte_identical_payloads(
    tmp_path: Path,
) -> None:
    with _application(tmp_path) as (application, source_folder_path):
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

            over_http = client.get(f"/projects/{project_id}/history").json()

        through_mcp = call_tool(
            application.base_url, "get_history", {"project_id": project_id}
        )

    assert through_mcp.refused is False
    assert through_mcp.payload == over_http
    # The grouping and the ordering happen once, in the core function, so the
    # two doors cannot drift into showing two different histories.
    assert json.dumps(through_mcp.payload, sort_keys=True) == json.dumps(
        over_http, sort_keys=True
    )
    assert over_http["entries"] != []
