from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from app.examine.examine_register import EXAMINE_PROMPT_MARKER
from tests.runs.application import (
    ApplicationProcess,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)
from tests.examine.answers import examine_answer, one_finding
from tests.documents.register_documents import (
    extract_marker,
    extraction_answer,
    match_answer,
    match_marker,
    write_meeting_note,
)


SOURCE_FILE = "meeting-note.md"
REQUIREMENT = "an email to the operations team on intake form submit"
# What the person reads on the button, and what the recorded decision keeps as
# the question they answered.
EXPORT_QUESTION = "Add this run's changes to the register?"


@contextmanager
def _run_at_review_with_one_finding(
    tmp_path: Path,
) -> Iterator[tuple[ApplicationProcess, str, str, str]]:
    """One run parked at Review with a finding waiting — a real question of its own.

    A finding rather than nothing at all, because the export gate is no longer
    a queue question: without one the queue would be empty and neither the
    refusal nor the count would have anything to be about.
    """
    with temporary_project_folder("one-press") as (source_folder, source_folder_path):
        quote = write_meeting_note(source_folder, SOURCE_FILE, REQUIREMENT)
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                match_marker(): match_answer(1),
                EXAMINE_PROMPT_MARKER: examine_answer([one_finding()]),
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
                    wait_for_run_status(client, run_id, "needs review")
                yield application, database_url, project_id, run_id
            finally:
                application.stop()


def test_entering_review_raises_no_export_decision_and_leaves_only_the_runs_own_questions(
    tmp_path: Path,
) -> None:
    with _run_at_review_with_one_finding(tmp_path) as (
        application,
        database_url,
        _project_id,
        run_id,
    ):
        with application.client() as client:
            waiting = client.get(f"/runs/{run_id}").json()
            refusal = client.post(
                f"/runs/{run_id}/finish-review", json={"add_to_register": True}
            )

        stored_kinds = _decision_kinds(database_url, run_id)

    assert [decision["kind"] for decision in waiting["decisions"]] == ["finding"]
    assert stored_kinds == ["finding"]
    # The one unanswered question is the finding, and the refusal counts it
    # alone — no gate is hiding in the queue behind it.
    assert refusal.status_code == 409
    assert "1 decision(s) are unanswered" in refusal.json()["detail"]
    assert waiting["decisions"][0]["decision_id"] in refusal.json()["detail"]


def test_one_press_adding_this_runs_changes_commits_them_and_records_the_answer(
    tmp_path: Path,
) -> None:
    with _run_at_review_with_one_finding(tmp_path) as (
        application,
        database_url,
        project_id,
        run_id,
    ):
        with application.client() as client:
            _approve_the_finding(client, run_id)
            finished = client.post(
                f"/runs/{run_id}/finish-review", json={"add_to_register": True}
            )
            wait_for_run_status(client, run_id, "done")
            register = client.get(f"/projects/{project_id}/register").json()

        recorded = _export_decision(database_url, run_id)

    assert finished.status_code == 200
    assert [row["cells"]["what_was_asked"] for row in register["rows"]] == [REQUIREMENT]
    # The audit still shows what the person answered, on the question they read.
    assert recorded["kind"] == "export"
    assert recorded["question"] == EXPORT_QUESTION
    assert recorded["outcome"] == "approved"
    assert recorded["decided_at"] is not None


def test_one_press_discarding_this_runs_changes_commits_nothing_and_ends_the_run_discarded(
    tmp_path: Path,
) -> None:
    with _run_at_review_with_one_finding(tmp_path) as (
        application,
        database_url,
        project_id,
        run_id,
    ):
        with application.client() as client:
            _approve_the_finding(client, run_id)
            finished = client.post(
                f"/runs/{run_id}/finish-review", json={"add_to_register": False}
            )
            wait_for_run_status(client, run_id, "discarded")
            register_after_discard = client.get(f"/projects/{project_id}/register")

        recorded = _export_decision(database_url, run_id)
        committed = _committed_row_count(database_url, run_id)

    assert finished.status_code == 200
    assert committed == 0
    # The register answers exactly as it does when nothing has ever committed:
    # the empty state, never an error.
    assert register_after_discard.status_code == 200
    assert register_after_discard.json()["rows"] == []
    assert recorded["question"] == EXPORT_QUESTION
    assert recorded["outcome"] == "rejected"


def test_finishing_a_review_without_saying_which_answer_names_the_cause_and_the_fix(
    tmp_path: Path,
) -> None:
    with _run_at_review_with_one_finding(tmp_path) as (
        application,
        _database_url,
        _project_id,
        run_id,
    ):
        with application.client() as client:
            _approve_the_finding(client, run_id)
            refusal = client.post(f"/runs/{run_id}/finish-review")
            after_refusal = client.get(f"/runs/{run_id}").json()

    assert refusal.status_code == 400
    detail = refusal.json()["detail"]
    assert "add_to_register" in detail
    assert "discard" in detail
    assert after_refusal["status"] == "needs review"


def _approve_the_finding(client: Any, run_id: str) -> None:
    finding = next(
        decision
        for decision in client.get(f"/runs/{run_id}").json()["decisions"]
        if decision["kind"] == "finding"
    )
    client.post(
        f"/runs/{run_id}/decisions",
        json={"decision_id": finding["decision_id"], "outcome": "approved"},
    ).raise_for_status()


def _decision_kinds(database_url: str, run_id: str) -> list[str]:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return list(
                connection.execute(
                    text("SELECT kind FROM decisions WHERE run_id = :run_id"),
                    {"run_id": run_id},
                )
                .scalars()
                .all()
            )
    finally:
        engine.dispose()


def _export_decision(database_url: str, run_id: str) -> dict[str, Any]:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return dict(
                connection.execute(
                    text(
                        "SELECT kind, question, outcome, decided_at FROM decisions "
                        "WHERE run_id = :run_id AND kind = 'export'"
                    ),
                    {"run_id": run_id},
                )
                .mappings()
                .one()
            )
    finally:
        engine.dispose()


def _committed_row_count(database_url: str, run_id: str) -> int:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return connection.execute(
                text(
                    "SELECT count(*) FROM register_rows "
                    "WHERE proposed_by_run_id = :run_id AND is_committed"
                ),
                {"run_id": run_id},
            ).scalar_one()
    finally:
        engine.dispose()
