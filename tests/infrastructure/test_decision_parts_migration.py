from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from tests.runs.application import PROJECT_ROOT, temporary_database


BEFORE_THE_COLUMN = "20260823_0024"
ADDED_COLUMN = "parts"
STORED_PARTS = {
    "row": {
        "row_number": 2,
        "label": "Register row 2",
        "cells": {
            "What was asked": "an email to the operations team on submit",
            "Written down": "Not known yet",
            "What testing found": "Not known yet",
            "Status": "Requested",
        },
    },
    "quotes": [
        {
            "source_line": 'client-requirements-v1.md, under "Requirements"',
            "quote": "An email notification to the operations team.",
        }
    ],
    "rule_text": None,
    "issue": None,
    "question": "Is this the same ask as row 2?",
    "if_approved": [{"cell": "Written down", "value": "Yes"}],
    "if_rejected": "A new row is created for this ask, with Written down: Yes.",
}


def test_decision_parts_migration_adds_and_removes_the_column() -> None:
    """The column arrives empty, holds one decision's parts, and goes cleanly.

    The export gate is answered by pressing a button rather than by reading a
    card, so it has no parts at all — which is why the column is nullable
    rather than defaulted to an empty object, a different claim entirely.
    """
    with temporary_database(upgrade_to=BEFORE_THE_COLUMN) as database_url:
        alembic_config = Config(PROJECT_ROOT / "alembic.ini")
        alembic_config.set_main_option("sqlalchemy.url", database_url)
        decision_id = _seed_a_decision(database_url)

        command.upgrade(alembic_config, "head")
        columns_after_upgrade = _column_names(database_url)
        before_anything_was_stored = _parts(database_url, decision_id)
        _store_parts(database_url, decision_id, STORED_PARTS)
        stored = _parts(database_url, decision_id)

        command.downgrade(alembic_config, BEFORE_THE_COLUMN)
        columns_after_downgrade = _column_names(database_url)

        command.upgrade(alembic_config, "head")
        after_second_upgrade = _parts(database_url, decision_id)

    assert ADDED_COLUMN in columns_after_upgrade
    assert before_anything_was_stored is None
    assert stored == STORED_PARTS
    assert ADDED_COLUMN not in columns_after_downgrade
    # The downgrade drops the column, so the parts go with it: the decision is
    # back to carrying its whole text and nothing taken apart.
    assert after_second_upgrade is None


def _seed_a_decision(database_url: str) -> Any:
    project_id, run_id, decision_id = uuid4(), uuid4(), uuid4()
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
                    "name": f"Decision parts {project_id}",
                    "folder": f"sample-projects/decision-parts-{project_id}",
                },
            )
            connection.execute(
                text(
                    "INSERT INTO runs (id, project_id, status) "
                    "VALUES (:id, :project_id, 'done')"
                ),
                {"id": run_id, "project_id": project_id},
            )
            connection.execute(
                text(
                    "INSERT INTO decisions (id, run_id, kind, question) "
                    "VALUES (:id, :run_id, 'possible match', :question)"
                ),
                {
                    "id": decision_id,
                    "run_id": run_id,
                    "question": "Is this the same ask as row 2?",
                },
            )
    finally:
        engine.dispose()
    return decision_id


def _store_parts(database_url: str, decision_id: Any, parts: dict[str, Any]) -> None:
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"UPDATE decisions SET {ADDED_COLUMN} = CAST(:parts AS jsonb) "
                    "WHERE id = :decision_id"
                ),
                {"parts": json.dumps(parts), "decision_id": decision_id},
            )
    finally:
        engine.dispose()


def _parts(database_url: str, decision_id: Any) -> Any:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return connection.execute(
                text(f"SELECT {ADDED_COLUMN} FROM decisions WHERE id = :decision_id"),
                {"decision_id": decision_id},
            ).scalar_one()
    finally:
        engine.dispose()


def _column_names(database_url: str) -> set[str]:
    engine = create_engine(database_url)
    try:
        return {column["name"] for column in inspect(engine).get_columns("decisions")}
    finally:
        engine.dispose()
