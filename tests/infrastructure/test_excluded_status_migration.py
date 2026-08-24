from __future__ import annotations

from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from tests.runs.application import PROJECT_ROOT, temporary_database


BEFORE_EXCLUDED = "20260823_0025"
CONSTRAINT_NAME = "ck_register_rows_status"


def test_the_excluded_status_migration_round_trips_real_data() -> None:
    """Downgrade keeps the row usable, and upgrade restores the allowance."""
    with temporary_database(upgrade_to=BEFORE_EXCLUDED) as database_url:
        alembic_config = Config(PROJECT_ROOT / "alembic.ini")
        alembic_config.set_main_option("sqlalchemy.url", database_url)

        command.upgrade(alembic_config, "head")
        _seed_excluded_row(database_url)
        assert _status(database_url) == "Excluded"
        assert "Excluded" in _constraint(database_url)

        command.downgrade(alembic_config, BEFORE_EXCLUDED)
        assert _status(database_url) == "Requested"
        assert "Excluded" not in _constraint(database_url)

        command.upgrade(alembic_config, "head")
        assert _status(database_url) == "Requested"
        assert "Excluded" in _constraint(database_url)


def _seed_excluded_row(database_url: str) -> None:
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
                    "name": f"Excluded {project_id}",
                    "folder": f"sample-projects/excluded-{project_id}",
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
                    "INSERT INTO register_rows (id, project_id, "
                    "what_was_asked, in_writing, what_testing_found, status, "
                    "fingerprint, row_number, proposed_by_run_id, is_committed) "
                    "VALUES (:id, :project_id, 'mobile barcode scanning', "
                    "'Excluded', 'Not known yet', 'Excluded', 'fingerprint', "
                    "1, :run_id, true)"
                ),
                {
                    "id": uuid4(),
                    "project_id": project_id,
                    "run_id": run_id,
                },
            )
    finally:
        engine.dispose()


def _status(database_url: str) -> str:
    return _scalar(database_url, "SELECT status FROM register_rows")


def _constraint(database_url: str) -> str:
    return _scalar(
        database_url,
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        f"WHERE conname = '{CONSTRAINT_NAME}'",
    )


def _scalar(database_url: str, query: str) -> str:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return str(connection.execute(text(query)).scalar_one())
    finally:
        engine.dispose()
