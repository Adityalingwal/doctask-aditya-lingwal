from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID, uuid4

from psycopg import AsyncConnection

from app.refusal import UnusableRequest
from app.run_logging import log_run_event


DEMO_PROJECT_NAME = "Acme intake portal"
DEMO_PROJECT_FOLDER = "sample-projects/intake-portal"


class SourceFolderMissing(UnusableRequest):
    """Raised when a project is asked to watch a folder that is not there."""


async def create_project(
    connection: AsyncConnection,
    name: str,
    source_folder_path: str,
    project_root: Path,
) -> UUID:
    """The one way a project is created — the endpoint and startup both use it."""
    folder = Path(source_folder_path)
    resolved = folder if folder.is_absolute() else project_root / folder
    if not resolved.is_dir():
        raise SourceFolderMissing(
            f"the source folder '{source_folder_path}' does not exist — create "
            "it, or give a path that does, then create the project again."
        )

    project_id = uuid4()
    await connection.execute(
        "INSERT INTO projects (id, name, source_folder_path) VALUES (%s, %s, %s)",
        (project_id, name, source_folder_path),
    )
    return project_id


async def ensure_demo_project(
    connection: AsyncConnection,
    project_root: Path,
) -> UUID | None:
    """Make `docker compose up` alone enough to have something to run on.

    The check is on the demo project itself rather than on the projects table
    being empty, so a database that already holds other projects still gets the
    demo one, and a restart never creates a second copy.
    """
    existing = await connection.execute(
        "SELECT id FROM projects WHERE name = %s",
        (DEMO_PROJECT_NAME,),
    )
    if await existing.fetchone() is not None:
        return None

    project_id = await create_project(
        connection,
        DEMO_PROJECT_NAME,
        DEMO_PROJECT_FOLDER,
        project_root,
    )
    log_run_event(
        logging.INFO,
        "demo_project_created",
        f"Created the demo project '{DEMO_PROJECT_NAME}' reading "
        f"{DEMO_PROJECT_FOLDER}; start a run against it with POST /runs.",
        None,
        project_id=str(project_id),
    )
    return project_id
