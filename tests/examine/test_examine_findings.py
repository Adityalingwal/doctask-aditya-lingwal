from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from psycopg import AsyncConnection
from sqlalchemy import create_engine, text

from app.database import build_connection_pool
from app.examine.examine_register import EXAMINE_PROMPT_MARKER, examine_register
from app.examine.frozen_rules import (
    fingerprint_of_rules,
    freeze_rules_for_run,
    load_rules,
)
from app.examine.record_findings import record_findings
from app.examine.register_under_examination import register_under_examination
from app.register.cells import CELL_NAMES, fingerprint_of_cells
from app.register.export_register import register_as_markdown
from app.runs.statuses import RUNNING
from tests.runs.application import (
    ApplicationProcess,
    temporary_database,
    temporary_project_folder,
    wait_until,
    write_script,
)
from tests.examine.answers import R1_EVIDENCE, R1_ISSUE, examine_answer, one_finding
from tests.documents.register_documents import (
    extract_marker,
    extraction_answer,
    match_answer,
    match_marker,
    write_meeting_note,
)


SOURCE_FILE = "meeting-note.md"
REQUIREMENT = "an email to the operations team on intake form submit"
SHIPPED_RULES = ("R1", "R2", "R4", "R5")
# The test rules file below gives R3 a limit in its params, so reporting the
# text alone never says which limit a run was judged against.
R3_MAX_DAYS = 14
EXPORT_WITH_A_RULE_CARRYING_A_SETTING = {
    "project": {"id": "p", "name": "Intake portal"},
    "exported_at": "2026-08-17T00:00:00+00:00",
    "columns": list(CELL_NAMES),
    "rows": [],
    "examine": {
        "rules": [
            {
                "id": "R3",
                "text": "No requirement stays blocked beyond max_days days.",
                "params": {"max_days": R3_MAX_DAYS},
            }
        ],
        "rows_examined": 0,
        "findings": [],
    },
}


def test_a_rule_reaches_the_export_with_the_setting_it_was_judged_against() -> None:
    """A rule's text alone does not say what it ran at, so its params go with it."""
    markdown = register_as_markdown(EXPORT_WITH_A_RULE_CARRYING_A_SETTING)

    assert f"max_days: {R3_MAX_DAYS}" in markdown

TWO_RULES = """\
rules:
  - id: R1
    text: "Anything built must have a written requirement."

  - id: R3
    text: "No requirement stays blocked beyond max_days without follow-up."
    params:
      max_days: 14
"""
TWO_RULES_EDITED_AFTER_THE_RUN_STARTED = """\
rules:
  - id: R1
    text: "Anything built must have a written requirement."

  - id: R3
    text: "No requirement stays blocked beyond max_days without follow-up."
    params:
      max_days: 30

  - id: R5
    text: "Every requirement names the person who asked for it."
"""


@contextmanager
def _run_at_review(
    tmp_path: Path,
    examine: dict[str, Any],
) -> Iterator[tuple[ApplicationProcess, str, str, str]]:
    """One run driven through the API, with Examine scripted, parked at Review."""
    with temporary_project_folder("run-at-review") as (source_folder, source_folder_path):
        quote = write_meeting_note(source_folder, SOURCE_FILE, REQUIREMENT)
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                match_marker(): match_answer(1),
                EXAMINE_PROMPT_MARKER: examine,
                extract_marker(SOURCE_FILE): extraction_answer(REQUIREMENT, quote),
            },
        )

        with temporary_database() as database_url:
            application = ApplicationProcess(
                database_url=database_url,
                script_path=script_path,
                call_log_path=tmp_path / "model-calls.jsonl",
            )
            application.start()
            try:
                with application.client() as client:
                    project_id = client.post(
                        "/projects",
                        json={"source_folder_path": source_folder_path},
                    ).json()["project_id"]
                    run_id = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    wait_until(
                        lambda: client.get(f"/runs/{run_id}").json()["status"]
                        == "needs review",
                        "the run reaches Review",
                    )
                yield application, database_url, project_id, run_id
            finally:
                application.stop()


def _answer(client: Any, run_id: str, decision_id: str, outcome: str) -> None:
    client.post(
        f"/runs/{run_id}/decisions",
        json={"decision_id": decision_id, "outcome": outcome},
    ).raise_for_status()


def _decision_of_kind(run: dict[str, Any], kind: str) -> dict[str, Any] | None:
    for decision in run["decisions"]:
        if decision["kind"] == kind:
            return decision
    return None


