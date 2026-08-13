from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import AsyncConnection

from app.examine.read_findings import (
    approved_findings_of_project,
    examine_as_exported,
    exported_finding,
)
from app.register.cells import CELL_NAMES


JSON_FORMAT = "json"
MARKDOWN_FORMAT = "markdown"
EXPORT_FORMATS = (JSON_FORMAT, MARKDOWN_FORMAT)
COLUMN_HEADINGS = {
    "what_was_asked": "What was asked",
    "in_writing": "In writing?",
    "what_testing_found": "What testing found",
    "status": "Status",
    "blocked_on": "Blocked on",
    "first_seen": "First seen",
    "last_moved": "Last moved",
}


async def build_export(
    connection: AsyncConnection,
    project: dict[str, Any],
    run_id: UUID,
    exported_at: str,
) -> dict[str, Any]:
    """The approved register as JSON — the record every other surface reads."""
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
    # the examine block below is what this one run judged and found.
    findings_by_row: dict[UUID, list[dict[str, Any]]] = {}
    for finding in await approved_findings_of_project(connection, project["id"]):
        findings_by_row.setdefault(finding["register_row_id"], []).append(
            exported_finding(finding)
        )

    return {
        "project": {"id": str(project["id"]), "name": project["name"]},
        "run_id": str(run_id),
        "exported_at": exported_at,
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
        "examine": await examine_as_exported(connection, run_id),
    }


def export_as_markdown(export: dict[str, Any]) -> str:
    """Generated from the JSON record, never edited or stored separately."""
    headings = [COLUMN_HEADINGS[name] for name in export["columns"]]
    lines = [
        f"# Requirements-to-Delivery Register — {export['project']['name']}",
        "",
        f"Exported from run {export['run_id']} at {export['exported_at']}.",
        "",
        "| # | " + " | ".join(headings) + " |",
        "|---|" + "|".join(["---"] * len(headings)) + "|",
    ]
    for row in export["rows"]:
        cells = [_single_line(row["cells"][name]) for name in export["columns"]]
        lines.append(f"| {row['row_number']} | " + " | ".join(cells) + " |")

    lines += ["", "## Citations", ""]
    for row in export["rows"]:
        lines.append(f"**Row {row['row_number']}** — {row['cells']['what_was_asked']}")
        for citation in row["citations"]:
            lines.append(_citation_line(citation))
        lines.append("")

    return "\n".join(lines + _findings_lines(export["examine"]))


def _rule_settings(rule: dict[str, Any]) -> str:
    """R3 reads "beyond max_days", so the limit belongs beside its text here."""
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
