from __future__ import annotations

import os
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine, inspect, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import IntegrityError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_URL_ENVIRONMENT_VARIABLE = "DATABASE_URL"
DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres@db:5432/register"
POSTGRES_MAINTENANCE_DATABASE = "postgres"
TEST_DATABASE_PREFIX = "register_test_"
DOMAIN_TABLES = {
    "projects",
    "runs",
    "documents",
    "register_rows",
    "citations",
    "decisions",
    "audit",
}
EXPECTED_COLUMNS = {
    "projects": {"id", "name", "source_folder_path", "created_at"},
    "runs": {
        "id",
        "project_id",
        "status",
        "current_stage",
        "started_at",
        "finished_at",
        "stage_timings",
        "estimated_cost_usd",
        "skipped",
        "ended_early_reason",
        "export_json",
        "created_at",
    },
    "documents": {
        "id",
        "run_id",
        "source_path",
        "extracted_text",
        "content_hash",
        "extraction",
        "created_at",
    },
    "register_rows": {
        "id",
        "project_id",
        "what_was_asked",
        "in_writing",
        "what_testing_found",
        "status",
        "blocked_on",
        "first_seen",
        "last_moved",
        "fingerprint",
        "row_number",
        "proposed_by_run_id",
        "is_committed",
        "created_at",
    },
    "citations": {
        "id",
        "register_row_id",
        "cell_name",
        "source_file",
        "source_place",
        "source_words",
        "absence_statement",
        "created_at",
    },
    "decisions": {
        "id",
        "run_id",
        "kind",
        "question",
        "proposed_register_row_id",
        "candidate_register_row_id",
        "outcome",
        "decided_at",
    },
    "audit": {
        "id",
        "register_row_id",
        "cell_name",
        "old_value",
        "new_value",
        "run_id",
        "source_document_id",
        "created_at",
    },
}
RUN_STATUSES = (
    "waiting",
    "running",
    "waiting for review",
    "done",
    "closed without export",
)
REGISTER_ROW_STATUSES = (
    "Done",
    "Partial",
    "Never happened",
    "Blocked",
    "Disputed",
    "No evidence yet",
)


@pytest.fixture(scope="session")
def database_engine() -> Iterator[Engine]:
    application_database_url = make_url(
        os.environ.get(
            DATABASE_URL_ENVIRONMENT_VARIABLE,
            DEFAULT_DATABASE_URL,
        )
    )
    test_database_name = f"{TEST_DATABASE_PREFIX}{uuid4().hex}"
    test_database_url = application_database_url.set(database=test_database_name)
    maintenance_database_url = application_database_url.set(
        database=POSTGRES_MAINTENANCE_DATABASE
    )
    maintenance_engine = create_engine(
        maintenance_database_url,
        isolation_level="AUTOCOMMIT",
    )
    test_database_created = False
    engine: Engine | None = None

    try:
        with maintenance_engine.connect() as connection:
            connection.exec_driver_sql(f'CREATE DATABASE "{test_database_name}"')
        test_database_created = True

        alembic_config = Config(PROJECT_ROOT / "alembic.ini")
        alembic_config.set_main_option(
            "sqlalchemy.url",
            test_database_url.render_as_string(hide_password=False),
        )
        command.upgrade(alembic_config, "head")

        engine = create_engine(test_database_url)
        yield engine
    finally:
        if engine is not None:
            engine.dispose()
        if test_database_created:
            with maintenance_engine.connect() as connection:
                connection.exec_driver_sql(
                    f'DROP DATABASE "{test_database_name}" WITH (FORCE)'
                )
        maintenance_engine.dispose()


@pytest.fixture
def database_connection(database_engine: Engine) -> Iterator[Connection]:
    with database_engine.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()


def _insert_project(connection: Connection, project_id: UUID | None = None) -> UUID:
    inserted_project_id = project_id or uuid4()
    connection.execute(
        text(
            "INSERT INTO projects (id, name, source_folder_path) "
            "VALUES (:id, :name, :source_folder_path)"
        ),
        {
            "id": inserted_project_id,
            "name": f"project-{inserted_project_id}",
            "source_folder_path": f"/projects/{inserted_project_id}",
        },
    )
    return inserted_project_id


