from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from tests.runs.application import migrate, temporary_database


BEFORE_THE_RENAME = "20260817_0018"
EARLIER_STATUS = "export rejected"
RENAMED_STATUS = "discarded"
# Every value the constraint held before this rename. One run per status, each
# on a project of its own: the two partial unique indexes allow one
# running/needs-review run and one queued run per project.
STATUSES_BEFORE = (
    "queued",
    "running",
    "needs review",
    "done",
    EARLIER_STATUS,
    "failed",
    "no changes",
)


def test_the_run_status_constraint_refuses_export_rejected_and_accepts_discarded() -> None:
    with temporary_database(upgrade_to=BEFORE_THE_RENAME) as database_url:
        project_ids = _seed_a_run_per_status(database_url)

        migrate(database_url, "head")

        with pytest.raises(IntegrityError):
            _insert_run(database_url, project_ids[EARLIER_STATUS], EARLIER_STATUS)
        _insert_run(database_url, uuid4(), RENAMED_STATUS, new_project=True)


def test_the_rename_rewrites_the_refused_run_and_leaves_every_other_status_alone() -> None:
    with temporary_database(upgrade_to=BEFORE_THE_RENAME) as database_url:
        _seed_a_run_per_status(database_url)

        migrate(database_url, "head")

        assert sorted(_statuses(database_url)) == sorted(
            RENAMED_STATUS if status == EARLIER_STATUS else status
            for status in STATUSES_BEFORE
        )


def _seed_a_run_per_status(database_url: str) -> dict[str, Any]:
    """One run per status, each on its own project, and the project ids back."""
    project_ids: dict[str, Any] = {}
    engine = create_engine(database_url)
    try:
        for status in STATUSES_BEFORE:
            project_id = uuid4()
            project_ids[status] = project_id
            with engine.begin() as connection:
                _insert_project(connection, project_id)
                connection.execute(
                    text(
                        "INSERT INTO runs (id, project_id, status) "
                        "VALUES (:id, :project_id, :status)"
                    ),
                    {"id": uuid4(), "project_id": project_id, "status": status},
                )
    finally:
        engine.dispose()
    return project_ids


def _insert_run(
    database_url: str,
    project_id: Any,
    status: str,
    new_project: bool = False,
) -> None:
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            if new_project:
                _insert_project(connection, project_id)
            connection.execute(
                text(
                    "INSERT INTO runs (id, project_id, status) "
                    "VALUES (:id, :project_id, :status)"
                ),
                {"id": uuid4(), "project_id": project_id, "status": status},
            )
    finally:
        engine.dispose()


def _insert_project(connection: Any, project_id: Any) -> None:
    connection.execute(
        text(
            "INSERT INTO projects (id, name, source_folder_path) "
            "VALUES (:id, :name, :folder)"
        ),
        {
            "id": project_id,
            "name": f"Discarded status {project_id}",
            "folder": f"sample-projects/discarded-status-{project_id}",
        },
    )


def _statuses(database_url: str) -> list[str]:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return list(
                connection.execute(text("SELECT status FROM runs")).scalars().all()
            )
    finally:
        engine.dispose()
