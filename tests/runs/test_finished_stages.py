from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from psycopg import AsyncConnection

from app.database import build_connection_pool
from app.runs.finished_stages import ordered_finished_stages, record_stage_finished
from app.runs.list_runs import read_run_list
from app.runs.run_status import read_run_status
from app.runs.statuses import EXTRACT_STAGE, RUNNING, WAITING
from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    temporary_database,
    wait_for_run_status,
    write_script,
)
from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    extraction_answer,
    match_answer,
    match_marker,
    no_findings_answer,
    write_meeting_note,
)

# Forbidden keys: none of the payload `read_run_status` reports may carry a
# cost, a duration or a token count anywhere in it — this is the shape D16's
# dropped machinery used to add, and none of it should still exist.
FORBIDDEN_KEYS = {
    "cost_and_timing",
    "seconds",
    "prompt_tokens",
    "completion_tokens",
    "estimated_cost_usd",
    "cost_unknown_reason",
    "token_usage",
    "stage_timings",
}


def test_a_rules_only_run_never_reports_extract_or_match_as_finished(
    tmp_path: Path,
) -> None:
    source_file = "meeting-notes-10-mar.md"
    requirement = "an email to the operations team on intake form submit"
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    quote = write_meeting_note(source_folder, source_file, requirement)
    rules_config_path = tmp_path / "rules.yaml"
    rules_config_path.write_text(
        "rules:\n  - id: R1\n    text: \"Anything built must be written down.\"\n",
        encoding="utf-8",
    )
    script_path = tmp_path / "script.json"
    write_script(
        script_path,
        {
            extract_marker(source_file): extraction_answer(requirement, quote),
            match_marker(): match_answer(1),
            examine_marker(): no_findings_answer(),
        },
    )

    with temporary_database() as database_url:
        application = ApplicationProcess(
            database_url=database_url,
            script_path=script_path,
            call_log_path=tmp_path / "model-calls.jsonl",
            rules_config_path=rules_config_path,
        )
        application.start()
        try:
            with application.client() as client:
                project_id = client.post(
                    "/projects",
                    json={
                        "name": "Rules-only intake portal",
                        "source_folder_path": str(source_folder),
                    },
                ).json()["project_id"]

                # First run: reads the one document, proposes and exports a row.
                first_run = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                wait_for_run_status(client, first_run, "waiting for review")
                approve_every_decision_and_finish_review(client, first_run)
                wait_for_run_status(client, first_run, "done")

                # Second run: only the rules changed, so Ingest routes straight
                # to Examine (D03/D07). Extract and Match never execute.
                rules_config_path.write_text(
                    "rules:\n  - id: R1\n    text: \"Anything built must be "
                    "written down.\"\n  - id: R9\n    text: \"Every requirement "
                    "names the person who asked for it.\"\n",
                    encoding="utf-8",
                )
                rules_run = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                wait_for_run_status(client, rules_run, "waiting for review")
                rules_run_at_review = client.get(f"/runs/{rules_run}").json()
                approve_every_decision_and_finish_review(client, rules_run)
                wait_for_run_status(client, rules_run, "done")
                rules_run_done = client.get(f"/runs/{rules_run}").json()
        finally:
            application.stop()

    # Neither snapshot of the rules-only run — mid-review or done — ever
    # reports extract or match, because on this route they never ran.
    assert rules_run_at_review["finished_stages"] == ["ingest", "examine"]
    assert rules_run_done["finished_stages"] == [
        "ingest",
        "examine",
        "review",
        "commit",
    ]


def test_a_re_entered_extract_never_reports_extract_twice() -> None:
    finished = asyncio.run(_mark_extract_finished_twice())

    # `||` merge overwrites the key a second pass writes, so the stage is
    # reported once whether it ran once or was resumed after a kill.
    assert finished == {"ingest": True, "extract": True}
    assert ordered_finished_stages(finished) == ["ingest", "extract"]


