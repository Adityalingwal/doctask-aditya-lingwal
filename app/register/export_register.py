from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import AsyncConnection

from app.examine.read_findings import (
    approved_findings_of_project,
    examine_as_exported,
    finding_on_the_register,
    rules_that_ran,
)
from app.ingest.source_line import source_line
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
    # One REPEATABLE READ snapshot for every query below: the pool runs
    # autocommit, so without this a commit landing between two of the reads
    # could mix new rows with an older run's timestamp, citations or findings.
    async with connection.transaction():
        await connection.execute(
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"
        )
        return await _read_register_document(connection, project)


async def _read_register_document(
    connection: AsyncConnection,
    project: dict[str, Any],
) -> dict[str, Any]:
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
        "citations.absence_statement, citations.created_at FROM citations "
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
                "created_at": citation["created_at"],
            }
        )

    # A row carries what each rule found the last time that rule ran — which
    # may be nothing at all; the examine block below is what the newest
    # committed run judged and found.
    findings_by_row: dict[UUID, list[dict[str, Any]]] = {}
    for finding in await approved_findings_of_project(connection, project["id"]):
        findings_by_row.setdefault(finding["register_row_id"], []).append(
            finding_on_the_register(finding)
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
                # `citations` is the shape `ui/src/Register.jsx` still reads;
                # `evidence` is the shape every surface moves to. Both are
                # answered until the screen has moved.
                "citations": [
                    {name: value for name, value in citation.items()
                     if name != "created_at"}
                    for citation in citations_by_row.get(row["id"], [])
                ],
                "evidence": _evidence_of_row(citations_by_row.get(row["id"], [])),
                # Item 43: the field exists only when findings exist — a
                # machine caller never sees "0 findings" spelled as [].
                **(
                    {"findings": findings_by_row[row["id"]]}
                    if findings_by_row.get(row["id"])
                    else {}
                ),
            }
            for row in rows
        ],
        "rules": (
            await _rules_the_newest_run_applied(connection, newest_done)
            if newest_done is not None
            else None
        ),
        "examine": (
            await examine_as_exported(connection, newest_done["id"])
            if newest_done is not None
            else None
        ),
    }