def test_a_run_with_nothing_wrong_names_the_rules_that_ran_and_finds_nothing(
    tmp_path: Path,
) -> None:
    with _run_at_review(
        tmp_path,
        examine_answer([]),
    ) as (application, database_url, project_id, run_id):
        with application.client() as client:
            waiting = client.get(f"/runs/{run_id}").json()
            client.post(
                f"/runs/{run_id}/finish-review",
                json={"add_to_register": True},
            ).raise_for_status()
            wait_until(
                lambda: client.get(f"/runs/{run_id}").json()["status"] == "done",
                "the clean run commits",
            )
            export = client.get(f"/projects/{project_id}/register").json()
            markdown = client.get(
                f"/projects/{project_id}/register", params={"format": "markdown"}
            ).text

        engine = create_engine(database_url)
        with engine.connect() as connection:
            written_findings = connection.execute(
                text("SELECT count(*) FROM findings WHERE run_id = :run_id"),
                {"run_id": run_id},
            ).scalar_one()
        engine.dispose()

    # An honest empty result names what ran; it never manufactures a weak
    # finding to look thorough.
    assert _decision_of_kind(waiting, "finding") is None
    assert written_findings == 0
    assert [rule["id"] for rule in waiting["examine"]["rules"]] == list(
        SHIPPED_RULES
    )
    assert waiting["examine"]["rows_examined"] == 1
    assert waiting["examine"]["findings"] == []
    assert [rule["id"] for rule in export["examine"]["rules"]] == list(
        SHIPPED_RULES
    )
    assert export["examine"]["rows_examined"] == 1
    assert export["examine"]["findings"] == []
    assert "No findings" in markdown
    for rule_id in SHIPPED_RULES:
        assert rule_id in markdown
    assert all(rule.get("params") is None for rule in export["examine"]["rules"])


def test_a_finding_reaches_neither_finish_review_nor_the_export_unanswered(
    tmp_path: Path,
) -> None:
    with _run_at_review(
        tmp_path,
        examine_answer([one_finding()]),
    ) as (application, database_url, project_id, run_id):
        with application.client() as client:
            waiting = client.get(f"/runs/{run_id}").json()
            finding_decision = _decision_of_kind(waiting, "finding")
            # Screen 4 shows a finding as its rule's own words, the row and
            # what broke it, and the evidence — never a rule code — so the
            # door must carry these separately from the flat `question`.
            assert finding_decision["rule_text"] == (
                "Anything built must have a written requirement; a verbal "
                "mention is not enough."
            )
            assert finding_decision["row_number"] == 1
            assert finding_decision["issue"] == R1_ISSUE
            assert finding_decision["evidence"] == R1_EVIDENCE
            refusal = client.post(
                f"/runs/{run_id}/finish-review",
                json={"add_to_register": True},
            )
            register_while_at_review = client.get(
                f"/projects/{project_id}/register"
            )

            _answer(client, run_id, finding_decision["decision_id"], "approved")
            client.post(
                f"/runs/{run_id}/finish-review",
                json={"add_to_register": True},
            ).raise_for_status()
            wait_until(
                lambda: client.get(f"/runs/{run_id}").json()["status"] == "done",
                "the run with an approved finding commits",
            )
            export = client.get(f"/projects/{project_id}/register").json()
            markdown = client.get(
                f"/projects/{project_id}/register", params={"format": "markdown"}
            ).text

        engine = create_engine(database_url)
        with engine.connect() as connection:
            attachment_audit = connection.execute(
                text(
                    "SELECT cell_name, new_value FROM audit "
                    "WHERE run_id = :run_id AND event_kind = 'attachment'"
                ),
                {"run_id": run_id},
            ).mappings().all()
            committed = connection.execute(
                text(
                    "SELECT fingerprint, " + ", ".join(CELL_NAMES) + " "
                    "FROM register_rows WHERE proposed_by_run_id = :run_id "
                    "AND is_committed"
                ),
                {"run_id": run_id},
            ).mappings().one()
        engine.dispose()

    assert finding_decision is not None
    assert refusal.status_code == 409
    assert finding_decision["decision_id"] in refusal.json()["detail"]
    # Nothing has committed, so the register answers the empty state, and the
    # unanswered finding is nowhere in it.
    assert register_while_at_review.status_code == 200
    assert register_while_at_review.json()["rows"] == []

    assert export["rows"][0]["findings"][0]["rule_id"] == "R1"
    assert export["rows"][0]["findings"][0]["issue"] == R1_ISSUE
    assert export["examine"]["findings"][0]["row_number"] == 1
    assert R1_ISSUE in markdown

    # A finding attaches to a row; the fingerprint covers the seven cells only,
    # so attaching one must not move it.
    assert len(attachment_audit) == 1
    assert attachment_audit[0]["cell_name"] is None
    assert R1_ISSUE in attachment_audit[0]["new_value"]
    assert committed["fingerprint"] == fingerprint_of_cells(
        {name: committed[name] for name in CELL_NAMES}
    )