def _insert_run(
    connection: Connection,
    project_id: UUID | None,
    status: str = "done",
) -> UUID:
    run_id = uuid4()
    connection.execute(
        text(
            "INSERT INTO runs (id, project_id, status) "
            "VALUES (:id, :project_id, :status)"
        ),
        {"id": run_id, "project_id": project_id, "status": status},
    )
    return run_id


def _insert_document(connection: Connection, run_id: UUID) -> UUID:
    document_id = uuid4()
    connection.execute(
        text(
            "INSERT INTO documents "
            "(id, run_id, source_path, extracted_text, content_hash) "
            "VALUES (:id, :run_id, :source_path, :extracted_text, :content_hash)"
        ),
        {
            "id": document_id,
            "run_id": run_id,
            "source_path": "meeting-notes.md",
            "extracted_text": "A fabricated meeting note.",
            "content_hash": "0" * 64,
        },
    )
    return document_id


def _insert_register_row(
    connection: Connection,
    project_id: UUID | None,
    run_id: UUID,
    status: str = "No evidence yet",
    row_number: int = 1,
) -> UUID:
    register_row_id = uuid4()
    connection.execute(
        text(
            """
            INSERT INTO register_rows (
                id,
                project_id,
                what_was_asked,
                in_writing,
                what_testing_found,
                status,
                blocked_on,
                first_seen,
                last_moved,
                fingerprint,
                row_number,
                proposed_by_run_id,
                is_committed
            ) VALUES (
                :id,
                :project_id,
                :what_was_asked,
                :in_writing,
                :what_testing_found,
                :status,
                :blocked_on,
                :first_seen,
                :last_moved,
                :fingerprint,
                :row_number,
                :proposed_by_run_id,
                :is_committed
            )
            """
        ),
        {
            "id": register_row_id,
            "project_id": project_id,
            "what_was_asked": "Send a notification on form submission.",
            "in_writing": "Yes",
            "what_testing_found": "No testing evidence yet.",
            "status": status,
            "blocked_on": "Not blocked",
            "first_seen": "10 March 2026",
            "last_moved": "10 March 2026",
            "fingerprint": f"fingerprint-{register_row_id}",
            "row_number": row_number,
            "proposed_by_run_id": run_id,
            "is_committed": False,
        },
    )
    return register_row_id


def test_schema_tests_do_not_use_the_application_database(
    database_engine: Engine,
) -> None:
    application_database_url: URL = make_url(
        os.environ.get(
            DATABASE_URL_ENVIRONMENT_VARIABLE,
            DEFAULT_DATABASE_URL,
        )
    )
    test_database_name = database_engine.url.database

    assert test_database_name is not None
    assert test_database_name.startswith(TEST_DATABASE_PREFIX)
    assert test_database_name != application_database_url.database


def test_all_seven_domain_tables_have_the_expected_columns(
    database_connection: Connection,
) -> None:
    inspector = inspect(database_connection)
    table_names = set(inspector.get_table_names(schema="public"))

    assert DOMAIN_TABLES.issubset(table_names)
    for table_name, expected_columns in EXPECTED_COLUMNS.items():
        actual_columns = {
            column["name"] for column in inspector.get_columns(table_name, schema="public")
        }
        assert actual_columns == expected_columns


@pytest.mark.parametrize("project_id", [None, uuid4()])
def test_register_row_requires_one_existing_project(
    database_connection: Connection,
    project_id: UUID | None,
) -> None:
    valid_project_id = _insert_project(database_connection)
    run_id = _insert_run(database_connection, valid_project_id)

    with pytest.raises(IntegrityError):
        with database_connection.begin_nested():
            _insert_register_row(database_connection, project_id, run_id)


@pytest.mark.parametrize("project_id", [None, uuid4()])
def test_run_requires_one_existing_project(
    database_connection: Connection,
    project_id: UUID | None,
) -> None:
    with pytest.raises(IntegrityError):
        with database_connection.begin_nested():
            _insert_run(database_connection, project_id)


@pytest.mark.parametrize(
    ("first_status", "second_status"),
    [
        ("running", "running"),
        ("waiting for review", "running"),
        ("running", "waiting for review"),
    ],
)
def test_project_refuses_a_second_active_run(
    database_connection: Connection,
    first_status: str,
    second_status: str,
) -> None:
    project_id = _insert_project(database_connection)
    _insert_run(database_connection, project_id, status=first_status)

    with pytest.raises(IntegrityError):
        with database_connection.begin_nested():
            _insert_run(database_connection, project_id, status=second_status)


