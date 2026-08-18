from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from psycopg import AsyncConnection
from psycopg.errors import UniqueViolation

from app.projects.list_projects import read_projects_root
from app.refusal import UnusableRequest


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

    resolved, folder = _confined_folder(
        source_folder_path, project_root, projects_config_path
    )
    if not resolved.is_dir():
        raise SourceFolderMissing(
            f"the folder '{source_folder_path}' is not there — put it there, "
            "or use one that exists, then try again."
        )

    # From here on the resolved folder is the identity, never the string the
    # caller typed: `sample-projects/x`, `sample-projects/./x` and
    # `sample-projects/x/` name one directory, and stored raw they would be
    # three projects over it, each with its own register, lock and watcher.
    existing = await _project_over(connection, folder)
    if existing is not None:
        return CreatedProject(existing, created=False)

    project_id = uuid4()
    name = _name_derived_from_folder(folder)
    try:
        async with connection.transaction():
            await connection.execute(
                "INSERT INTO projects (id, name, source_folder_path) "
                "VALUES (%s, %s, %s)",
                (project_id, name, folder),
            )
    except UniqueViolation:
        # Another caller's create_project() won the race between the read
        # above and this insert — re-read rather than fail, so two callers
        # creating the same project at the same moment both reach its one id.
        # This is not speculative: the HTTP endpoint and the MCP tool both
        # reach this function independently, so two of them can race over one
        # folder without either being a bug on its own.
        existing = await _project_over(connection, folder)
        return CreatedProject(existing, created=False)
    return CreatedProject(project_id, created=True)


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
) -> tuple[Path, str]:
    """The real folder a caller named, and the one spelling this system stores.

    Nothing legitimate ever sends an absolute path — the dropdown always
    sends `sample-projects/<folder>` — so an absolute path is refused
    outright rather than resolved and checked; that also covers `/`
    and `/workspace` naming something real but outside the root. `..` is
    refused the same way. What is left is resolved with `Path.resolve()`
    (which also collapses a symlink) and must sit directly inside the
    projects root — not the root itself, and not two levels down. What comes
    back beside it is that folder written one way, `<root>/<folder>`, which is
    what every later reader stores and compares.
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
    return resolved_candidate, f"{projects_root_name}/{resolved_candidate.name}"


def _name_derived_from_folder(source_folder_path: str) -> str:
    """`intake-portal` -> `Intake Portal`: dashes and underscores become
    spaces, each word capitalised. The export heading reads a name, not a
    slug — `# Requirements-to-Delivery Register — Intake Portal`."""
    segment = source_folder_path.rstrip("/").rsplit("/", 1)[-1]
    words = [word for word in _NAME_WORD_SPLIT.split(segment) if word != ""]
    return " ".join(word[0].upper() + word[1:] for word in words)
