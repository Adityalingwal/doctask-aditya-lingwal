from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import AsyncConnection

from app.examine.read_findings import (
    approved_findings_of_project,
    examine_as_exported,
    exported_finding,
)
from app.register.cells import CELL_NAMES, COLUMN_HEADINGS
from app.runs.statuses import DONE


JSON_FORMAT = "json"
MARKDOWN_FORMAT = "markdown"
REGISTER_FORMATS = (JSON_FORMAT, MARKDOWN_FORMAT)

# The one sentence a register no run has committed to answers with — the same
# words the screen shows, never an error and never an empty table.
EMPTY_REGISTER_LINE = "Nothing has been added to this register yet."


async def build_register_document(
    connection: AsyncConnection,
    project: dict[str, Any],
) -> dict[str, Any]:
    """The project's committed register as JSON — the record every surface reads.

    Read live from `register_rows` on every call: what used to be computed at
    commit time and copied into a snapshot is computed at read time, so the
    register has one truth. `exported_at` and `examine` come from the newest
    `done` run — `finished_at` is written in the same transaction that commits
    the rows, so it is exactly the moment the register last gained rows — and
    both are null while no run has committed anything.
    """
    newest_done = await _newest_done_run(connection, project["id"])
    rows_result = await connection.execute(
        "SELECT id, row_number, fingerprint, "
        + ", ".join(CELL_NAMES)
        + " FROM register_rows WHERE project_id = %s AND is_committed "
        "ORDER BY row_number",
        (project["id"],),
    )
    rows = list(await rows_result.fetchall())

    citations_result = await connection.execute(
        "SELECT citations.register_row_id, citations.cell_name, "
        "citations.source_file, citations.source_place, citations.source_words, "
        "citations.absence_statement FROM citations "
        "JOIN register_rows ON register_rows.id = citations.register_row_id "
        "WHERE register_rows.project_id = %s AND register_rows.is_committed "
        "ORDER BY register_rows.row_number, citations.cell_name",
        (project["id"],),
    )
    citations_by_row: dict[UUID, list[dict[str, Any]]] = {}
    for citation in await citations_result.fetchall():
        citations_by_row.setdefault(citation["register_row_id"], []).append(
            {
                "cell": citation["cell_name"],
                "source_file": citation["source_file"],
                "place": citation["source_place"],
                "source_words": citation["source_words"],
                "absence_statement": citation["absence_statement"],
            }
        )

    # A row carries every finding approved onto it, whichever run raised it;
    # the examine block below is what the newest committed run judged and found.
    findings_by_row: dict[UUID, list[dict[str, Any]]] = {}
    for finding in await approved_findings_of_project(connection, project["id"]):
        findings_by_row.setdefault(finding["register_row_id"], []).append(
            exported_finding(finding)
        )

    return {
        "project": {"id": str(project["id"]), "name": project["name"]},
        "exported_at": (
            newest_done["finished_at"].isoformat()
            if newest_done is not None
            else None
        ),
        "columns": list(CELL_NAMES),
        "rows": [
            {
                "row_number": row["row_number"],
                "fingerprint": row["fingerprint"],
                "cells": {name: row[name] for name in CELL_NAMES},
                "citations": citations_by_row.get(row["id"], []),
                "findings": findings_by_row.get(row["id"], []),
            }
            for row in rows
        ],
        "examine": (
            await examine_as_exported(connection, newest_done["id"])
            if newest_done is not None
            else None
        ),
    }


async def _newest_done_run(
    connection: AsyncConnection,
    project_id: UUID,
) -> dict[str, Any] | None:
    result = await connection.execute(
        "SELECT id, finished_at FROM runs "
        "WHERE project_id = %s AND status = %s "
        "ORDER BY finished_at DESC LIMIT 1",
        (project_id, DONE),
    )
    return await result.fetchone()


def register_as_markdown(register: dict[str, Any]) -> str:
    """Generated from the JSON record, never edited or stored separately."""
    lines = [
        f"# Requirements-to-Delivery Register — {register['project']['name']}",
        "",
    ]
    if register["exported_at"] is not None:
        lines += [f"Last updated {register['exported_at']}.", ""]

    if register["rows"]:
        headings = [COLUMN_HEADINGS[name] for name in register["columns"]]
        lines += [
            "| # | " + " | ".join(headings) + " |",
            "|---|" + "|".join(["---"] * len(headings)) + "|",
        ]
        for row in register["rows"]:
            cells = [
                _single_line(row["cells"][name]) for name in register["columns"]
            ]
            lines.append(f"| {row['row_number']} | " + " | ".join(cells) + " |")

        lines += ["", "## Citations", ""]
        for row in register["rows"]:
            lines.append(
                f"**Row {row['row_number']}** — {row['cells']['what_was_asked']}"
            )
            for citation in row["citations"]:
                lines.append(_citation_line(citation))
            lines.append("")
    else:
        lines += [EMPTY_REGISTER_LINE, ""]

    if register["examine"] is None:
        return "\n".join(lines)
    return "\n".join(lines + _findings_lines(register["examine"]))


def _rule_settings(rule: dict[str, Any]) -> str:
    """A rule whose text names a setting cannot be read without its value."""
    params = rule.get("params")
    if not params:
        return ""
    settings = ", ".join(f"{name}: {value}" for name, value in params.items())
    return f" ({settings})"


def _findings_lines(examine: dict[str, Any]) -> list[str]:
    lines = [
        "## Findings",
        "",
        f"Rules run against {examine['rows_examined']} register row(s):",
    ]
    for rule in examine["rules"]:
        lines.append(f"- `{rule['id']}` — {rule['text']}{_rule_settings(rule)}")
    lines.append("")
    if not examine["findings"]:
        # An empty result is stated, never left as a silent pass.
        lines.append("No findings — no register row broke one of those rules.")
        return lines
    for finding in examine["findings"]:
        lines.append(
            f"- **Row {finding['row_number']}** `{finding['rule_id']}` — "
            f"{_single_line(finding['issue'])} "
            f"({_single_line(finding['evidence'])})"
        )
    return lines


def _citation_line(citation: dict[str, Any]) -> str:
    if citation["source_words"] is None:
        return (
            f"- `{citation['cell']}` — {citation['source_file']}: "
            f"{citation['absence_statement']}"
        )
    words = " ".join(citation["source_words"].split())
    return (
        f"- `{citation['cell']}` — {citation['source_file']}, "
        f"{citation['place']}: \"{words}\""
    )


def _single_line(cell_value: str) -> str:
    return " ".join(cell_value.split()).replace("|", "\\|")
