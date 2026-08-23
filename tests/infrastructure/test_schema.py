from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine, inspect, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import IntegrityError

from tests.runs.application import PROJECT_ROOT, temporary_database


BEFORE_THIS_SLICE = "20260813_0004"
WITH_WITHDRAWAL = "20260814_0010"
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
    "findings",
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
        "finished_stages",
        "skipped",
        "ended_early_reason",
        "failure_reason",
        "pending_moves",
        "reported_instructions",
        "review_finished_at",
        "rules_snapshot",
        "rules_applied",
        "rules_fingerprint",
        "examined_row_count",
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
        "fingerprint",
        "row_number",
        "proposed_by_run_id",
        "merged_into_register_row_id",
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
        "parts",
        "proposed_register_row_id",
        "candidate_register_row_id",
        "outcome",
        "decided_at",
    },
    "audit": {
        "id",
        "register_row_id",
        "cell_name",
        "event_kind",
        "old_value",
        "new_value",
        "run_id",
        "source_document_id",
        "created_at",
    },
    "findings": {
        "id",
        "run_id",
        "register_row_id",
        "rule_id",
        "rule_text",
        "issue",
        "evidence",
        "question",
        "decision_key",
        "created_at",
    },
}
RUN_STATUSES = (
    "queued",
    "running",
    "needs review",
    "done",
    "discarded",
    "failed",
    "no changes",
)
REGISTER_ROW_STATUSES = (
    "Done",
    "Partial",
    "Not delivered",
    "Handed over",
    "Disputed",
    "Requested",
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


# The three cells 20260817_0017 dropped. A test that first downgrades past
# that migration writes them too, because the older shape holds them NOT NULL.
CELLS_DROPPED_BY_THE_NARROWING = {
    "blocked_on": "Not blocked",
    "first_seen": "10 March 2026",
    "last_moved": "10 March 2026",
}


def _insert_register_row(
    connection: Connection,
    project_id: UUID | None,
    run_id: UUID,
    status: str = "Requested",
    row_number: int = 1,
    on_the_seven_cell_shape: bool = False,
) -> UUID:
    register_row_id = uuid4()
    values = {
        "id": register_row_id,
        "project_id": project_id,
        "what_was_asked": "Send a notification on form submission.",
        "in_writing": "Yes",
        "what_testing_found": "No testing evidence yet.",
        "status": status,
        "fingerprint": f"fingerprint-{register_row_id}",
        "row_number": row_number,
        "proposed_by_run_id": run_id,
        "is_committed": False,
    }
    if on_the_seven_cell_shape:
        values |= CELLS_DROPPED_BY_THE_NARROWING
    columns = ", ".join(values)
    placeholders = ", ".join(f":{name}" for name in values)
    connection.execute(
        text(f"INSERT INTO register_rows ({columns}) VALUES ({placeholders})"),
        values,
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
        ("needs review", "running"),
        ("running", "needs review"),
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
    _insert_run(database_connection, project_id, status="queued")

    with pytest.raises(IntegrityError):
        with database_connection.begin_nested():
            _insert_run(database_connection, project_id, status="queued")


def test_run_refuses_a_second_row_for_the_same_document(
    database_connection: Connection,
) -> None:
    project_id = _insert_project(database_connection)
    run_id = _insert_run(database_connection, project_id)
    _insert_document(database_connection, run_id)

    with pytest.raises(IntegrityError):
        with database_connection.begin_nested():
            _insert_document(database_connection, run_id)


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
                    "old_value": "Requested",
                    "new_value": "Done",
                    "run_id": audit_run_id,
                    "source_document_id": document_id,
                },
            )


def _insert_audit_event(
    connection: Connection,
    register_row_id: UUID,
    run_id: UUID,
    event_kind: str,
    cell_name: str | None,
) -> None:
    connection.execute(
        text(
            "INSERT INTO audit (id, register_row_id, cell_name, event_kind, "
            "old_value, new_value, run_id, source_document_id) "
            "VALUES (:id, :register_row_id, :cell_name, :event_kind, "
            ":old_value, :new_value, :run_id, NULL)"
        ),
        {
            "id": uuid4(),
            "register_row_id": register_row_id,
            "cell_name": cell_name,
            "event_kind": event_kind,
            "old_value": None,
            "new_value": "R1 — the requirement is not written down anywhere.",
            "run_id": run_id,
        },
    )


def test_attachment_audit_event_refuses_to_name_a_changed_cell(
    database_connection: Connection,
) -> None:
    project_id = _insert_project(database_connection)
    run_id = _insert_run(database_connection, project_id)
    register_row_id = _insert_register_row(database_connection, project_id, run_id)

    _insert_audit_event(
        database_connection, register_row_id, run_id, "attachment", None
    )

    # A finding attaches to a row, so there is no honest cell name to write.
    with pytest.raises(IntegrityError):
        with database_connection.begin_nested():
            _insert_audit_event(
                database_connection, register_row_id, run_id, "attachment", "status"
            )


