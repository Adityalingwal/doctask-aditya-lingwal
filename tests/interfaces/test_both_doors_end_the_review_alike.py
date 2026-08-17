from __future__ import annotations

from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from tests.runs.application import (
    ApplicationProcess,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
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
EXPORT_QUESTION = "Add this run's changes to the register?"


@contextmanager
def _two_projects_at_review(
    tmp_path: Path,
) -> Iterator[tuple[ApplicationProcess, str, str, str]]:
    """One application, two projects, each with a run parked at Review.

    Two projects rather than two runs of one, because a project holds at most
    one run in an active status — the second would be queued and never reach
    Review while the first waits.
    """
    with ExitStack() as folders:
        first_folder, first_path = folders.enter_context(
            temporary_project_folder("both-doors-http")
        )
        second_folder, second_path = folders.enter_context(
            temporary_project_folder("both-doors-mcp")
        )
        quote = write_meeting_note(first_folder, SOURCE_FILE, REQUIREMENT)
        write_meeting_note(second_folder, SOURCE_FILE, REQUIREMENT)
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
                with application.client() as client:
                    over_http = _run_at_review(client, first_path)
                    through_mcp = _run_at_review(client, second_path)
                yield application, database_url, over_http, through_mcp
            finally:
                application.stop()


def test_both_doors_add_this_runs_changes_to_the_register_alike(
    tmp_path: Path,
) -> None:
    with _two_projects_at_review(tmp_path) as (
        application,
        database_url,
        over_http,
        through_mcp,
    ):
        with application.client() as client:
            endpoint_answer = client.post(
                f"/runs/{over_http}/finish-review",
                json={"add_to_register": True},
            ).json()
        tool_answer = call_tool(
            application.base_url,
            "finish_review",
            {"run_id": through_mcp, "add_to_register": True},
        )

        with application.client() as client:
            wait_for_run_status(client, over_http, "done")
            wait_for_run_status(client, through_mcp, "done")
            endpoint_register = client.get(
                f"/projects/{_project_of(client, over_http)}/register"
            ).json()
            tool_register = client.get(
                f"/projects/{_project_of(client, through_mcp)}/register"
            ).json()

        assert _without_run_id(tool_answer.payload) == _without_run_id(endpoint_answer)
        assert _export_answer(database_url, over_http) == _export_answer(
            database_url, through_mcp
        )
        assert _export_answer(database_url, over_http) == (EXPORT_QUESTION, "approved")
        assert [row["cells"]["what_was_asked"] for row in endpoint_register["rows"]] == [
            row["cells"]["what_was_asked"] for row in tool_register["rows"]
        ]


def test_both_doors_discard_this_runs_changes_alike(tmp_path: Path) -> None:
    with _two_projects_at_review(tmp_path) as (
        application,
        database_url,
        over_http,
        through_mcp,
    ):
        with application.client() as client:
            endpoint_answer = client.post(
                f"/runs/{over_http}/finish-review",
                json={"add_to_register": False},
            ).json()
        tool_answer = call_tool(
            application.base_url,
            "finish_review",
            {"run_id": through_mcp, "add_to_register": False},
        )

        with application.client() as client:
            wait_for_run_status(client, over_http, "discarded")
            wait_for_run_status(client, through_mcp, "discarded")
            endpoint_register = client.get(
                f"/projects/{_project_of(client, over_http)}/register"
            )
            tool_register = client.get(
                f"/projects/{_project_of(client, through_mcp)}/register"
            )

        assert _without_run_id(tool_answer.payload) == _without_run_id(endpoint_answer)
        assert _export_answer(database_url, over_http) == _export_answer(
            database_url, through_mcp
        )
        assert _export_answer(database_url, over_http) == (EXPORT_QUESTION, "rejected")
        # Neither project committed anything, so both registers answer the
        # empty state — never an error.
        assert endpoint_register.status_code == tool_register.status_code == 200
        assert endpoint_register.json()["rows"] == tool_register.json()["rows"] == []


def _run_at_review(client: Any, source_folder_path: str) -> str:
    project_id = client.post(
        "/projects", json={"source_folder_path": source_folder_path}
    ).json()["project_id"]
    run_id = client.post("/runs", json={"project_id": project_id}).json()["run_id"]
    wait_for_run_status(client, run_id, "needs review")
    return run_id


def _project_of(client: Any, run_id: str) -> str:
    return client.get(f"/runs/{run_id}").json()["project_id"]


def _without_run_id(payload: dict[str, Any]) -> dict[str, Any]:
    """Both doors answer the same thing about different runs, so the id goes."""
    return {key: value for key, value in payload.items() if key != "run_id"}


def _export_answer(database_url: str, run_id: str) -> tuple[str, str]:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            recorded = connection.execute(
                text(
                    "SELECT question, outcome FROM decisions "
                    "WHERE run_id = :run_id AND kind = 'export'"
                ),
                {"run_id": run_id},
            ).one()
    finally:
        engine.dispose()
    return recorded.question, recorded.outcome
