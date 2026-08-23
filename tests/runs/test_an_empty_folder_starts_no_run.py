from __future__ import annotations

import time
from pathlib import Path

import yaml

from app.runs.run_lifecycle import EMPTY_FOLDER_REFUSAL
from tests.interfaces.mcp_client import call_tool
from tests.runs.application import (
    PROJECT_ROOT,
    ApplicationProcess,
    temporary_database,
    temporary_project_folder,
    write_script,
)


SHIPPED_WATCHER_CONFIG = PROJECT_ROOT / "config" / "watcher.yaml"
POLL_SECONDS = 0.2
QUIET_SECONDS = 0.4
LONGER_THAN_A_QUIET_PERIOD = 2.0


def test_all_three_doors_refuse_a_run_over_an_empty_folder_in_the_same_words(
    tmp_path: Path,
) -> None:
    """A run over an empty folder reads nothing and would end early.

    The refusal lives in `start_or_queue_run`, the one function POST /runs,
    the MCP tool and the watcher all reach, so none of the three can grow its
    own wording — or its own idea of what an empty folder is (S15).
    """
    watcher_config_path = tmp_path / "watcher.yaml"
    watcher_config_path.write_text(
        f"poll_seconds: {POLL_SECONDS}\nquiet_seconds: {QUIET_SECONDS}\n",
        encoding="utf-8",
    )
    script_path = tmp_path / "script.json"
    write_script(script_path, {})

    with temporary_project_folder("empty-folder") as (_folder, folder_path):
        with temporary_database() as database_url:
            application = ApplicationProcess(
                database_url=database_url,
                script_path=script_path,
                call_log_path=tmp_path / "model-calls.jsonl",
                watcher_config_path=watcher_config_path,
            )
            application.start()
            try:
                with application.client() as client:
                    project_id = client.post(
                        "/projects", json={"source_folder_path": folder_path}
                    ).json()["project_id"]
                    over_http = client.post(
                        "/runs", json={"project_id": project_id}
                    )
                    through_mcp = call_tool(
                        application.base_url,
                        "start_run",
                        {"project_id": project_id},
                    )
                    # The watcher sees the folder settle over several polls and
                    # still starts nothing, because there is nothing to read.
                    time.sleep(LONGER_THAN_A_QUIET_PERIOD)
                    listed = client.get("/projects").json()
                    project = next(
                        entry
                        for entry in listed["projects"]
                        if entry["project_id"] == project_id
                    )
            finally:
                application.stop()

    assert over_http.status_code == 400
    assert over_http.json()["detail"] == EMPTY_FOLDER_REFUSAL
    assert through_mcp.refused
    # Both doors say the same words, so a machine caller and a person are told
    # the same thing to do about it.
    assert EMPTY_FOLDER_REFUSAL in through_mcp.text
    # Nothing started, through any door: the project exists and has no run.
    assert project["run_count"] == 0
    assert project["runs"] == []


def test_the_folder_list_says_which_folders_hold_a_file(tmp_path: Path) -> None:
    """The Add-project button offers a run only where there is one to have."""
    script_path = tmp_path / "script.json"
    write_script(script_path, {})

    with temporary_project_folder("has-files") as (with_a_file, folder_with_a_file):
        with temporary_project_folder("no-files") as (_empty, empty_folder):
            (with_a_file / "meeting-notes-10-mar.md").write_text(
                "# Notes\n\nThe client asked for an intake form.\n",
                encoding="utf-8",
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
                        listed = client.get("/projects").json()
                finally:
                    application.stop()

    has_files = listed["has_files_by_folder"]
    assert has_files[folder_with_a_file] is True
    assert has_files[empty_folder] is False


def test_the_shipped_watcher_config_polls_every_two_seconds_and_waits_five() -> None:
    """A demo waits out these two numbers, so they are the shipped file's own.

    Ten seconds of stillness after four-second polls made a person watching a
    folder wonder whether anything was working at all.
    """
    settings = yaml.safe_load(SHIPPED_WATCHER_CONFIG.read_text(encoding="utf-8"))

    assert settings["poll_seconds"] == 2
    assert settings["quiet_seconds"] == 5
