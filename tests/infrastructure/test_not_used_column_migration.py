from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from tests.runs.application import PROJECT_ROOT, temporary_database


BEFORE_THE_RENAME = "20260817_0019"
EARLIER_COLUMN = "skipped"
RENAMED_COLUMN = "not_used"
# One entry of each weight the list holds, written as the pipeline writes them.
STORED_ENTRIES = [
    {
        "kind": "already read",
        "file": "12-march-scope.md",
        "reason": "Already read, and unchanged since.",
    },
    {
        "kind": "not read",
        "file": "clinic-staff-leave-policy.md",
        "reason": "This document is not related to this client or project.",
    },
    {
        "kind": "dropped",
        "file": "meeting-notes-10-mar.md",
        "summary": "a weekly AI summary of all open tickets",
        "quote": "the client wants a weekly AI summary of every open ticket",
        "reason": (
            "These words were not found in the file, so this requirement was dropped."
        ),
    },
]


def test_the_rename_carries_every_entry_across_and_the_downgrade_carries_it_back() -> None:
    """The column changes name; what a run recorded in it does not change at all."""
    with temporary_database(upgrade_to=BEFORE_THE_RENAME) as database_url:
        run_id = _seed_a_run_holding_the_entries(database_url)
        alembic_config = Config(PROJECT_ROOT / "alembic.ini")
        alembic_config.set_main_option("sqlalchemy.url", database_url)
        engine = create_engine(database_url)
        try:
            before = _entries(engine, EARLIER_COLUMN, run_id)

            command.upgrade(alembic_config, "head")
            renamed_columns = _column_names(engine)
            after_upgrade = _entries(engine, RENAMED_COLUMN, run_id)

            command.downgrade(alembic_config, BEFORE_THE_RENAME)
            restored_columns = _column_names(engine)
            after_downgrade = _entries(engine, EARLIER_COLUMN, run_id)

            command.upgrade(alembic_config, "head")
            after_second_upgrade = _entries(engine, RENAMED_COLUMN, run_id)
        finally:
            engine.dispose()

    assert RENAMED_COLUMN in renamed_columns
    assert EARLIER_COLUMN not in renamed_columns
    assert EARLIER_COLUMN in restored_columns
    assert RENAMED_COLUMN not in restored_columns
    # Byte for byte, not merely equal as parsed JSON: the migration renames the
    # column and rewrites nothing stored inside it.
    assert after_upgrade == before
    assert after_downgrade == before
    assert after_second_upgrade == before


def _seed_a_run_holding_the_entries(database_url: str) -> Any:
    project_id = uuid4()
    run_id = uuid4()
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO projects (id, name, source_folder_path) "
                    "VALUES (:id, :name, :folder)"
                ),
                {
                    "id": project_id,
                    "name": f"Not used {project_id}",
                    "folder": f"sample-projects/not-used-{project_id}",
                },
            )
            connection.execute(
                text(
                    f"INSERT INTO runs (id, project_id, status, {EARLIER_COLUMN}) "
                    "VALUES (:id, :project_id, 'done', CAST(:entries AS jsonb))"
                ),
                {
                    "id": run_id,
                    "project_id": project_id,
                    "entries": json.dumps(STORED_ENTRIES),
                },
            )
    finally:
        engine.dispose()
    return run_id


def _entries(engine: Any, column: str, run_id: Any) -> str:
    with engine.connect() as connection:
        return connection.execute(
            text(f"SELECT {column}::text FROM runs WHERE id = :run_id"),
            {"run_id": run_id},
        ).scalar_one()


def _column_names(engine: Any) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns("runs")}
