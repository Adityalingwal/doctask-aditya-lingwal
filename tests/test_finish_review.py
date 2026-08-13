from __future__ import annotations

import asyncio
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from sqlalchemy import create_engine, text

from app.database import build_connection_pool
from app.graph.register_graph import build_register_graph
from app.model.scripted_client import build_scripted_client
from app.review.review_queue import APPROVED, answer_decision, decisions_of_run
from app.runs.run_records import claim_review_finished, read_run
from app.runs.statuses import DONE, RUNNING, WAITING_FOR_REVIEW
from conftest import (
    PROJECT_ROOT,
    ApplicationProcess,
    approve_every_decision,
    temporary_database,
    wait_for_run_status,
    write_script,
)
from register_documents import (
    examine_marker,
    extract_marker,
    extraction_answer,
    match_answer,
    match_marker,
    no_findings_answer,
    write_meeting_note,
)


SOURCE_FILE = "meeting-note.md"
REQUIREMENT = "an email to the operations team on intake form submit"
ACCEPTED_EXTENSIONS = frozenset({".md"})
PAGE_LIMIT = 20
RULES_CONFIG_PATH = PROJECT_ROOT / "config" / "rules.yaml"


@contextmanager
def _run_ready_to_finish(
    tmp_path: Path,
    project_name: str,
) -> Iterator[tuple[ApplicationProcess, str, str]]:
    """One run at Review with every decision already approved."""
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    quote = write_meeting_note(source_folder, SOURCE_FILE, REQUIREMENT)
    script_path = tmp_path / "script.json"
    write_script(
        script_path,
        {
            match_marker(): match_answer(1),
            examine_marker(): no_findings_answer(),
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
                    json={
                        "name": project_name,
                        "source_folder_path": str(source_folder),
                    },
                ).json()["project_id"]
                run_id = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                wait_for_run_status(client, run_id, "waiting for review")
                approve_every_decision(client, run_id)
            yield application, database_url, run_id
        finally:
            application.stop()


def test_finish_review_is_accepted_once(tmp_path: Path) -> None:
    with _run_ready_to_finish(tmp_path, "Twice finished intake portal") as (
        application,
        database_url,
        run_id,
    ):
        base_url = application.base_url
        # Two callers at once is the case the compare-and-set exists for: a
        # status read and a later write would let both start the graph.
        with ThreadPoolExecutor(max_workers=2) as callers:
            finishing = [
                callers.submit(_finish_review, base_url, run_id) for _ in range(2)
            ]
            answers = sorted(caller.result() for caller in finishing)

        with application.client() as client:
            wait_for_run_status(client, run_id, "done")
            export = client.get(f"/runs/{run_id}/export").json()

        engine = create_engine(database_url)
        with engine.connect() as connection:
            committed_rows = connection.execute(
                text(
                    "SELECT count(*) FROM register_rows "
                    "WHERE proposed_by_run_id = :run_id AND is_committed"
                ),
                {"run_id": run_id},
            ).scalar_one()
            audit_entries = connection.execute(
                text("SELECT count(*) FROM audit WHERE run_id = :run_id"),
                {"run_id": run_id},
            ).scalar_one()
        engine.dispose()

    assert answers == [200, 409]
    assert len(export["rows"]) == 1
    assert committed_rows == 1
    assert audit_entries == len(export["columns"])


def test_a_decision_cannot_change_after_finish_review(tmp_path: Path) -> None:
    with _run_ready_to_finish(tmp_path, "Late change intake portal") as (
        application,
        _database_url,
        run_id,
    ):
        with application.client() as client:
            export_decision = next(
                decision
                for decision in client.get(f"/runs/{run_id}").json()["decisions"]
                if decision["kind"] == "export"
            )
            finished = client.post(f"/runs/{run_id}/finish-review")
            wait_for_run_status(client, run_id, "done")
            late_change = client.post(
                f"/runs/{run_id}/decisions",
                json={
                    "decision_id": export_decision["decision_id"],
                    "outcome": "rejected",
                },
            )
            settled = client.get(f"/runs/{run_id}").json()

    assert finished.status_code == 200
    assert late_change.status_code == 409
    assert "not at review" in late_change.json()["detail"]
    assert [decision["outcome"] for decision in settled["decisions"]] == ["approved"]


def test_decision_refused_after_review_finished_even_if_status_regresses(
    tmp_path: Path,
) -> None:
    """submit_decision must refuse on the finished fact, not on status alone.

    Status is exactly what the replay bug corrupts (see
    test_finished_review_does_not_reopen_on_resume in this file), so a guard
    that reads only status would still accept a decision during that window.
    Forcing that same corrupted status by hand, on a run whose review has
    genuinely finished, proves the durable review_finished_at guard is what
    refuses it — not a status value that a bug could put back.
    """
    with _run_ready_to_finish(tmp_path, "Regressed status intake portal") as (
        application,
        database_url,
        run_id,
    ):
        with application.client() as client:
            export_decision = next(
                decision
                for decision in client.get(f"/runs/{run_id}").json()["decisions"]
                if decision["kind"] == "export"
            )
            finished = client.post(f"/runs/{run_id}/finish-review")
            wait_for_run_status(client, run_id, "done")

            engine = create_engine(database_url)
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "UPDATE runs SET status = :status WHERE id = :run_id"
                    ),
                    {"status": WAITING_FOR_REVIEW, "run_id": run_id},
                )
            engine.dispose()

            regressed = client.post(
                f"/runs/{run_id}/decisions",
                json={
                    "decision_id": export_decision["decision_id"],
                    "outcome": "rejected",
                },
            )

    assert finished.status_code == 200
    assert regressed.status_code == 409
    assert "review" in regressed.json()["detail"]
    assert "finished" in regressed.json()["detail"]