def _evidence_of_row(citations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One entry per thing a document said, and the cells it supports.

    Two cells resting on one quote are one piece of evidence, not two — the
    old per-cell list showed the same sentence twice and left a reader
    counting. Grouped by the words themselves, so a document quoted twice on
    one row stays two entries. Ordered by when each group's evidence first
    arrived, then by column order (S22).
    """
    grouped: dict[tuple[str, str | None, str | None], dict[str, Any]] = {}
    for citation in citations:
        key = (
            citation["source_file"],
            citation["source_words"],
            citation["absence_statement"],
        )
        entry = grouped.get(key)
        if entry is None:
            entry = {
                # An absence has no place to name — the sentence names the
                # file and says the file was silent (S12's rule, here too).
                "source_line": (
                    source_line(citation["source_file"], citation["place"])
                    if citation["source_words"] is not None
                    else None
                ),
                "quote": citation["source_words"],
                "absence": citation["absence_statement"],
                "cells": [],
                "first_cited_at": citation["created_at"],
            }
            grouped[key] = entry
        entry["cells"].append(citation["cell"])
        entry["first_cited_at"] = min(
            entry["first_cited_at"], citation["created_at"]
        )

    ordered = sorted(
        grouped.values(),
        key=lambda entry: (
            entry["first_cited_at"],
            # The earliest register column the group supports — the cells
            # arrive alphabetically, so the first-seen one is not it.
            min(CELL_NAMES.index(cell) for cell in entry["cells"]),
        ),
    )
    return [
        {
            "source_line": entry["source_line"],
            "quote": entry["quote"],
            "absence": entry["absence"],
            "cells": [
                COLUMN_HEADINGS[cell]
                for cell in sorted(entry["cells"], key=CELL_NAMES.index)
            ],
        }
        for entry in ordered
    ]


async def _rules_the_newest_run_applied(
    connection: AsyncConnection,
    newest_done: dict[str, Any],
) -> dict[str, Any]:
    """Which rules last judged this register, how many rows, and on which run.

    Read from `rules_applied` rather than from the frozen snapshot, because a
    rule the run froze but never applied did not judge anything.
    """
    examined = await connection.execute(
        "SELECT examined_row_count FROM runs WHERE id = %s",
        (newest_done["id"],),
    )
    return {
        "run_number": newest_done["run_number"],
        "rows_examined": (await examined.fetchone())["examined_row_count"],
        "rules": await rules_that_ran(connection, newest_done["id"]),
    }


async def _newest_done_run(
    connection: AsyncConnection,
    project_id: UUID,
) -> dict[str, Any] | None:
    """The run that last committed to this register, and its number.

    A run's number is not stored anywhere. It is counted here exactly as
    `app/examine/read_findings.py`, `app/register/read_history.py` and
    `app/projects/list_projects.py` count it, so no surface can number one run
    differently.
    """
    result = await connection.execute(
        "SELECT id, finished_at, run_number FROM ("
        "SELECT id, finished_at, status, ROW_NUMBER() OVER ("
        "PARTITION BY project_id ORDER BY created_at ASC) AS run_number "
        "FROM runs WHERE project_id = %s) AS numbered_runs "
        "WHERE status = %s ORDER BY finished_at DESC LIMIT 1",
        (project_id, DONE),
    )
    return await result.fetchone()


def register_as_markdown(register: dict[str, Any]) -> str:
    """Generated from the same JSON the screen and the MCP caller read.

    The new fields only — `evidence`, `findings` and `rules` — so a reader of
    the file and a reader of the screen are looking at one record. No rule id
    anywhere: whoever opens this file has never seen `config/rules.yaml`.
    """
    lines = [
        f"# Requirements-to-Delivery Register — {register['project']['name']}",
        "",
    ]
    if register["exported_at"] is not None:
        lines += [f"Last updated {register['exported_at']}.", ""]

    if not register["rows"]:
        return "\n".join(lines + [EMPTY_REGISTER_LINE, ""] + _rules_lines(register))

    headings = [COLUMN_HEADINGS[name] for name in register["columns"]]
    lines += [
        "| Row | " + " | ".join(headings) + " |",
        "|---|" + "|".join(["---"] * len(headings)) + "|",
    ]
    for row in register["rows"]:
        cells = [_single_line(row["cells"][name]) for name in register["columns"]]
        lines.append(f"| {row['row_number']} | " + " | ".join(cells) + " |")
    lines.append("")

    for row in register["rows"]:
        lines += _row_detail_lines(row)
    return "\n".join(lines + _rules_lines(register))


def _row_detail_lines(row: dict[str, Any]) -> list[str]:
    lines = [
        f"## Row {row['row_number']} — {_single_line(row['cells']['what_was_asked'])}",
        "",
        "**Evidence**",
        "",
    ]
    lines += [_evidence_line(entry) for entry in row["evidence"]]
    lines.append("")
    # A row nothing was found wrong with prints no block at all: "No findings"
    # on every clean row is noise a reader has to skim past (item 43).
    if row.get("findings"):
        lines += ["**Findings**", ""]
        lines += [_finding_line(finding) for finding in row["findings"]]
        lines.append("")
    return lines


def _evidence_line(entry: dict[str, Any]) -> str:
    cells = ", ".join(entry["cells"])
    if entry["quote"] is None:
        return f"- {entry['absence']} — {cells}"
    words = " ".join(entry["quote"].split())
    return f"- {entry['source_line']}: \"{words}\" — {cells}"


def _finding_line(finding: dict[str, Any]) -> str:
    return (
        f"- {_single_line(finding['rule_text'])} — raised by run "
        f"{finding['raised_by_run']} — {_single_line(finding['issue'])}"
    )


def _rules_lines(register: dict[str, Any]) -> list[str]:
    """Which rules last judged this register, named by their own words.

    A findings list is only honest beside the rules that produced it: no
    finding under a rule that never ran means nothing at all.
    """
    applied = register["rules"]
    if applied is None or not applied["rules"]:
        return ["## Rules", "", "No rules applied", ""]
    return (
        [
            "## Rules",
            "",
            f"Run {applied['run_number']} applied "
            f"{_counted(len(applied['rules']), 'rule')} against "
            f"{_counted(applied['rows_examined'], 'row')}",
            "",
        ]
        + [
            f"- {_single_line(rule['text'])}{_rule_settings(rule)}"
            for rule in applied["rules"]
        ]
        + [""]
    )


def _rule_settings(rule: dict[str, Any]) -> str:
    """A rule whose text names a setting cannot be read without its value."""
    params = rule.get("params")
    if not params:
        return ""
    settings = ", ".join(f"{name}: {value}" for name, value in params.items())
    return f" ({settings})"


def _counted(how_many: int, thing: str) -> str:
    return f"{how_many} {thing}" if how_many == 1 else f"{how_many} {thing}s"


def _single_line(cell_value: str) -> str:
    return " ".join(cell_value.split()).replace("|", "\\|")
