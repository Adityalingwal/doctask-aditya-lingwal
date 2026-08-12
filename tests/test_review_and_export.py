from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, text

from conftest import (
    ApplicationProcess,
    temporary_database,
    wait_until,
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
def _application_at_review(
    tmp_path: Path,
    project_name: str,
) -> Iterator[tuple[ApplicationProcess, str, str]]:
    """One run driven through the API until it is parked at Review."""
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
                wait_until(
                    lambda: client.get(f"/runs/{run_id}").json()["status"]
                    == "waiting for review",
                    "the run reaches Review",
                )
            yield application, database_url, run_id
        finally:
            application.stop()


def test_approved_run_exports_the_register(tmp_path: Path) -> None:
    with _application_at_review(tmp_path, "Approved intake portal") as (
        application,
        database_url,
        run_id,
    ):
        with application.client() as client:
            waiting = client.get(f"/runs/{run_id}").json()
            export_decision = next(
                decision
                for decision in waiting["decisions"]
                if decision["kind"] == "export"
            )
            assert export_decision["outcome"] is None

            answered = client.post(
                f"/runs/{run_id}/decisions",
                json={
                    "decision_id": export_decision["decision_id"],
                    "outcome": "approved",
                },
            )
            assert answered.status_code == 200

            finished = client.post(f"/runs/{run_id}/finish-review")
            assert finished.status_code == 200

            wait_until(
                lambda: client.get(f"/runs/{run_id}").json()["status"] == "done",
                "the approved run commits",
            )
            export = client.get(f"/runs/{run_id}/export").json()
            markdown = client.get(
                f"/runs/{run_id}/export", params={"format": "markdown"}
            ).text

        engine = create_engine(database_url)
        with engine.connect() as connection:
            committed_fingerprints = (
                connection.execute(
                    text(
                        "SELECT fingerprint FROM register_rows "
                        "WHERE proposed_by_run_id = :run_id AND is_committed"
                    ),
                    {"run_id": run_id},
                )
                .scalars()
                .all()
            )
            audited_cells = (
                connection.execute(
                    text("SELECT cell_name FROM audit WHERE run_id = :run_id"),
                    {"run_id": run_id},
                )
                .scalars()
                .all()
            )
        engine.dispose()

    assert [row["cells"]["what_was_asked"] for row in export["rows"]] == [REQUIREMENT]
    assert export["rows"][0]["cells"]["status"] == "No evidence yet"
    what_was_asked_citation = next(
        citation
        for citation in export["rows"][0]["citations"]
        if citation["cell"] == "what_was_asked"
    )
    assert what_was_asked_citation["source_file"] == SOURCE_FILE
    assert what_was_asked_citation["place"] == "Discussion"
    assert REQUIREMENT in what_was_asked_citation["source_words"]
    assert REQUIREMENT in markdown
    assert len(committed_fingerprints) == 1
    assert committed_fingerprints[0]
    assert sorted(audited_cells) == sorted(export["columns"])


def test_finish_review_refused_while_a_decision_is_pending(tmp_path: Path) -> None:
    with _application_at_review(tmp_path, "Pending intake portal") as (
        application,
        _database_url,
        run_id,
    ):
        with application.client() as client:
            waiting = client.get(f"/runs/{run_id}").json()
            unanswered = [
                decision
                for decision in waiting["decisions"]
                if decision["outcome"] is None
            ]

            refusal = client.post(f"/runs/{run_id}/finish-review")
            after_refusal = client.get(f"/runs/{run_id}").json()
            export_attempt = client.get(f"/runs/{run_id}/export")

    assert unanswered
    assert refusal.status_code == 409
    for decision in unanswered:
        assert decision["decision_id"] in refusal.json()["detail"]
        assert decision["question"] in refusal.json()["detail"]
    assert after_refusal["status"] == "waiting for review"
    assert after_refusal["exported"] is False
    assert export_attempt.status_code == 409
