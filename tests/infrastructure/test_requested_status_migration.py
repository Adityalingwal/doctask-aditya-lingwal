from __future__ import annotations

from typing import Any
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.register.cells import STATUS_HANDED_OVER, STATUS_REQUESTED
from tests.runs.application import PROJECT_ROOT, temporary_database


BEFORE_THE_RENAME = "20260818_0021"
EARLIER_STATUS = "Nothing said yet"
CONSTRAINT_NAME = "ck_register_rows_status"
# Every file a reader or the running system takes the status word from. The
# migration files are excluded on purpose: an older one names the wording it
# renamed, and rewriting it would make it describe a rename it never made.
SEARCHED_PLACES = ("app", "ui/config", "README.md")
# Compiled caches sit beside the sources under `app/`, and a stale one holds
# whatever the source said when it was written rather than what it says now.
SEARCHED_SUFFIXES = frozenset({".py", ".json", ".md", ".yaml", ".yml"})


def test_the_status_requested_replaces_nothing_said_yet_everywhere() -> None:
    """The stored rows, the check constraint and every surface use one word.

    The 2026-08-17 rename left `ui/config/screen.json` naming a status the
    register had stopped writing, and the caution colour quietly stopped
    appearing. A rename is only finished when nothing still says the old word.
    """
    with temporary_database(upgrade_to=BEFORE_THE_RENAME) as database_url:
        alembic_config = Config(PROJECT_ROOT / "alembic.ini")
        alembic_config.set_main_option("sqlalchemy.url", database_url)
        _seed_a_row_per_status(database_url, EARLIER_STATUS)

        command.upgrade(alembic_config, "head")
        after_upgrade = _statuses(database_url)
        constraint_after_upgrade = _status_constraint(database_url)

        command.downgrade(alembic_config, BEFORE_THE_RENAME)
        after_downgrade = _statuses(database_url)
        constraint_after_downgrade = _status_constraint(database_url)

        command.upgrade(alembic_config, "head")
        after_second_upgrade = _statuses(database_url)

    assert after_upgrade == [STATUS_REQUESTED, STATUS_HANDED_OVER]
    assert STATUS_REQUESTED in constraint_after_upgrade
    assert EARLIER_STATUS not in constraint_after_upgrade
    # The downgrade puts back the value and the constraint together: a database
    # holding the new word under the old constraint could not be written to.
    assert after_downgrade == [EARLIER_STATUS, STATUS_HANDED_OVER]
    assert EARLIER_STATUS in constraint_after_downgrade
    assert STATUS_REQUESTED not in constraint_after_downgrade
    assert after_second_upgrade == [STATUS_REQUESTED, STATUS_HANDED_OVER]

    for place in SEARCHED_PLACES:
        assert _files_naming(EARLIER_STATUS, place) == []


def _files_naming(word: str, place: str) -> list[str]:
    searched = PROJECT_ROOT / place
    paths = [searched] if searched.is_file() else sorted(searched.rglob("*"))
    return [
        str(path.relative_to(PROJECT_ROOT))
        for path in paths
        if path.is_file()
        and path.suffix in SEARCHED_SUFFIXES
        and word in path.read_text(encoding="utf-8", errors="replace")
    ]


def _seed_a_row_per_status(database_url: str, starting_status: str) -> None:
    """Two committed rows: one the rename moves, one it must leave alone."""
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
                    "name": f"Requested {project_id}",
                    "folder": f"sample-projects/requested-{project_id}",
                },
            )
            connection.execute(
                text(
                    "INSERT INTO runs (id, project_id, status) "
                    "VALUES (:id, :project_id, 'done')"
                ),
                {"id": run_id, "project_id": project_id},
            )
            for row_number, status in enumerate(
                (starting_status, STATUS_HANDED_OVER), start=1
            ):
                connection.execute(
                    text(
                        "INSERT INTO register_rows (id, project_id, "
                        "what_was_asked, in_writing, what_testing_found, status, "
                        "fingerprint, row_number, proposed_by_run_id, is_committed) "
                        "VALUES (:id, :project_id, :asked, 'Yes', 'Not known yet', "
                        ":status, :fingerprint, :row_number, :run_id, true)"
                    ),
                    {
                        "id": uuid4(),
                        "project_id": project_id,
                        "asked": f"Requirement {row_number}.",
                        "status": status,
                        "fingerprint": f"fingerprint-{row_number}",
                        "row_number": row_number,
                        "run_id": run_id,
                    },
                )
    finally:
        engine.dispose()


def _statuses(database_url: str) -> list[str]:
    return _read(
        database_url,
        "SELECT status FROM register_rows ORDER BY row_number",
    )


def _status_constraint(database_url: str) -> str:
    return _read(
        database_url,
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        f"WHERE conname = '{CONSTRAINT_NAME}'",
    )[0]


def _read(database_url: str, query: str) -> list[Any]:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return list(connection.execute(text(query)).scalars().all())
    finally:
        engine.dispose()