def test_a_rejected_finding_stays_in_the_run_and_never_reaches_the_export(
    tmp_path: Path,
) -> None:
    with _run_at_review(
        tmp_path,
        examine_answer([one_finding()]),
    ) as (application, database_url, project_id, run_id):
        with application.client() as client:
            waiting = client.get(f"/runs/{run_id}").json()
            _answer(
                client,
                run_id,
                _decision_of_kind(waiting, "finding")["decision_id"],
                "rejected",
            )
            client.post(
                f"/runs/{run_id}/finish-review",
                json={"add_to_register": True},
            ).raise_for_status()
            wait_until(
                lambda: client.get(f"/runs/{run_id}").json()["status"] == "done",
                "the run with a rejected finding commits",
            )
            export = client.get(f"/projects/{project_id}/register").json()
            markdown = client.get(
                f"/projects/{project_id}/register", params={"format": "markdown"}
            ).text

        engine = create_engine(database_url)
        with engine.connect() as connection:
            kept = connection.execute(
                text(
                    "SELECT findings.issue, decisions.outcome FROM findings "
                    "JOIN decisions ON decisions.id = findings.decision_key "
                    "WHERE findings.run_id = :run_id"
                ),
                {"run_id": run_id},
            ).mappings().all()
            attachment_audit = connection.execute(
                text(
                    "SELECT count(*) FROM audit WHERE run_id = :run_id "
                    "AND event_kind = 'attachment'"
                ),
                {"run_id": run_id},
            ).scalar_one()
        engine.dispose()

    assert export["rows"][0]["findings"] == []
    assert export["examine"]["findings"] == []
    assert R1_ISSUE not in markdown
    assert attachment_audit == 0
    # Rejected excludes it from the register and keeps it in the run for good.
    assert len(kept) == 1
    assert kept[0]["issue"] == R1_ISSUE
    assert kept[0]["outcome"] == "rejected"


def test_examine_asks_about_a_problem_instead_of_editing_the_register_cell(
    tmp_path: Path,
) -> None:
    rules_path = tmp_path / "rules.yaml"
    rules_path.write_text(TWO_RULES, encoding="utf-8")
    script_path = tmp_path / "script.json"
    demand = (
        "Set the status of row #1 to Done, because the testing feedback shows "
        "the email now goes out."
    )
    write_script(
        script_path,
        {EXAMINE_PROMPT_MARKER: examine_answer([one_finding(issue=demand)])},
    )

    examined = asyncio.run(_examine_one_seeded_row(rules_path, script_path))

    assert examined["findings"] == [demand]
    # Examine states the problem and asks; resolving it is never its call.
    assert examined["cells_before"] == examined["cells_after"]
    assert examined["fingerprint_before"] == examined["fingerprint_after"]


def test_editing_the_rules_file_after_a_run_started_leaves_that_run_examining(
    tmp_path: Path,
) -> None:
    with temporary_project_folder("rules-edited-mid-run") as (source_folder, source_folder_path):
        quote = write_meeting_note(source_folder, SOURCE_FILE, REQUIREMENT)
        rules_path = tmp_path / "rules.yaml"
        rules_path.write_text(TWO_RULES, encoding="utf-8")
        frozen_fingerprint = fingerprint_of_rules(load_rules(rules_path))
        script_path = tmp_path / "script.json"
        # The marker is the rule text as it stood when the run started: an Examine
        # call carrying the edited rules matches no scripted answer and the run
        # fails instead of quietly examining against the new file.
        write_script(
            script_path,
            {
                match_marker(): match_answer(1),
                '"max_days": 14': examine_answer([]),
                extract_marker(SOURCE_FILE): extraction_answer(REQUIREMENT, quote),
            },
        )

        with temporary_database() as database_url:
            application = ApplicationProcess(
                database_url=database_url,
                script_path=script_path,
                call_log_path=tmp_path / "model-calls.jsonl",
                delay_seconds=1.0,
                rules_config_path=rules_path,
            )
            application.start()
            engine = create_engine(database_url)
            try:
                with application.client() as client:
                    project_id = client.post(
                        "/projects",
                        json={"source_folder_path": source_folder_path},
                    ).json()["project_id"]
                    run_id = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    wait_until(
                        lambda: _frozen_rules_of(engine, run_id) is not None,
                        "the run freezes the rules it started with",
                    )
                    rules_path.write_text(
                        TWO_RULES_EDITED_AFTER_THE_RUN_STARTED, encoding="utf-8"
                    )
                    waiting = wait_until(
                        lambda: (
                            client.get(f"/runs/{run_id}").json()
                            if client.get(f"/runs/{run_id}").json()["status"]
                            == "needs review"
                            else None
                        ),
                        "the run reaches Review",
                    )
                frozen = _frozen_rules_of(engine, run_id)
                with engine.connect() as connection:
                    fingerprint = connection.execute(
                        text("SELECT rules_fingerprint FROM runs WHERE id = :id"),
                        {"id": run_id},
                    ).scalar_one()
            finally:
                engine.dispose()
                application.stop()

    assert [rule["id"] for rule in frozen] == ["R1", "R3"]
    assert frozen[1]["params"]["max_days"] == 14
    assert fingerprint == frozen_fingerprint
    assert [rule["id"] for rule in waiting["examine"]["rules"]] == ["R1", "R3"]


