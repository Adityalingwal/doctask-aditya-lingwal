from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from app.database import build_connection_pool
from app.projects.list_projects import read_project_list
from app.refusal import ProjectsUnavailable
from tests.runs.application import PROJECT_ROOT, temporary_database


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