def test_finished_review_does_not_reopen_on_resume(tmp_path: Path) -> None:
    """A crash-and-restart resume must never replay Review's pre-interrupt work.

    LangGraph replays an interrupted node from its start on any resume that
    carries no cached answer — exactly what resume_unfinished_runs does after
    a killed process restarts (it calls ainvoke(None, ...)). Calling that
    directly, right after the review has genuinely finished, reproduces the
    crash-resume replay deterministically, with no process kill and no race.
    """
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    quote = write_meeting_note(source_folder, SOURCE_FILE, REQUIREMENT)
    script_path = tmp_path / "script.json"
    write_script(
        script_path,
        {
            match_marker(): match_answer(1),
            examine_marker(): no_findings_answer(),
            extract_marker(SOURCE_FILE): extraction_answer(REQUIREMENT, quote),
        },
    )

    run = asyncio.run(_drive_review_replay(source_folder, script_path))

    assert run["status"] == DONE


async def _drive_review_replay(
    source_folder: Path,
    script_path: Path,
) -> dict[str, Any]:
    with temporary_database() as database_url:
        pool = build_connection_pool(database_url)
        await pool.open(wait=True)
        try:
            checkpointer = AsyncPostgresSaver(pool)
            await checkpointer.setup()
            model_client = build_scripted_client(script_path, None, 0.0)
            graph = build_register_graph(
                model_client,
                pool,
                checkpointer,
                PROJECT_ROOT,
                ACCEPTED_EXTENSIONS,
                PAGE_LIMIT,
                RULES_CONFIG_PATH,
            )

            project_id, run_id = uuid4(), uuid4()
            async with pool.connection() as connection:
                await connection.execute(
                    "INSERT INTO projects (id, name, source_folder_path) "
                    "VALUES (%s, %s, %s)",
                    (
                        project_id,
                        "Review replay intake portal",
                        str(source_folder),
                    ),
                )
                await connection.execute(
                    "INSERT INTO runs (id, project_id, status) VALUES (%s, %s, %s)",
                    (run_id, project_id, RUNNING),
                )

            configuration = {"configurable": {"thread_id": str(run_id)}}
            await graph.ainvoke(
                {"run_id": str(run_id), "project_id": str(project_id)},
                configuration,
            )

            async with pool.connection() as connection:
                waiting = await read_run(connection, run_id)
                assert waiting["status"] == WAITING_FOR_REVIEW
                for decision in await decisions_of_run(connection, run_id):
                    await answer_decision(
                        connection, run_id, decision["id"], APPROVED
                    )
                claimed = await claim_review_finished(connection, run_id)
                assert claimed is not None

            # What resume_unfinished_runs does for a run left at RUNNING with
            # an existing checkpoint: continue the same thread with no resume
            # value, i.e. ainvoke(None, ...) — not Command(resume=...).
            await graph.ainvoke(None, configuration)

            async with pool.connection() as connection:
                return await read_run(connection, run_id)
        finally:
            await pool.close()


def _finish_review(base_url: str, run_id: str) -> int:
    with httpx.Client(base_url=base_url, timeout=30) as client:
        return client.post(f"/runs/{run_id}/finish-review").status_code