def test_project_refuses_a_second_waiting_run(
    database_connection: Connection,
) -> None:
    project_id = _insert_project(database_connection)
    _insert_run(database_connection, project_id, status="waiting")

    with pytest.raises(IntegrityError):
        with database_connection.begin_nested():
            _insert_run(database_connection, project_id, status="waiting")


@pytest.mark.parametrize("run_id", [None, uuid4()])
def test_decision_requires_one_existing_run(
    database_connection: Connection,
    run_id: UUID | None,
) -> None:
    with pytest.raises(IntegrityError):
        with database_connection.begin_nested():
            database_connection.execute(
                text(
                    "INSERT INTO decisions (id, run_id, kind, question, outcome) "
                    "VALUES (:id, :run_id, :kind, :question, :outcome)"
                ),
                {
                    "id": uuid4(),
                    "run_id": run_id,
                    "kind": "export",
                    "question": "Export this register?",
                    "outcome": "approved",
                },
            )


@pytest.mark.parametrize("register_row_id", [None, uuid4()])
def test_citation_requires_one_existing_register_row(
    database_connection: Connection,
    register_row_id: UUID | None,
) -> None:
    with pytest.raises(IntegrityError):
        with database_connection.begin_nested():
            database_connection.execute(
                text(
                    """
                    INSERT INTO citations (
                        id,
                        register_row_id,
                        cell_name,
                        source_file,
                        source_place,
                        source_words
                    ) VALUES (
                        :id,
                        :register_row_id,
                        :cell_name,
                        :source_file,
                        :source_place,
                        :source_words
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "register_row_id": register_row_id,
                    "cell_name": "what_was_asked",
                    "source_file": "meeting-notes.md",
                    "source_place": "Discussion",
                    "source_words": "Send a notification on submission.",
                },
            )


@pytest.mark.parametrize("audit_run_id", [None, uuid4()])
def test_audit_change_requires_one_existing_run(
    database_connection: Connection,
    audit_run_id: UUID | None,
) -> None:
    project_id = _insert_project(database_connection)
    valid_run_id = _insert_run(database_connection, project_id)
    document_id = _insert_document(database_connection, valid_run_id)
    register_row_id = _insert_register_row(
        database_connection,
        project_id,
        valid_run_id,
    )

    with pytest.raises(IntegrityError):
        with database_connection.begin_nested():
            database_connection.execute(
                text(
                    """
                    INSERT INTO audit (
                        id,
                        register_row_id,
                        cell_name,
                        old_value,
                        new_value,
                        run_id,
                        source_document_id
                    ) VALUES (
                        :id,
                        :register_row_id,
                        :cell_name,
                        :old_value,
                        :new_value,
                        :run_id,
                        :source_document_id
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "register_row_id": register_row_id,
                    "cell_name": "status",
                    "old_value": "No evidence yet",
                    "new_value": "Done",
                    "run_id": audit_run_id,
                    "source_document_id": document_id,
                },
            )


def test_run_refuses_status_outside_the_locked_set(
    database_connection: Connection,
) -> None:
    for status in RUN_STATUSES:
        project_id = _insert_project(database_connection)
        _insert_run(database_connection, project_id, status=status)

    invalid_project_id = _insert_project(database_connection)
    with pytest.raises(IntegrityError):
        with database_connection.begin_nested():
            _insert_run(database_connection, invalid_project_id, status="finished")


def test_register_row_refuses_status_outside_the_locked_set(
    database_connection: Connection,
) -> None:
    for status in REGISTER_ROW_STATUSES:
        project_id = _insert_project(database_connection)
        run_id = _insert_run(database_connection, project_id)
        _insert_register_row(database_connection, project_id, run_id, status=status)

    invalid_project_id = _insert_project(database_connection)
    invalid_run_id = _insert_run(database_connection, invalid_project_id)
    with pytest.raises(IntegrityError):
        with database_connection.begin_nested():
            _insert_register_row(
                database_connection,
                invalid_project_id,
                invalid_run_id,
                status="Delivered",
            )


def test_new_run_cost_defaults_to_zero(database_connection: Connection) -> None:
    project_id = _insert_project(database_connection)
    run_id = _insert_run(database_connection, project_id)

    estimated_cost = database_connection.execute(
        text("SELECT estimated_cost_usd FROM runs WHERE id = :id"),
        {"id": run_id},
    ).scalar_one()

    assert estimated_cost == Decimal("0")
