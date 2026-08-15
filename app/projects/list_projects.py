from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from psycopg import AsyncConnection

from app.refusal import ProjectsUnavailable
from app.runs.finished_stages import ordered_finished_stages


PROJECTS_ROOT_KEY = "projects_root"


async def read_project_list(
    connection: AsyncConnection,
    project_root: Path,
    projects_config_path: Path,
) -> dict[str, Any]:
    """Every project with its runs nested, plus the folders a new one may watch.

    One answer for the whole screen (L1): the projects column and the
    Add-project dropdown both come from this single unconditional read, so
    there is no per-project fetch and no conditional refresh to reason about.
    A run's own `started_at` is sent as `null` when it has not started, never
    substituted with `created_at`, and the list carries no cap.
    """
    result = await connection.execute(
        "SELECT projects.id AS project_id, projects.name AS project_name, "
        "projects.source_folder_path AS source_folder_path, "
        "projects.created_at AS project_created_at, "
        "runs.id AS run_id, runs.status AS run_status, "
        "runs.started_at AS run_started_at, runs.created_at AS run_created_at, "
        "runs.finished_stages AS run_finished_stages, "
        "(SELECT count(*) FROM decisions WHERE decisions.run_id = runs.id "
        "AND decisions.outcome IS NULL) AS waiting_decisions, "
        "ROW_NUMBER() OVER (PARTITION BY runs.project_id ORDER BY "
        "runs.created_at ASC) AS run_number "
        "FROM projects LEFT JOIN runs ON runs.project_id = projects.id "
        "ORDER BY projects.created_at ASC, runs.created_at DESC"
    )
    rows = await result.fetchall()
    return {
        "projects": _grouped_by_project(rows),
        "available_folders": _available_folders(project_root, projects_config_path),
    }


def _grouped_by_project(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    projects: dict[Any, dict[str, Any]] = {}
    for row in rows:
        project = projects.get(row["project_id"])
        if project is None:
            project = {
                "project_id": str(row["project_id"]),
                "name": row["project_name"],
                "source_folder_path": row["source_folder_path"],
                "run_count": 0,
                "most_recent_run_at": None,
                "runs": [],
            }
            projects[row["project_id"]] = project

        if row["run_id"] is None:
            # A LEFT JOIN row for a project with no runs at all (never-do
            # test 2): every other field stays at its just-initialised default.
            continue

        project["run_count"] += 1
        # The rows for one project arrive newest run first, so the first run
        # row seen is the most recent one.
        if project["most_recent_run_at"] is None:
            project["most_recent_run_at"] = _isoformat(
                row["run_started_at"] or row["run_created_at"]
            )
        project["runs"].append(
            {
                "run_id": str(row["run_id"]),
                "run_number": row["run_number"],
                "status": row["run_status"],
                # Sent unchanged rather than substituted with created_at: a run
                # that has not started must say so, not report a moment it
                # started as a fact.
                "started_at": _isoformat(row["run_started_at"]),
                "waiting_decisions": row["waiting_decisions"],
                "finished_stages": ordered_finished_stages(row["run_finished_stages"]),
            }
        )
    return list(projects.values())


def _isoformat(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def _available_folders(project_root: Path, projects_config_path: Path) -> list[str]:
    """The folders a person may point a new project at, as project-root-relative paths.

    Read fresh on every call, the same unconditional-read philosophy as L1: the
    dropdown is never stale because nothing about it is cached.
    """
    parsed = _read_projects_config(projects_config_path)
    projects_root = Path(parsed[PROJECTS_ROOT_KEY])
    resolved_root = (
        projects_root if projects_root.is_absolute() else project_root / projects_root
    )
    if not resolved_root.is_dir():
        raise ProjectsUnavailable(
            f"{projects_config_path} names '{projects_root}' as the projects "
            f"root, but {resolved_root} does not exist — create it, or point "
            f"{PROJECTS_ROOT_KEY} at a folder that does, then try again."
        )
    return sorted(
        f"{projects_root}/{entry.name}"
        for entry in resolved_root.iterdir()
        if entry.is_dir()
    )


def _read_projects_config(projects_config_path: Path) -> dict[str, Any]:
    try:
        parsed = yaml.safe_load(projects_config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ProjectsUnavailable(
            f"{projects_config_path} is missing — restore config/projects.yaml, "
            f"which holds {PROJECTS_ROOT_KEY}, then try again."
        ) from error
    except OSError as error:
        raise ProjectsUnavailable(
            f"{projects_config_path} could not be read ({error.strerror}) — "
            "check its permissions, then try again."
        ) from error
    except yaml.YAMLError as error:
        raise ProjectsUnavailable(
            f"{projects_config_path} is not valid YAML ({error}) — fix its "
            "syntax, then try again."
        ) from error

    if not isinstance(parsed, dict) or PROJECTS_ROOT_KEY not in parsed:
        raise ProjectsUnavailable(
            f"{projects_config_path} must hold a YAML mapping with "
            f"{PROJECTS_ROOT_KEY} in it — restore that key, then try again."
        )
    return parsed