async def _mark_extract_finished_twice() -> dict[str, Any]:
    with temporary_database() as database_url:
        pool = build_connection_pool(database_url)
        await pool.open(wait=True)
        try:
            async with pool.connection() as connection:
                project_id, run_id = await _project_with_a_running_run(connection)
                await record_stage_finished(connection, run_id, "ingest")
                await record_stage_finished(connection, run_id, EXTRACT_STAGE)
                # The kill lands after Extract wrote its mark; the resumed pass
                # writes it again rather than adding a second entry.
                await record_stage_finished(connection, run_id, EXTRACT_STAGE)
                run = await connection.execute(
                    "SELECT finished_stages FROM runs WHERE id = %s", (run_id,)
                )
                return (await run.fetchone())["finished_stages"]
        finally:
            await pool.close()


def test_a_review_still_waiting_is_never_reported_as_finished(tmp_path: Path) -> None:
    source_file = "meeting-note.md"
    requirement = "an email to the operations team on intake form submit"
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    quote = write_meeting_note(source_folder, source_file, requirement)
    script_path = tmp_path / "script.json"
    write_script(
        script_path,
        {
            extract_marker(source_file): extraction_answer(requirement, quote),
            match_marker(): match_answer(1),
            examine_marker(): no_findings_answer(),
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
                    json={
                        "name": "Waiting review intake portal",
                        "source_folder_path": str(source_folder),
                    },
                ).json()["project_id"]
                run_id = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                waiting = wait_for_run_status(client, run_id, "waiting for review")
        finally:
            application.stop()

    assert "review" not in waiting["finished_stages"]
    assert waiting["finished_stages"] == ["ingest", "extract", "match", "examine"]


def test_a_run_that_has_not_started_never_reports_a_time_it_started() -> None:
    entry = asyncio.run(_waiting_run_list_entry())

    assert entry["started_at"] is None


async def _waiting_run_list_entry() -> dict[str, Any]:
    with temporary_database() as database_url:
        pool = build_connection_pool(database_url)
        await pool.open(wait=True)
        try:
            async with pool.connection() as connection:
                project_id, run_id = await _project_with_a_waiting_run(connection)
                listed = await read_run_list(connection)
                return next(
                    run for run in listed["runs"] if run["run_id"] == str(run_id)
                )
        finally:
            await pool.close()


def test_the_status_door_never_reports_a_cost_or_a_duration() -> None:
    payload = asyncio.run(_status_of_a_fresh_run())

    assert not (_all_keys(payload) & FORBIDDEN_KEYS)


async def _status_of_a_fresh_run() -> dict[str, Any]:
    with temporary_database() as database_url:
        pool = build_connection_pool(database_url)
        await pool.open(wait=True)
        try:
            async with pool.connection() as connection:
                _project_id, run_id = await _project_with_a_running_run(connection)
                return await read_run_status(connection, run_id)
        finally:
            await pool.close()


def _all_keys(value: Any) -> set[str]:
    """Every dict key anywhere inside a JSON-shaped value, however nested."""
    found: set[str] = set()
    if isinstance(value, dict):
        found |= set(value.keys())
        for nested in value.values():
            found |= _all_keys(nested)
    elif isinstance(value, list):
        for item in value:
            found |= _all_keys(item)
    return found


async def _project_with_a_running_run(
    connection: AsyncConnection,
) -> tuple[UUID, UUID]:
    project_id, run_id = uuid4(), uuid4()
    await connection.execute(
        "INSERT INTO projects (id, name, source_folder_path) VALUES (%s, %s, %s)",
        (project_id, "Finished-stages intake portal", "/projects/intake-portal"),
    )
    await connection.execute(
        "INSERT INTO runs (id, project_id, status) VALUES (%s, %s, %s)",
        (run_id, project_id, RUNNING),
    )
    return project_id, run_id


async def _project_with_a_waiting_run(
    connection: AsyncConnection,
) -> tuple[UUID, UUID]:
    project_id, run_id = uuid4(), uuid4()
    await connection.execute(
        "INSERT INTO projects (id, name, source_folder_path) VALUES (%s, %s, %s)",
        (project_id, "Queued intake portal", "/projects/intake-portal"),
    )
    await connection.execute(
        "INSERT INTO runs (id, project_id, status) VALUES (%s, %s, %s)",
        (run_id, project_id, WAITING),
    )
    return project_id, run_id
