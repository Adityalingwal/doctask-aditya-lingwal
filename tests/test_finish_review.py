from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

from conftest import (
    ApplicationProcess,
    approve_every_decision,
    temporary_database,
    wait_for_run_status,
    write_script,
)
from register_documents import (
    extract_marker,
    extraction_answer,
    match_answer,
    match_marker,
    write_meeting_note,
)


SOURCE_FILE = "meeting-note.md"
REQUIREMENT = "an email to the operations team on intake form submit"


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


def _finish_review(base_url: str, run_id: str) -> int:
    with httpx.Client(base_url=base_url, timeout=30) as client:
        return client.post(f"/runs/{run_id}/finish-review").status_code