def test_cell_change_audit_event_still_names_a_register_cell(
    database_connection: Connection,
) -> None:
    """The audit check keeps the names of the cells 20260817_0017 dropped.

    An audit entry is history: a row whose `Blocked on` changed before that
    migration ran still names that cell, and narrowing the check would either
    refuse the entry or force it to be deleted.
    """
    project_id = _insert_project(database_connection)
    run_id = _insert_run(database_connection, project_id)
    register_row_id = _insert_register_row(database_connection, project_id, run_id)

    _insert_audit_event(
        database_connection, register_row_id, run_id, "cell change", "status"
    )

    for refused_cell_name in (None, "findings"):
        with pytest.raises(IntegrityError):
            with database_connection.begin_nested():
                _insert_audit_event(
                    database_connection,
                    register_row_id,
                    run_id,
                    "cell change",
                    refused_cell_name,
                )


def test_this_slice_downgrades_and_upgrades_again_with_attachments_written(
) -> None:
    with temporary_database() as database_url:
        alembic_config = Config(PROJECT_ROOT / "alembic.ini")
        alembic_config.set_main_option("sqlalchemy.url", database_url)
        engine = create_engine(database_url)
        try:
            with engine.begin() as connection:
                project_id = _insert_project(connection)
                run_id = _insert_run(connection, project_id)
                register_row_id = _insert_register_row(
                    connection, project_id, run_id
                )
                _insert_audit_event(
                    connection, register_row_id, run_id, "attachment", None
                )
                _insert_audit_event(
                    connection, register_row_id, run_id, "cell change", "status"
                )

            command.downgrade(alembic_config, BEFORE_THIS_SLICE)
            with engine.connect() as connection:
                kept_after_downgrade = connection.execute(
                    text("SELECT cell_name FROM audit")
                ).scalars().all()

            command.upgrade(alembic_config, "head")
            with engine.connect() as connection:
                kept_after_upgrade = connection.execute(
                    text("SELECT cell_name, event_kind FROM audit")
                ).mappings().all()
        finally:
            engine.dispose()

    # The older shape cannot say "this event named no cell", so the downgrade
    # drops the attachment events rather than leaving them claiming a cell.
    assert kept_after_downgrade == ["status"]
    assert [dict(row) for row in kept_after_upgrade] == [
        {"cell_name": "status", "event_kind": "cell change"}
    ]


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


def test_register_row_takes_requested_and_refuses_the_name_it_replaced(
    database_connection: Connection,
) -> None:
    """20260823_0022 renamed the value, so the old spelling is now outside the set.

    A database left holding `Nothing said yet` would show a status the register
    no longer defines, which is why the rename rewrites the stored rows rather
    than only widening the check.
    """
    accepting_project_id = _insert_project(database_connection)
    accepting_run_id = _insert_run(database_connection, accepting_project_id)
    _insert_register_row(
        database_connection,
        accepting_project_id,
        accepting_run_id,
        status="Requested",
    )

    refusing_project_id = _insert_project(database_connection)
    refusing_run_id = _insert_run(database_connection, refusing_project_id)
    with pytest.raises(IntegrityError):
        with database_connection.begin_nested():
            _insert_register_row(
                database_connection,
                refusing_project_id,
                refusing_run_id,
                status="Nothing said yet",
            )


def test_the_upgrade_removing_withdrawal_refuses_while_a_withdrawn_row_exists(
) -> None:
    """20260814_0011 narrows the status check; a `Withdrawn` row must block it.

    `Withdrawn` can no longer be inserted once 20260814_0011 has run (it is
    outside `test_register_row_refuses_status_outside_the_locked_set`'s locked
    set on purpose), so this drives the migration itself: land on the last
    revision that still allows the status, write a row that holds it, then
    upgrade to head and watch the migration refuse.
    """
    with temporary_database() as database_url:
        alembic_config = Config(PROJECT_ROOT / "alembic.ini")
        alembic_config.set_main_option("sqlalchemy.url", database_url)
        engine = create_engine(database_url)
        try:
            command.downgrade(alembic_config, WITH_WITHDRAWAL)
            with engine.begin() as connection:
                project_id = _insert_project(connection)
                run_id = _insert_run(connection, project_id)
                _insert_register_row(
                    connection,
                    project_id,
                    run_id,
                    status="Withdrawn",
                    on_the_seven_cell_shape=True,
                )

            with pytest.raises(RuntimeError) as refused:
                command.upgrade(alembic_config, "head")

            with engine.connect() as connection:
                still_there = connection.execute(
                    text("SELECT status FROM register_rows")
                ).scalars().all()
        finally:
            engine.dispose()

    # The new schema has no status that means withdrawn, and the row is never
    # deleted, so the migration says what is in the way and what to do about it.
    assert "1 register row(s) are 'Withdrawn'" in str(refused.value)
    assert "change its status, then run this migration again" in str(refused.value)
    assert still_there == ["Withdrawn"]
