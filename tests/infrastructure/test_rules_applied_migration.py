from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from tests.runs.application import PROJECT_ROOT, temporary_database


BEFORE_THE_COLUMN = "20260823_0022"
ADDED_COLUMN = "rules_applied"
APPLIED_RULES = ["R1", "R5"]


def test_rules_applied_migration_adds_and_removes_the_column() -> None:
    """The column arrives empty, holds a run's applied rule ids, and goes cleanly.

    A run written before the column existed answers null — it never recorded
    which rules ran — which is why the column is nullable rather than defaulted
    to an empty list, a different claim entirely.
    """
    with temporary_database(upgrade_to=BEFORE_THE_COLUMN) as database_url:
        alembic_config = Config(PROJECT_ROOT / "alembic.ini")
        alembic_config.set_main_option("sqlalchemy.url", database_url)
        run_id = _seed_a_run(database_url)

        command.upgrade(alembic_config, "head")
        columns_after_upgrade = _column_names(database_url)
        before_examine_ran = _rules_applied(database_url, run_id)
        _store_applied_rules(database_url, run_id, APPLIED_RULES)
        stored = _rules_applied(database_url, run_id)

        command.downgrade(alembic_config, BEFORE_THE_COLUMN)
        columns_after_downgrade = _column_names(database_url)

        command.upgrade(alembic_config, "head")
        after_second_upgrade = _rules_applied(database_url, run_id)

    assert ADDED_COLUMN in columns_after_upgrade
    assert before_examine_ran is None
    assert stored == APPLIED_RULES
    assert ADDED_COLUMN not in columns_after_downgrade
    # The downgrade drops the column, so the values go with it: the run is back
    # to never having recorded which rules ran.
    assert after_second_upgrade is None


def _seed_a_run(database_url: str) -> Any:
    project_id, run_id = uuid4(), uuid4()
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
                    "name": f"Rules applied {project_id}",
                    "folder": f"sample-projects/rules-applied-{project_id}",
                },
            )
            connection.execute(
                text(
                    "INSERT INTO runs (id, project_id, status) "
                    "VALUES (:id, :project_id, 'done')"
                ),
                {"id": run_id, "project_id": project_id},
            )
    finally:
        engine.dispose()
    return run_id


def _store_applied_rules(
    database_url: str,
    run_id: Any,
    rule_ids: list[str],
) -> None:
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"UPDATE runs SET {ADDED_COLUMN} = CAST(:applied AS jsonb) "
                    "WHERE id = :run_id"
                ),
                {"applied": json.dumps(rule_ids), "run_id": run_id},
            )
    finally:
        engine.dispose()


def _rules_applied(database_url: str, run_id: Any) -> Any:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return connection.execute(
                text(f"SELECT {ADDED_COLUMN} FROM runs WHERE id = :run_id"),
                {"run_id": run_id},
            ).scalar_one()
    finally:
        engine.dispose()


def _column_names(database_url: str) -> set[str]:
    engine = create_engine(database_url)
    try:
        return {column["name"] for column in inspect(engine).get_columns("runs")}
    finally:
        engine.dispose()
