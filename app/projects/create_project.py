from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from psycopg import AsyncConnection
from psycopg.errors import UniqueViolation

from app.projects.list_projects import read_projects_root
from app.refusal import UnusableRequest
from app.run_logging import log_run_event


DEMO_PROJECT_FOLDER = "sample-projects/intake-portal"
_NAME_WORD_SPLIT = re.compile(r"[-_]+")


class SourceFolderMissing(UnusableRequest):
    """Raised when a project is asked to watch a folder that is not there."""


class SourceFolderOutsideRoot(UnusableRequest):
    """Raised when a folder is not a direct child of the configured projects root."""


@dataclass(frozen=True)
class CreatedProject:
    """What `create_project` answers: the project's id, and whether this call
    is the one that made it. A caller that gets `created=False` changed
    nothing — the folder already had a project, and this is its id."""

    project_id: UUID
    created: bool


async def create_project(
    connection: AsyncConnection,
    source_folder_path: str,
    project_root: Path,
    projects_config_path: Path,
) -> CreatedProject:
    """Get-or-create the one project for this folder — every door uses this.

    The folder is the project's identity: two calls for the same folder
    return the same project and create nothing the second time, and a name is
    never accepted here — it is derived from the folder, once, below. A
    folder outside the configured projects root is refused before it is ever
    checked against the database, so a caller can never point a run at
    documents the operator did not put there.
    """
    if not source_folder_path.strip():
        raise UnusableRequest(
            "a project needs a source folder — give the path of the folder its "
            "documents arrive in, then create the project again."
        )

    resolved = _confined_folder(source_folder_path, project_root, projects_config_path)
    if not resolved.is_dir():
        raise SourceFolderMissing(
            f"the folder '{source_folder_path}' is not there — put it there, "
            "or use one that exists, then try again."
        )

    existing = await _project_over(connection, source_folder_path)
    if existing is not None:
        return CreatedProject(existing, created=False)

    project_id = uuid4()
    name = _name_derived_from_folder(source_folder_path)
    try:
        async with connection.transaction():
            await connection.execute(
                "INSERT INTO projects (id, name, source_folder_path) "
                "VALUES (%s, %s, %s)",
                (project_id, name, source_folder_path),
            )
    except UniqueViolation:
        # Another caller's create_project() won the race between the read
        # above and this insert — re-read rather than fail, so two callers
        # creating the same project at the same moment both reach its one id.
        # This is not speculative: the HTTP endpoint, the MCP tool and the
        # startup demo seed all reach this function independently, so two of
        # them can race over one folder without either being a bug on its own.
        existing = await _project_over(connection, source_folder_path)
        return CreatedProject(existing, created=False)
    return CreatedProject(project_id, created=True)


async def ensure_demo_project(
    connection: AsyncConnection,
    project_root: Path,
    projects_config_path: Path,
) -> UUID | None:
    """Make `docker compose up` alone enough to have something to run on.

    Get-or-create already makes a restart safe — a database that already
    holds a project over the demo folder gets its existing id back, not a
    second row — so this is nothing more than that one call, named for what
    it is used for at startup.
    """
    created = await create_project(
        connection, DEMO_PROJECT_FOLDER, project_root, projects_config_path
    )
    if not created.created:
        return None
    log_run_event(
        logging.INFO,
        "demo_project_created",
        f"Created the demo project reading {DEMO_PROJECT_FOLDER}; start a run "
        "against it with POST /runs.",
        None,
        project_id=str(created.project_id),
    )
    return created.project_id


async def _project_over(
    connection: AsyncConnection, source_folder_path: str
) -> UUID | None:
    found = await connection.execute(
        "SELECT id FROM projects WHERE source_folder_path = %s",
        (source_folder_path,),
    )
    row = await found.fetchone()
    return row["id"] if row is not None else None


def _confined_folder(
    source_folder_path: str,
    project_root: Path,
    projects_config_path: Path,
) -> Path:
    """The real folder a caller named, or a refusal naming why it is refused.

    Nothing legitimate ever sends an absolute path — the dropdown and the
    demo seed both send `sample-projects/<folder>` — so an absolute path is
    refused outright rather than resolved and checked; that also covers `/`
    and `/workspace` naming something real but outside the root. `..` is
    refused the same way. What is left is resolved with `Path.resolve()`
    (which also collapses a symlink) and must sit directly inside the
    projects root — not the root itself, and not two levels down.
    """
    projects_root_name, resolved_root = read_projects_root(
        project_root, projects_config_path
    )
    candidate = Path(source_folder_path)
    if candidate.is_absolute():
        raise SourceFolderOutsideRoot(
            f"'{source_folder_path}' is an absolute path — give a folder "
            f"inside {projects_root_name}, such as "
            f"'{projects_root_name}/<folder>', then try again."
        )
    if ".." in candidate.parts:
        raise SourceFolderOutsideRoot(
            f"'{source_folder_path}' reaches outside {projects_root_name} with "
            "'..' — give a folder directly inside it instead, then try again."
        )
    resolved_candidate = (project_root / candidate).resolve()
    if resolved_candidate.parent != resolved_root:
        raise SourceFolderOutsideRoot(
            f"'{source_folder_path}' does not sit directly inside "
            f"{projects_root_name} — put the folder there, or name one that "
            "is already directly inside it, then try again."
        )
    return resolved_candidate


def _name_derived_from_folder(source_folder_path: str) -> str:
    """`intake-portal` -> `Intake Portal`: dashes and underscores become
    spaces, each word capitalised. The export heading reads a name, not a
    slug — `# Requirements-to-Delivery Register — Intake Portal`."""
    segment = source_folder_path.rstrip("/").rsplit("/", 1)[-1]
    words = [word for word in _NAME_WORD_SPLIT.split(segment) if word != ""]
    return " ".join(word[0].upper() + word[1:] for word in words)
