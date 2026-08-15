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
    substituted with `created_at`, and the list carries no cap. `stage` and
    `row_count` are carried alongside `status` because the project card and
    the run row (L4/L6) show a live run's stage strip and an exported run's
    row count, neither of which the flat status word alone can answer.
    """
    result = await connection.execute(
        "SELECT projects.id AS project_id, projects.name AS project_name, "
        "projects.source_folder_path AS source_folder_path, "
        "projects.created_at AS project_created_at, "
        "runs.id AS run_id, runs.status AS run_status, "
        "runs.current_stage AS run_current_stage, "
        "runs.started_at AS run_started_at, runs.created_at AS run_created_at, "
        "runs.finished_stages AS run_finished_stages, "
        "jsonb_array_length(runs.export_json -> 'rows') AS run_row_count, "
        "(SELECT count(*) FROM decisions WHERE decisions.run_id = runs.id "
        "AND decisions.outcome IS NULL) AS waiting_decisions, "
        "ROW_NUMBER() OVER (PARTITION BY runs.project_id ORDER BY "
        "runs.created_at ASC) AS run_number "
        "FROM projects LEFT JOIN runs ON runs.project_id = projects.id "
        "ORDER BY projects.created_at ASC, runs.created_at DESC"
    )
    rows = await result.fetchall()
    projects_root, available_folders = _available_folders(
        project_root, projects_config_path
    )
    return {
        "projects": _grouped_by_project(rows),
        "projects_root": projects_root,
        "available_folders": available_folders,
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
                "stage": row["run_current_stage"],
                # Sent unchanged rather than substituted with created_at: a run
                # that has not started must say so, not report a moment it
                # started as a fact.
                "started_at": _isoformat(row["run_started_at"]),
                "waiting_decisions": row["waiting_decisions"],
                "finished_stages": ordered_finished_stages(row["run_finished_stages"]),
                "row_count": row["run_row_count"],
            }
        )
    return list(projects.values())


def _isoformat(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def read_projects_root(
    project_root: Path, projects_config_path: Path
) -> tuple[str, Path]:
    """The projects root as configured, and as a real, resolved directory.

    Shared with `create_project` (app/projects/create_project.py), which
    confines every caller-supplied folder to this same resolved root — one
    reading of `config/projects.yaml`, so the dropdown and the confinement
    check can never disagree about where the root actually is.
    """
    parsed = _read_projects_config(projects_config_path)
    projects_root = Path(parsed[PROJECTS_ROOT_KEY])
    resolved_root = (
        projects_root if projects_root.is_absolute() else project_root / projects_root
    ).resolve()
    if not resolved_root.is_dir():
        raise ProjectsUnavailable(
            f"{projects_config_path} names '{projects_root}' as the projects "
            f"root, but {resolved_root} does not exist — create it, or point "
            f"{PROJECTS_ROOT_KEY} at a folder that does, then try again."
        )
    return str(projects_root), resolved_root


def _available_folders(
    project_root: Path, projects_config_path: Path
) -> tuple[str, list[str]]:
    """The projects root, and the folders a person may point a new project at.

    Read fresh on every call, the same unconditional-read philosophy as L1: the
    dropdown is never stale because nothing about it is cached. The root is
    returned alongside the folders because the Add-project box (L8/screen 2)
    states where a new folder must be put even when none exist there yet.
    """
    projects_root, resolved_root = read_projects_root(
        project_root, projects_config_path
    )
    folders = sorted(
        f"{projects_root}/{entry.name}"
        for entry in resolved_root.iterdir()
        if entry.is_dir()
    )
    return projects_root, folders


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
