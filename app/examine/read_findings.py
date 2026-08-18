from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import AsyncConnection

from app.examine.frozen_rules import frozen_rules_of_run
from app.review.review_queue import APPROVED
from app.runs.statuses import DONE


# A finding follows its row through a merge, so both the id and the number it
# reports come from the row it ended up on. Reading the number from the
# proposal instead would sit a finding under one row while naming another.
_SELECT_FINDINGS = (
    "SELECT findings.id, findings.rule_id, findings.rule_text, findings.issue, "
    "findings.evidence, findings.question, findings.decision_key, "
    "decisions.outcome, reported_row.row_number, reported_row.id "
    "AS register_row_id FROM findings "
    "JOIN decisions ON decisions.id = findings.decision_key "
    "JOIN register_rows ON register_rows.id = findings.register_row_id "
    "JOIN register_rows AS reported_row ON reported_row.id = COALESCE("
    "register_rows.merged_into_register_row_id, register_rows.id) "
)
_ORDER_FINDINGS = " ORDER BY reported_row.row_number, findings.rule_id"


async def examine_under_review(
    connection: AsyncConnection,
    run: dict[str, Any],
) -> dict[str, Any] | None:
    """What Examine judged and found, or nothing while it has not run yet."""
    if run["examined_row_count"] is None:
        return None
    findings = await findings_of_run(connection, run["id"])
    return await _examine_summary(
        connection,
        run["id"],
        run["examined_row_count"],
        [_finding_under_review(finding) for finding in findings],
    )


async def examine_as_exported(
    connection: AsyncConnection,
    run_id: UUID,
) -> dict[str, Any]:
    """The rules that ran, how much they ran against, and what they found.

    An empty findings list is the honest result D10 asks for, and it is only
    honest because the rules and the row count sit beside it.
    """
    examined = await connection.execute(
        "SELECT examined_row_count FROM runs WHERE id = %s",
        (run_id,),
    )
    findings = await findings_of_run(connection, run_id, approved_only=True)
    return await _examine_summary(
        connection,
        run_id,
        (await examined.fetchone())["examined_row_count"],
        [exported_finding(finding) for finding in findings],
    )


def exported_finding(finding: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_number": finding["row_number"],
        "rule_id": finding["rule_id"],
        "rule_text": finding["rule_text"],
        "issue": finding["issue"],
        "evidence": finding["evidence"],
        "question": finding["question"],
    }


async def _examine_summary(
    connection: AsyncConnection,
    run_id: UUID,
    rows_examined: int | None,
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "rules": await rules_that_ran(connection, run_id),
        "rows_examined": rows_examined,
        "findings": findings,
    }


def _finding_under_review(finding: dict[str, Any]) -> dict[str, Any]:
    """A finding as the person answering its gate is shown it."""
    return {
        "finding_id": str(finding["finding_id"]),
        "decision_id": str(finding["decision_id"]),
        "row_number": finding["row_number"],
        "rule_id": finding["rule_id"],
        "rule_text": finding["rule_text"],
        "issue": finding["issue"],
        "evidence": finding["evidence"],
        "question": finding["question"],
        "outcome": finding["outcome"],
    }


async def findings_of_run(
    connection: AsyncConnection,
    run_id: UUID,
    approved_only: bool = False,
) -> list[dict[str, Any]]:
    """This run's findings, each carrying the answer read from its decision.

    A finding stores no answer of its own, so the outcome is joined from the
    decision that gates it and there is never a second copy to fall behind.
    """
    if approved_only:
        return await _findings_matching(
            connection,
            "WHERE findings.run_id = %s AND decisions.outcome = %s",
            (run_id, APPROVED),
        )
    return await _findings_matching(
        connection,
        "WHERE findings.run_id = %s",
        (run_id,),
    )


async def approved_findings_of_project(
    connection: AsyncConnection,
    project_id: UUID,
) -> list[dict[str, Any]]:
    """Every finding a person approved onto a row of this project's register.

    Only findings of runs that ended `done` count: an approved finding on a
    run still at review has not passed the add/discard gate, and one on a
    discarded run never will — the register is only what was added to it.
    """
    return await _findings_matching(
        connection,
        "WHERE register_rows.project_id = %s AND decisions.outcome = %s "
        "AND EXISTS (SELECT 1 FROM runs "
        "WHERE runs.id = findings.run_id AND runs.status = %s)",
        (project_id, APPROVED, DONE),
    )


async def rules_that_ran(
    connection: AsyncConnection,
    run_id: UUID,
) -> list[dict[str, Any]]:
    """Every rule this run was judged against — the ones it froze, and no others."""
    frozen = await frozen_rules_of_run(connection, run_id) or []
    return [_rule_as_reported(rule) for rule in frozen]


def _rule_as_reported(rule: dict[str, Any]) -> dict[str, Any]:
    """A rule's text alone does not say what it ran at.

    A rule may name a limit in its text and keep the value in its params, so
    reporting the text without them cannot tell a reader which value applied.
    No rule in `config/rules.yaml` carries params today; the last one that did
    left with the date cells on 2026-08-17.
    """
    reported: dict[str, Any] = {"id": rule["id"], "text": rule["text"]}
    if rule.get("params"):
        reported["params"] = rule["params"]
    return reported


async def _findings_matching(
    connection: AsyncConnection,
    condition: str,
    parameters: tuple[Any, ...],
) -> list[dict[str, Any]]:
    result = await connection.execute(
        _SELECT_FINDINGS + condition + _ORDER_FINDINGS,
        parameters,
    )
    return [
        {
            "finding_id": finding["id"],
            "decision_id": finding["decision_key"],
            "register_row_id": finding["register_row_id"],
            "row_number": finding["row_number"],
            "rule_id": finding["rule_id"],
            "rule_text": finding["rule_text"],
            "issue": finding["issue"],
            "evidence": finding["evidence"],
            "question": finding["question"],
            "outcome": finding["outcome"],
        }
        for finding in await result.fetchall()
    ]
