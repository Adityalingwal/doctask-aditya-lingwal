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
_FINDING_COLUMNS = (
    "findings.id, findings.rule_id, findings.rule_text, findings.issue, "
    "findings.evidence, findings.question, findings.decision_key, "
    "decisions.outcome, reported_row.row_number, reported_row.id "
    "AS register_row_id"
)
_FINDING_JOINS = (
    " FROM findings "
    "JOIN decisions ON decisions.id = findings.decision_key "
    "JOIN register_rows ON register_rows.id = findings.register_row_id "
    "JOIN register_rows AS reported_row ON reported_row.id = COALESCE("
    "register_rows.merged_into_register_row_id, register_rows.id) "
)
_SELECT_FINDINGS = "SELECT " + _FINDING_COLUMNS + _FINDING_JOINS
_ORDER_FINDINGS = " ORDER BY reported_row.row_number, findings.rule_id"

# Each rule's latest `done` run that actually applied it, and that run's
# number. A run's number is not stored anywhere; it is counted here exactly as
# `app/register/read_history.py` and `app/projects/list_projects.py` count it,
# so no surface can number one run differently. `rules_applied` is null on a
# run that never reached Examine, and the lateral join drops it.
_LATEST_APPLICABLE_FINDINGS = (
    "WITH numbered_runs AS ("
    "SELECT runs.id, runs.status, runs.finished_at, runs.rules_applied, "
    "ROW_NUMBER() OVER (PARTITION BY runs.project_id "
    "ORDER BY runs.created_at ASC) AS run_number "
    "FROM runs WHERE runs.project_id = %s), "
    "latest_run_of_rule AS ("
    "SELECT DISTINCT ON (applied.rule_id) applied.rule_id AS rule_id, "
    "numbered_runs.id AS run_id FROM numbered_runs "
    "CROSS JOIN LATERAL jsonb_array_elements_text(numbered_runs.rules_applied) "
    "AS applied(rule_id) WHERE numbered_runs.status = %s "
    "ORDER BY applied.rule_id, numbered_runs.finished_at DESC) "
    "SELECT " + _FINDING_COLUMNS + ", numbered_runs.run_number"
    + _FINDING_JOINS
    + "JOIN latest_run_of_rule ON latest_run_of_rule.rule_id = findings.rule_id "
    "AND latest_run_of_rule.run_id = findings.run_id "
    "JOIN numbered_runs ON numbered_runs.id = findings.run_id "
    "WHERE decisions.outcome = %s" + _ORDER_FINDINGS
)


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


def exported_finding(finding: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_number": finding["row_number"],
        "rule_id": finding["rule_id"],
        "rule_text": finding["rule_text"],
        "issue": finding["issue"],
        "evidence": finding["evidence"],
        "question": finding["question"],
    }


def finding_on_the_register(finding: dict[str, Any]) -> dict[str, Any]:
    """A finding as the register shows it, naming the run that raised it.

    The run number is what a person reads beside the finding in History, so
    the register names the same one rather than a run id nobody has seen.
    """
    return exported_finding(finding) | {
        "finding_id": str(finding["finding_id"]),
        "raised_by_run": finding["raised_by_run"],
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
    """What each rule found, the last time each rule actually ran.

    Every run re-examines the whole register, so a rule that raised a finding
    in run 5 and raised nothing in run 6 has answered again — and the register
    shows the newer answer, which is no finding at all. A rejected finding in
    that newer run clears the row for that rule too: the person was asked and
    said no. Where the newer run never applied the rule — because a kind of
    document it names had not been read — the older answer is still the
    latest one there is, and it stands.

    Only runs that ended `done` count: an approved finding on a run still at
    review has not passed the add/discard gate, and one on a discarded run
    never will. Nothing is deleted; History keeps every run's findings.
    """
    result = await connection.execute(
        _LATEST_APPLICABLE_FINDINGS, (project_id, DONE, APPROVED)
    )
    return [
        _finding_as_read(finding) | {"raised_by_run": finding["run_number"]}
        for finding in await result.fetchall()
    ]


async def rules_that_ran(
    connection: AsyncConnection,
    run_id: UUID,
) -> list[dict[str, Any]]:
    """Every rule this run actually sent to the model, and no other.

    A rule the run froze but never applied — because a kind of document it
    names had not been read — did not judge this register, and reporting it as
    having run would make an honest `No findings` result say more than it can.
    The text still comes from the snapshot, which is where a rule's words live.
    """
    applied = await _rules_applied(connection, run_id)
    frozen = await frozen_rules_of_run(connection, run_id) or []
    rule_by_id = {rule["id"]: rule for rule in frozen}
    return [_rule_as_reported(rule_by_id[rule_id]) for rule_id in applied]


async def _rules_applied(
    connection: AsyncConnection,
    run_id: UUID,
) -> list[str]:
    """The rule ids Examine sent to the model, or none while it has not run."""
    result = await connection.execute(
        "SELECT rules_applied FROM runs WHERE id = %s",
        (run_id,),
    )
    run = await result.fetchone()
    return (run["rules_applied"] if run else None) or []


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
    return [_finding_as_read(finding) for finding in await result.fetchall()]


def _finding_as_read(finding: dict[str, Any]) -> dict[str, Any]:
    return {
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
