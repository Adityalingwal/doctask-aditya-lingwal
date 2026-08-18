from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import AsyncConnection

from app.register.audit_entries import ATTACHMENT_EVENT
from app.register.cells import WHAT_WAS_ASKED
from app.runs.run_records import require_project


CELL_CHANGE_ENTRY = "cell change"
ROW_CREATED_ENTRY = "row created"
FINDING_ATTACHED_ENTRY = "finding attached"

# Newest first, and within one moment by row and then by cell: a run commits
# in one transaction, so all of its entries carry that transaction's timestamp
# and nothing but these two further keys can order them. A cell name is null
# on an attachment, which is why it sorts last rather than first — and why
# two attachments on one row in one run tie on all three keys, so the entry
# id settles them; without it two reads could answer in two orders.
#
# A run's number is not stored anywhere. It is counted here exactly as
# `app/projects/list_projects.py` counts it, so the history and the projects
# list can never number one run differently.
HISTORY_QUERY = (
    "SELECT audit.register_row_id, audit.run_id, audit.cell_name, "
    "audit.event_kind, audit.old_value, audit.new_value, audit.created_at, "
    "register_rows.row_number, documents.source_path AS source_file, "
    "numbered_runs.run_number "
    "FROM audit "
    "JOIN register_rows ON register_rows.id = audit.register_row_id "
    "JOIN (SELECT runs.id, ROW_NUMBER() OVER (PARTITION BY runs.project_id "
    "ORDER BY runs.created_at ASC) AS run_number FROM runs) AS numbered_runs "
    "ON numbered_runs.id = audit.run_id "
    "LEFT JOIN documents ON documents.id = audit.source_document_id "
    "WHERE register_rows.project_id = %s "
    "ORDER BY audit.created_at DESC, register_rows.row_number ASC, "
    "audit.cell_name ASC NULLS LAST, audit.id ASC"
)


async def read_history(
    connection: AsyncConnection,
    project_id: UUID,
) -> dict[str, Any]:
    """What changed in one project's register, when, and from which document.

    Read-only over the `audit` table. It is not part of the register document:
    the register read answers what the register holds now, and this answers how
    it came to hold it. A project whose trail is empty answers no entries,
    which is an answer and not a refusal.
    """
    project = await require_project(connection, project_id)
    # The one-snapshot read `build_register_document` takes
    # (app/register/export_register.py): the pool runs autocommit, so the
    # isolation level belongs to the read rather than to the connection.
    async with connection.transaction():
        await connection.execute(
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"
        )
        result = await connection.execute(HISTORY_QUERY, (project["id"],))
        recorded = list(await result.fetchall())
    return {"entries": _entries(recorded)}


def _entries(recorded: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One entry per thing a reader sees, in the order the query already fixed.

    The fold happens here rather than on any surface, so the screen, curl and
    the MCP tool are answered with the same list rather than three readings of
    one table.
    """
    births = _row_births(recorded)
    folded: set[tuple[Any, Any]] = set()
    entries: list[dict[str, Any]] = []
    for change in recorded:
        if change["event_kind"] == ATTACHMENT_EVENT:
            entries.append(_finding_attached(change))
            continue
        born = births.get(_row_and_run(change))
        if born is None:
            entries.append(_cell_change(change))
            continue
        if _row_and_run(change) in folded:
            continue
        folded.add(_row_and_run(change))
        entries.append(_row_created(born))
    return entries


def _row_births(
    recorded: list[dict[str, Any]],
) -> dict[tuple[Any, Any], dict[str, Any]]:
    """Each row's own `what was asked` write, for the run that first wrote it.

    Committing a row writes one cell-change entry per cell, each with no old
    value, in a single transaction. Nothing else writes a cell with no old
    value, so a run and row whose cell changes are all of that shape is the
    row being born — four writes a reader is shown once.
    """
    changes_of: dict[tuple[Any, Any], list[dict[str, Any]]] = {}
    for change in recorded:
        if change["event_kind"] == ATTACHMENT_EVENT:
            continue
        changes_of.setdefault(_row_and_run(change), []).append(change)

    births: dict[tuple[Any, Any], dict[str, Any]] = {}
    for row_and_run, changes in changes_of.items():
        if any(change["old_value"] is not None for change in changes):
            continue
        what_was_asked = next(
            (
                change
                for change in changes
                if change["cell_name"] == WHAT_WAS_ASKED
            ),
            None,
        )
        if what_was_asked is not None:
            births[row_and_run] = what_was_asked
    return births


def _cell_change(change: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": CELL_CHANGE_ENTRY,
        "row_number": change["row_number"],
        "cell": change["cell_name"],
        "old_value": change["old_value"],
        "new_value": change["new_value"],
        "changed_at": change["created_at"].isoformat(),
        "run_number": change["run_number"],
        "source_file": change["source_file"],
    }


def _row_created(what_was_asked: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": ROW_CREATED_ENTRY,
        "row_number": what_was_asked["row_number"],
        "what_was_asked": what_was_asked["new_value"],
        "changed_at": what_was_asked["created_at"].isoformat(),
        "run_number": what_was_asked["run_number"],
        "source_file": what_was_asked["source_file"],
    }


def _finding_attached(change: dict[str, Any]) -> dict[str, Any]:
    # An attachment moved no cell and came from no document, so it names
    # neither rather than carrying a null a reader has to interpret.
    return {
        "kind": FINDING_ATTACHED_ENTRY,
        "row_number": change["row_number"],
        "detail": change["new_value"],
        "changed_at": change["created_at"].isoformat(),
        "run_number": change["run_number"],
    }


def _row_and_run(change: dict[str, Any]) -> tuple[Any, Any]:
    return (change["run_id"], change["register_row_id"])
