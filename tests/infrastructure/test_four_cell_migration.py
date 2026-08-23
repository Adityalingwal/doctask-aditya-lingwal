from __future__ import annotations

import hashlib
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text

from app.register.cells import CELL_NAMES, fingerprint_of_cells
from tests.runs.application import migrate, temporary_database


BEFORE_THE_NARROWING = "20260816_0016"
DROPPED_CELLS = ("blocked_on", "first_seen", "last_moved")
# The shape the row had before this migration, spelled out here rather than
# imported: the constants that named it are deleted, and a test of a schema
# change has to state the schema it changed from.
SEVEN_CELLS = (
    "what_was_asked",
    "in_writing",
    "what_testing_found",
    "status",
    "blocked_on",
    "first_seen",
    "last_moved",
)
STATUSES_BEFORE = (
    "No evidence yet",
    "Done",
    "Partial",
    "Not delivered",
    "Disputed",
    "Blocked",
)
STATUSES_THE_NARROWER_CONSTRAINT_HOLDS = tuple(
    status for status in STATUSES_BEFORE if status != "Blocked"
)


def test_a_row_that_was_blocked_stops_the_migration_instead_of_being_rewritten() -> None:
    """A `Blocked` row has no honest status to become, so narrowing must stop.

    Rewriting it would make the register claim something no document said, and
    deleting it would destroy the history the register exists to keep.
    """
    with temporary_database(upgrade_to=BEFORE_THE_NARROWING) as database_url:
        _seed_a_row_per_status(database_url)

        with pytest.raises(RuntimeError) as refused:
            migrate(database_url, "head")

        message = str(refused.value)
        assert "Blocked" in message
        # Named, not merely counted: a person must be able to act on the
        # message without writing a query of their own first.
        assert "#6" in message
        assert "run this migration again" in message

        # The whole step rolled back: the row still says what it said, the
        # three columns are still there, and their citations are untouched.
        assert _statuses(database_url) == list(STATUSES_BEFORE)
        assert _columns_of_register_rows(database_url) >= set(DROPPED_CELLS)
        assert _cited_cells(database_url) == set(SEVEN_CELLS)


def test_the_migration_leaves_every_stored_fingerprint_exactly_as_it_was() -> None:
    """Narrowing the cell list changes what the hash would be, not what is stored.

    So a row stored before the migration ends up holding a seven-cell hash while
    its four cells would now hash to something else. That is deliberate, not
    corruption: the migration must leave the stored value alone rather than
    compute one, because a migration that computes a hash has to carry the
    application's rules.
    """
    with temporary_database(upgrade_to=BEFORE_THE_NARROWING) as database_url:
        _seed_a_row_per_status(database_url, include_blocked=False)
        before = _fingerprints(database_url)

        migrate(database_url, "head")

        after = _fingerprints(database_url)
        assert after == before

        for row_number, cells in _four_cells_of_every_row(database_url).items():
            assert fingerprint_of_cells(cells) != after[row_number]

        assert _columns_of_register_rows(database_url).isdisjoint(DROPPED_CELLS)
        assert _cited_cells(database_url) == {
            "what_was_asked",
            "in_writing",
            "what_testing_found",
            "status",
        }


def _seed_a_row_per_status(
    database_url: str,
    include_blocked: bool = True,
) -> None:
    """One committed row per status, each citing all seven of its cells."""
    statuses = (
        STATUSES_BEFORE if include_blocked else STATUSES_THE_NARROWER_CONSTRAINT_HOLDS
    )
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
                    "name": "Narrowed intake portal",
                    "folder": "sample-projects/narrowed-portal",
                },
            )
            connection.execute(
                text(
                    "INSERT INTO runs (id, project_id, status) "
                    "VALUES (:id, :project_id, 'running')"
                ),
                {"id": run_id, "project_id": project_id},
            )
            for row_number, status in enumerate(statuses, start=1):
                _insert_seven_cell_row(
                    connection, project_id, run_id, row_number, status
                )
    finally:
        engine.dispose()


def _insert_seven_cell_row(
    connection: Any,
    project_id: UUID,
    run_id: UUID,
    row_number: int,
    status: str,
) -> None:
    row_id = uuid4()
    cells = {
        "what_was_asked": f"Requirement {row_number}.",
        "in_writing": "Yes",
        "what_testing_found": "Not known yet.",
        "status": status,
        "blocked_on": "Waiting on the client's WhatsApp credentials.",
        "first_seen": "10 March 2026",
        "last_moved": "25 March 2026",
    }
    connection.execute(
        text(
            "INSERT INTO register_rows (id, project_id, "
            + ", ".join(SEVEN_CELLS)
            + ", fingerprint, row_number, proposed_by_run_id, is_committed) VALUES "
            "(:id, :project_id, "
            + ", ".join(f":{name}" for name in SEVEN_CELLS)
            + ", :fingerprint, :row_number, :run_id, true)"
        ),
        {
            "id": row_id,
            "project_id": project_id,
            **cells,
            "fingerprint": _seven_cell_fingerprint(cells),
            "row_number": row_number,
            "run_id": run_id,
        },
    )
    for cell_name in SEVEN_CELLS:
        connection.execute(
            text(
                "INSERT INTO citations (id, register_row_id, cell_name, "
                "source_file, source_place, source_words) VALUES "
                "(:id, :row_id, :cell_name, 'meeting-notes-10-mar.md', "
                "'Discussion', 'the client asked for it')"
            ),
            {"id": uuid4(), "row_id": row_id, "cell_name": cell_name},
        )


def _seven_cell_fingerprint(cells: dict[str, str]) -> str:
    joined = "\n".join(f"{name}={cells[name]}" for name in SEVEN_CELLS)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _statuses(database_url: str) -> list[str]:
    return _scalars(
        database_url, "SELECT status FROM register_rows ORDER BY row_number"
    )


def _fingerprints(database_url: str) -> dict[int, str]:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return {
                row.row_number: row.fingerprint
                for row in connection.execute(
                    text("SELECT row_number, fingerprint FROM register_rows")
                )
            }
    finally:
        engine.dispose()


def _four_cells_of_every_row(database_url: str) -> dict[int, dict[str, str]]:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return {
                row["row_number"]: {name: row[name] for name in CELL_NAMES}
                for row in connection.execute(
                    text(
                        "SELECT row_number, "
                        + ", ".join(CELL_NAMES)
                        + " FROM register_rows"
                    )
                ).mappings()
            }
    finally:
        engine.dispose()


def _columns_of_register_rows(database_url: str) -> set[str]:
    return set(
        _scalars(
            database_url,
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'register_rows'",
        )
    )


def _cited_cells(database_url: str) -> set[str]:
    return set(_scalars(database_url, "SELECT DISTINCT cell_name FROM citations"))


def _scalars(database_url: str, query: str) -> list[Any]:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return list(connection.execute(text(query)).scalars().all())
    finally:
        engine.dispose()