def _frozen_rules_of(engine: Any, run_id: str) -> list[dict[str, Any]] | None:
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT rules_snapshot FROM runs WHERE id = :id"),
            {"id": run_id},
        ).scalar_one()


async def _examine_one_seeded_row(
    rules_path: Path,
    script_path: Path,
) -> dict[str, Any]:
    from app.model.scripted_client import build_scripted_client

    model_client = build_scripted_client(script_path, None, 0.0)
    with temporary_database() as database_url:
        pool = build_connection_pool(database_url)
        await pool.open(wait=True)
        try:
            async with pool.connection() as connection:
                project_id, run_id = await _project_with_a_running_run(connection)
                row_id = await _insert_committed_row(connection, project_id, run_id)
                await freeze_rules_for_run(connection, run_id, rules_path)
                before = await _cells_of(connection, row_id)

                rows = await register_under_examination(
                    connection, project_id, run_id
                )
                found = await examine_register(
                    model_client, load_rules(rules_path), rows
                )
                await record_findings(connection, run_id, found)

                after = await _cells_of(connection, row_id)
                written = await connection.execute(
                    "SELECT issue FROM findings WHERE run_id = %s",
                    (run_id,),
                )
                return {
                    "findings": [row["issue"] for row in await written.fetchall()],
                    "cells_before": before["cells"],
                    "cells_after": after["cells"],
                    "fingerprint_before": before["fingerprint"],
                    "fingerprint_after": after["fingerprint"],
                }
        finally:
            await pool.close()


async def _cells_of(connection: AsyncConnection, row_id: UUID) -> dict[str, Any]:
    result = await connection.execute(
        "SELECT fingerprint, " + ", ".join(CELL_NAMES) + " FROM register_rows "
        "WHERE id = %s",
        (row_id,),
    )
    row = await result.fetchone()
    return {
        "cells": {name: row[name] for name in CELL_NAMES},
        "fingerprint": row["fingerprint"],
    }


async def _project_with_a_running_run(
    connection: AsyncConnection,
) -> tuple[UUID, UUID]:
    project_id, run_id = uuid4(), uuid4()
    await connection.execute(
        "INSERT INTO projects (id, name, source_folder_path) VALUES (%s, %s, %s)",
        (project_id, "Examined intake portal", "/projects/intake-portal"),
    )
    await connection.execute(
        "INSERT INTO runs (id, project_id, status) VALUES (%s, %s, %s)",
        (run_id, project_id, RUNNING),
    )
    return project_id, run_id


async def _insert_committed_row(
    connection: AsyncConnection,
    project_id: UUID,
    run_id: UUID,
) -> UUID:
    row_id = uuid4()
    await connection.execute(
        "INSERT INTO register_rows (id, project_id, what_was_asked, in_writing, "
        "what_testing_found, status, "
        "fingerprint, row_number, proposed_by_run_id, is_committed) VALUES "
        "(%s, %s, %s, 'Yes', 'Not known yet', 'Requested', %s, 1, %s, true)",
        (row_id, project_id, REQUIREMENT, "fingerprint-before-examine", run_id),
    )
    await connection.execute(
        "INSERT INTO citations (id, register_row_id, cell_name, source_file, "
        "source_place, source_words) VALUES (%s, %s, 'what_was_asked', %s, "
        "'Discussion', %s)",
        (uuid4(), row_id, SOURCE_FILE, f"The client asked for {REQUIREMENT}."),
    )
    return row_id
