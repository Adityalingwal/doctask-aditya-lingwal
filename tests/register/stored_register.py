from __future__ import annotations

from typing import Any, NamedTuple

from sqlalchemy import create_engine, text

from app.register.cells import CELL_NAMES


class StoredRow(NamedTuple):
    """One committed row exactly as PostgreSQL holds it, citations included.

    Comparing these across two runs is what proves a row was left alone: a row
    that merely looks the same on screen can still have been rewritten, and a
    fingerprint that moved says so even when every cell reads identically.
    """

    cells: tuple[str, ...]
    fingerprint: str
    citations: tuple[tuple[Any, ...], ...]


def stored_rows(database_url: str, project_id: str) -> dict[int, StoredRow]:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT id, row_number, fingerprint, "
                    + ", ".join(CELL_NAMES)
                    + " FROM register_rows WHERE project_id = :project_id "
                    "AND is_committed ORDER BY row_number"
                ),
                {"project_id": project_id},
            ).mappings().all()
            citations = connection.execute(
                text(
                    "SELECT register_row_id, cell_name, source_file, "
                    "source_place, source_words, absence_statement FROM citations "
                    "WHERE register_row_id = ANY(:row_ids) "
                    "ORDER BY cell_name, source_file, source_words"
                ),
                {"row_ids": [row["id"] for row in rows]},
            ).mappings().all()
    finally:
        engine.dispose()

    citations_by_row: dict[Any, list[tuple[Any, ...]]] = {}
    for citation in citations:
        citations_by_row.setdefault(citation["register_row_id"], []).append(
            (
                citation["cell_name"],
                citation["source_file"],
                citation["source_place"],
                citation["source_words"],
                citation["absence_statement"],
            )
        )

    return {
        row["row_number"]: StoredRow(
            cells=tuple(row[name] for name in CELL_NAMES),
            fingerprint=row["fingerprint"],
            citations=tuple(citations_by_row.get(row["id"], [])),
        )
        for row in rows
    }


def audit_of_row(
    database_url: str,
    project_id: str,
    row_number: int,
) -> list[tuple[Any, ...]]:
    """Every audit entry written against one row, oldest first."""
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return [
                tuple(entry)
                for entry in connection.execute(
                    text(
                        "SELECT audit.cell_name, audit.event_kind, "
                        "audit.old_value, audit.new_value FROM audit "
                        "JOIN register_rows ON register_rows.id = "
                        "audit.register_row_id WHERE register_rows.project_id = "
                        ":project_id AND register_rows.row_number = :row_number "
                        "ORDER BY audit.created_at, audit.cell_name"
                    ),
                    {"project_id": project_id, "row_number": row_number},
                ).all()
            ]
    finally:
        engine.dispose()


def runs_of_project(database_url: str, project_id: str) -> list[tuple[Any, ...]]:
    """Every run of one project as (id, status), oldest first."""
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return [
                (str(run["id"]), run["status"])
                for run in connection.execute(
                    text(
                        "SELECT id, status FROM runs WHERE project_id = "
                        ":project_id ORDER BY created_at"
                    ),
                    {"project_id": project_id},
                ).mappings().all()
            ]
    finally:
        engine.dispose()


def rules_applied_of_run(database_url: str, run_id: str) -> list[str]:
    """The rule ids Examine sent to the model on one run, as PostgreSQL holds them."""
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return connection.execute(
                text("SELECT rules_applied FROM runs WHERE id = :run_id"),
                {"run_id": run_id},
            ).scalar_one()
    finally:
        engine.dispose()


def findings_of_run(database_url: str, run_id: str) -> list[tuple[Any, ...]]:
    """Every finding one run raised, with the project and row each one names."""
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return [
                (
                    finding["rule_id"],
                    finding["issue"],
                    finding["question"],
                    str(finding["project_id"]),
                    finding["row_number"],
                )
                for finding in connection.execute(
                    text(
                        "SELECT findings.rule_id, findings.issue, "
                        "findings.question, register_rows.project_id, "
                        "register_rows.row_number FROM findings "
                        "JOIN register_rows ON register_rows.id = "
                        "findings.register_row_id WHERE findings.run_id = "
                        ":run_id ORDER BY findings.rule_id"
                    ),
                    {"run_id": run_id},
                ).mappings().all()
            ]
    finally:
        engine.dispose()


def extraction_of_document(
    database_url: str,
    run_id: str,
    source_path: str,
) -> dict[str, Any]:
    """What Extract stored for one document of one run, as PostgreSQL holds it."""
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return connection.execute(
                text(
                    "SELECT extraction FROM documents WHERE run_id = :run_id "
                    "AND source_path = :source_path"
                ),
                {"run_id": run_id, "source_path": source_path},
            ).scalar_one()
    finally:
        engine.dispose()


def documents_of_run(database_url: str, run_id: str) -> list[str]:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return [
                source_path
                for source_path in connection.execute(
                    text(
                        "SELECT source_path FROM documents WHERE run_id = :run_id "
                        "ORDER BY source_path"
                    ),
                    {"run_id": run_id},
                ).scalars().all()
            ]
    finally:
        engine.dispose()
