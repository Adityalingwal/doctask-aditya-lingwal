from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, NamedTuple
from uuid import UUID, uuid4

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from app.database import build_connection_pool
from app.examine.read_findings import approved_findings_of_project
from app.register.cells import (
    CELL_NAMES,
    IN_WRITING_NOT_KNOWN_YET,
    STATUS_REQUESTED,
    TESTING_NOT_KNOWN_YET,
)
from app.register.export_register import build_register_document
from app.review.review_queue import APPROVED, FINDING_DECISION, REJECTED
from app.runs.statuses import DONE
from tests.runs.application import temporary_database


CLEARED_BY_A_CLEAN_RERUN = 1
REPLACED_BY_A_NEW_RAISE = 2
PRESERVED_BECAUSE_THE_RULE_DID_NOT_RUN = 3
CLEARED_BY_A_REJECTION = 4

# The earlier run applied every rule; the later one never applied R1, because a
# kind of document R1 names had not been read by then.
EARLIER_RUN_APPLIED = ["R1", "R2", "R4", "R5"]
LATER_RUN_APPLIED = ["R2", "R4", "R5"]


class SeededFinding(NamedTuple):
    run: str
    rule_id: str
    row_number: int
    outcome: str


SEEDED_FINDINGS = (
    SeededFinding("earlier", "R4", CLEARED_BY_A_CLEAN_RERUN, APPROVED),
    SeededFinding("earlier", "R2", REPLACED_BY_A_NEW_RAISE, APPROVED),
    SeededFinding("earlier", "R1", PRESERVED_BECAUSE_THE_RULE_DID_NOT_RUN, APPROVED),
    SeededFinding("earlier", "R5", CLEARED_BY_A_REJECTION, APPROVED),
    # R4 raised nothing at all in the later run, which is the newer answer.
    SeededFinding("later", "R2", REPLACED_BY_A_NEW_RAISE, APPROVED),
    SeededFinding("later", "R5", CLEARED_BY_A_REJECTION, REJECTED),
)


def test_the_register_shows_only_the_latest_applicable_finding_per_rule_and_row() -> None:
    """Each rule's newest answer stands, and no row ever carries two of one rule.

    Four rows, four rules, two runs. A rule that raised nothing the second
    time has answered again; a rule that raised again replaces rather than
    adds; a rule the second run never applied keeps the answer it gave; and a
    finding the person rejected in the newest run leaves the row clear rather
    than letting the older one reappear.
    """
    shown, register = asyncio.run(_two_runs_of_findings())

    assert [(finding["row_number"], finding["rule_id"]) for finding in shown] == [
        (REPLACED_BY_A_NEW_RAISE, "R2"),
        (PRESERVED_BECAUSE_THE_RULE_DID_NOT_RUN, "R1"),
    ]
    assert [finding["raised_by_run"] for finding in shown] == [2, 1]
    assert {
        row["row_number"]: [finding["rule_id"] for finding in row["findings"]]
        for row in register["rows"]
    } == {
        CLEARED_BY_A_CLEAN_RERUN: [],
        REPLACED_BY_A_NEW_RAISE: ["R2"],
        PRESERVED_BECAUSE_THE_RULE_DID_NOT_RUN: ["R1"],
        CLEARED_BY_A_REJECTION: [],
    }
    (kept,) = [
        finding
        for row in register["rows"]
        for finding in row["findings"]
        if finding["rule_id"] == "R1"
    ]
    assert kept["raised_by_run"] == 1
    assert kept["issue"] == _issue_of("earlier", "R1")


async def _two_runs_of_findings() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    with temporary_database() as database_url:
        pool = build_connection_pool(database_url)
        await pool.open(wait=True)
        try:
            async with pool.connection() as connection:
                project = await _seed(connection)
                return (
                    await approved_findings_of_project(connection, project["id"]),
                    await build_register_document(connection, project),
                )
        finally:
            await pool.close()


async def _seed(connection: AsyncConnection) -> dict[str, Any]:
    project_id = uuid4()
    name = f"Latest finding {project_id}"
    await connection.execute(
        "INSERT INTO projects (id, name, source_folder_path) VALUES (%s, %s, %s)",
        (project_id, name, f"sample-projects/latest-{project_id}"),
    )
    started = datetime(2026, 8, 20, 9, 0, tzinfo=timezone.utc)
    run_id = {
        "earlier": await _insert_run(
            connection, project_id, started, EARLIER_RUN_APPLIED
        ),
        "later": await _insert_run(
            connection,
            project_id,
            started + timedelta(days=1),
            LATER_RUN_APPLIED,
        ),
    }
    row_id = {
        row_number: await _insert_row(
            connection, project_id, run_id["earlier"], row_number
        )
        for row_number in range(1, 5)
    }
    for seeded in SEEDED_FINDINGS:
        await _insert_finding(connection, run_id[seeded.run], row_id, seeded)
    return {"id": project_id, "name": name}


async def _insert_run(
    connection: AsyncConnection,
    project_id: UUID,
    moment: datetime,
    rules_applied: list[str],
) -> UUID:
    run_id = uuid4()
    await connection.execute(
        "INSERT INTO runs (id, project_id, status, created_at, finished_at, "
        "examined_row_count, rules_snapshot, rules_applied) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (
            run_id,
            project_id,
            DONE,
            moment,
            moment,
            4,
            Jsonb(
                [
                    {"id": rule_id, "text": f"Rule {rule_id}.", "params": {}}
                    for rule_id in EARLIER_RUN_APPLIED
                ]
            ),
            Jsonb(rules_applied),
        ),
    )
    return run_id


async def _insert_row(
    connection: AsyncConnection,
    project_id: UUID,
    run_id: UUID,
    row_number: int,
) -> UUID:
    row_id = uuid4()
    await connection.execute(
        "INSERT INTO register_rows (id, project_id, "
        + ", ".join(CELL_NAMES)
        + ", fingerprint, row_number, proposed_by_run_id, is_committed) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, true)",
        (
            row_id,
            project_id,
            f"Requirement {row_number}.",
            IN_WRITING_NOT_KNOWN_YET,
            TESTING_NOT_KNOWN_YET,
            STATUS_REQUESTED,
            f"fingerprint-{row_number}",
            row_number,
            run_id,
        ),
    )
    return row_id


async def _insert_finding(
    connection: AsyncConnection,
    run_id: UUID,
    row_id: dict[int, UUID],
    seeded: SeededFinding,
) -> None:
    decision_id = uuid4()
    question = (
        f"Row #{seeded.row_number} breaks the rule about {seeded.rule_id}. "
        "Attach this finding?"
    )
    await connection.execute(
        "INSERT INTO decisions (id, run_id, kind, question, outcome, decided_at) "
        "VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)",
        (decision_id, run_id, FINDING_DECISION, question, seeded.outcome),
    )
    await connection.execute(
        "INSERT INTO findings (id, run_id, register_row_id, rule_id, rule_text, "
        "issue, evidence, question, decision_key) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            uuid4(),
            run_id,
            row_id[seeded.row_number],
            seeded.rule_id,
            f"Rule {seeded.rule_id}.",
            _issue_of(seeded.run, seeded.rule_id),
            IN_WRITING_NOT_KNOWN_YET,
            question,
            decision_id,
        ),
    )


def _issue_of(run: str, rule_id: str) -> str:
    return f"The {run} run found {rule_id} broken on this row."
