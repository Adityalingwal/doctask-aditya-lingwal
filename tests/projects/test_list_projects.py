from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from app.database import build_connection_pool
from app.projects.list_projects import read_project_list
from app.refusal import ProjectsUnavailable
from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    extraction_answer,
    match_answer,
    match_marker,
    no_findings_answer,
    write_meeting_note,
)
from tests.runs.application import (
    PROJECT_ROOT,
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    temporary_database,
    wait_for_run_status,
    wait_until,
    write_script,
)


def test_a_project_with_no_runs_still_appears_in_the_project_list() -> None:
    listed = asyncio.run(_project_list_after_creating_one_project())

    assert listed["run_count"] == 0
    assert listed["most_recent_run_at"] is None
    assert listed["runs"] == []


async def _project_list_after_creating_one_project() -> dict[str, Any]:
    with temporary_database() as database_url:
        pool = build_connection_pool(database_url)
        await pool.open(wait=True)
        try:
            async with pool.connection() as connection:
                project_id = uuid4()
                await connection.execute(
                    "INSERT INTO projects (id, name, source_folder_path) "
                    "VALUES (%s, %s, %s)",
                    (project_id, "No runs yet", "sample-projects/intake-portal"),
                )
                listed = await read_project_list(
                    connection,
                    PROJECT_ROOT,
                    PROJECT_ROOT / "config" / "projects.yaml",
                )
                return next(
                    project
                    for project in listed["projects"]
                    if project["project_id"] == str(project_id)
                )
        finally:
            await pool.close()


def test_a_runs_stage_and_row_count_are_carried_alongside_its_status(
    tmp_path: Path,
) -> None:
    """L4/L6: a project card and a run row show a live run's stage strip, or
    an exported run's row count — neither of which the flat status word
    alone can answer, so `list_projects` must carry both."""
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    quote = write_meeting_note(source_folder, "meeting-note.md", "a weekly digest")
    script_path = tmp_path / "script.json"
    write_script(
        script_path,
        {
            extract_marker("meeting-note.md"): extraction_answer(
                "a weekly digest", quote
            ),
            match_marker(): match_answer(1),
            examine_marker(): no_findings_answer(),
        },
    )

    with temporary_database() as database_url:
        application = ApplicationProcess(
            database_url=database_url,
            script_path=script_path,
            call_log_path=tmp_path / "model-calls.jsonl",
            delay_seconds=1.0,
        )
        application.start()
        try:
            with application.client() as client:
                project_id = client.post(
                    "/projects",
                    json={
                        "name": "Stage and row count portal",
                        "source_folder_path": str(source_folder),
                    },
                ).json()["project_id"]
                run_id = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]

                # Ingest has not necessarily entered a stage the instant
                # POST /runs returns, so wait for one before reading the list.
                wait_until(
                    lambda: client.get(f"/runs/{run_id}").json()["stage"] is not None,
                    "the run enters a stage",
                )
                while_running = _project_of(client, project_id)["runs"][0]

                wait_for_run_status(client, run_id, "needs review")
                approve_every_decision_and_finish_review(client, run_id)
                wait_for_run_status(client, run_id, "done")

                once_exported = _project_of(client, project_id)["runs"][0]
        finally:
            application.stop()

    assert while_running["status"] == "running"
    assert while_running["stage"] is not None
    assert while_running["row_count"] is None

    assert once_exported["status"] == "done"
    assert once_exported["row_count"] == 1


def _project_of(client, project_id: str) -> dict[str, Any]:
    projects = client.get("/projects").json()["projects"]
    return next(project for project in projects if project["project_id"] == project_id)


def test_the_project_list_never_names_a_folder_the_projects_root_does_not_hold(
    tmp_path: Path,
) -> None:
    projects_root = tmp_path / "clients"
    projects_root.mkdir()
    (projects_root / "northside-dental").mkdir()
    (projects_root / "acme-intake").mkdir()
    # Neither of these is a folder directly inside the root, so neither may be
    # offered: a file sitting beside the folders, and a folder nested one
    # level too deep.
    (projects_root / "README.md").write_text("not a project folder")
    (projects_root / "northside-dental" / "not-a-top-level-folder").mkdir()

    config_path = tmp_path / "projects.yaml"
    config_path.write_text(f"projects_root: {projects_root}\n")

    folders = asyncio.run(_available_folders(config_path))

    assert folders == [
        f"{projects_root}/acme-intake",
        f"{projects_root}/northside-dental",
    ]


async def _available_folders(config_path: Path) -> list[str]:
    with temporary_database() as database_url:
        pool = build_connection_pool(database_url)
        await pool.open(wait=True)
        try:
            async with pool.connection() as connection:
                listed = await read_project_list(connection, PROJECT_ROOT, config_path)
                return listed["available_folders"]
        finally:
            await pool.close()


def test_an_unreadable_projects_config_fails_the_request_naming_the_file(
    tmp_path: Path,
) -> None:
    missing_config = tmp_path / "does-not-exist.yaml"

    with pytest.raises(ProjectsUnavailable, match=str(missing_config)):
        asyncio.run(_available_folders(missing_config))
