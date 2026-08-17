from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from tests.runs.application import (
    ApplicationProcess,
    temporary_database,
    temporary_project_folder,
    wait_until,
    write_script,
)
from tests.examine.answers import examine_answer, one_finding
from tests.documents.register_documents import (
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


@contextmanager
def _application_at_review(
    tmp_path: Path,
    examine: dict[str, Any] | None = None,
) -> Iterator[tuple[ApplicationProcess, str, str]]:
    """One run driven through the API until it is parked at Review.

    `examine` decides whether the run reaches Review with a question of its
    own: the export gate is no longer one, so a test about an unanswered
    decision has to give the run a real finding to leave unanswered.
    """
    with temporary_project_folder("review-export") as (source_folder, source_folder_path):
        quote = write_meeting_note(source_folder, SOURCE_FILE, REQUIREMENT)
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                match_marker(): match_answer(1),
                examine_marker(): examine or no_findings_answer(),
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
                yield application, database_url, run_id
            finally:
                application.stop()


def test_approved_run_exports_the_register(tmp_path: Path) -> None:
    with _application_at_review(tmp_path) as (
        application,
        database_url,
        run_id,
    ):
        with application.client() as client:
            waiting = client.get(f"/runs/{run_id}").json()
            # The gate is not in the queue: one press writes it and ends the
            # review in the same step.
            assert waiting["decisions"] == []

            finished = client.post(
                f"/runs/{run_id}/finish-review",
                json={"add_to_register": True},
            )
            assert finished.status_code == 200

            export_decision = next(
                decision
                for decision in client.get(f"/runs/{run_id}").json()["decisions"]
                if decision["kind"] == "export"
            )
            assert export_decision["outcome"] == "approved"

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
    assert export["rows"][0]["cells"]["status"] == "Nothing said yet"
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
    with _application_at_review(
        tmp_path,
        examine_answer([one_finding()]),
    ) as (
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

            refusal = client.post(
                f"/runs/{run_id}/finish-review",
                json={"add_to_register": True},
            )
            after_refusal = client.get(f"/runs/{run_id}").json()
            export_attempt = client.get(f"/runs/{run_id}/export")

    assert unanswered
    assert refusal.status_code == 409
    for decision in unanswered:
        assert decision["decision_id"] in refusal.json()["detail"]
        assert decision["question"] in refusal.json()["detail"]
    assert after_refusal["status"] == "needs review"
    assert after_refusal["exported"] is False
    assert export_attempt.status_code == 409


def test_requirement_whose_quote_is_not_in_the_document_never_reaches_a_row(
    tmp_path: Path,
) -> None:
    with temporary_project_folder("paraphrased") as (source_folder, source_folder_path):
        quote = write_meeting_note(source_folder, SOURCE_FILE, REQUIREMENT)
        paraphrased = "the client wants search on old records"
        answer = extraction_answer(REQUIREMENT, quote)
        answer["requirements"].append(
            {"summary": "Search over old intake records", "quote": paraphrased}
        )
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                match_marker(): match_answer(1),
                examine_marker(): no_findings_answer(),
                extract_marker(SOURCE_FILE): answer,
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
                    status = wait_until(
                        lambda: (
                            client.get(f"/runs/{run_id}").json()
                            if client.get(f"/runs/{run_id}").json()["status"]
                            == "needs review"
                            else None
                        ),
                        "the run reaches Review",
                    )
            finally:
                application.stop()

            engine = create_engine(database_url)
            with engine.connect() as connection:
                proposed = (
                    connection.execute(
                        text(
                            "SELECT what_was_asked FROM register_rows "
                            "WHERE proposed_by_run_id = :run_id"
                        ),
                        {"run_id": run_id},
                    )
                    .scalars()
                    .all()
                )
            engine.dispose()

    # The paraphrase cannot be verified against the source, so no row carries it.
    assert list(proposed) == [REQUIREMENT]
    dropped = [entry for entry in status["skipped"] if entry["kind"] == "requirement"]
    assert len(dropped) == 1
    assert dropped[0]["file"] == SOURCE_FILE
    assert dropped[0]["quote"] == paraphrased
    assert dropped[0]["reason"] == (
        "These words were not found in the file, so this requirement was dropped."
    )
