from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, text

from app.match.match_requirements import IncompleteMatchAnswer, match_requirements
from app.model.client import (
    MODEL_CLIENT_ENVIRONMENT_VARIABLE,
    SCRIPTED_CLIENT,
    build_model_client,
)
from app.model.scripted_client import SCRIPT_PATH_ENVIRONMENT_VARIABLE
from tests.runs.application import (
    ApplicationProcess,
    PROJECT_ROOT,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)
from tests.documents.register_documents import (
    extract_marker,
    extraction_answer,
    match_marker,
    write_meeting_note,
)


MODEL_CONFIG_PATH = PROJECT_ROOT / "config" / "model.yaml"
DOCUMENTS = {
    "doc-1.md": "an email to the operations team on intake form submit",
    "doc-2.md": "the same notification sent over WhatsApp",
    "doc-3.md": "search over old intake records",
}


def _answered_by_the_model(
    tmp_path: Path,
    answer: dict[str, Any],
    requirement_count: int,
) -> None:
    """Send a batch of requirements to Match and take back the scripted answer."""
    script_path = tmp_path / "script.json"
    write_script(script_path, {match_marker(): answer})
    model_client = build_model_client(
        MODEL_CONFIG_PATH,
        {
            MODEL_CLIENT_ENVIRONMENT_VARIABLE: SCRIPTED_CLIENT,
            SCRIPT_PATH_ENVIRONMENT_VARIABLE: str(script_path),
        },
    )
    requirements = [
        {
            "summary": f"requirement {index}",
            "source_file": "meeting-note.md",
            "source_words": f"The client asked for requirement {index}.",
        }
        for index in range(requirement_count)
    ]
    asyncio.run(match_requirements(model_client, [], requirements))


def test_an_empty_match_answer_is_refused_instead_of_proposing_every_row_as_new(
    tmp_path: Path,
) -> None:
    with pytest.raises(IncompleteMatchAnswer) as refusal:
        _answered_by_the_model(tmp_path, {"outcomes": []}, 3)

    assert "answered for []" in str(refusal.value)
    assert "config/model.yaml" in str(refusal.value)


def test_a_requirement_answered_twice_is_refused(tmp_path: Path) -> None:
    answer = {
        "outcomes": [
            {"requirement_index": 0, "outcome": "new row", "row_number": None},
            {"requirement_index": 0, "outcome": "new row", "row_number": None},
        ]
    }

    with pytest.raises(IncompleteMatchAnswer) as refusal:
        _answered_by_the_model(tmp_path, answer, 1)

    assert "answered twice for requirement 0" in str(refusal.value)


def test_an_existing_row_answered_without_a_row_number_is_refused(
    tmp_path: Path,
) -> None:
    answer = {
        "outcomes": [
            {"requirement_index": 0, "outcome": "existing row", "row_number": None}
        ]
    }

    with pytest.raises(IncompleteMatchAnswer) as refusal:
        _answered_by_the_model(tmp_path, answer, 1)

    assert "without naming the register row it matched" in str(refusal.value)


def test_an_incomplete_match_answer_fails_the_run_and_proposes_nothing(
    tmp_path: Path,
) -> None:
    with temporary_project_folder("incomplete-match") as (source_folder, source_folder_path):
        script_path = tmp_path / "script.json"
        # The answer leaves out requirement 0, which today would have become a
        # confident new row nobody asked about.
        answers: dict[str, Any] = {
            match_marker(): {
                "outcomes": [
                    {"requirement_index": 1, "outcome": "new row", "row_number": None},
                    {"requirement_index": 2, "outcome": "new row", "row_number": None},
                ]
            }
        }
        for source_file, requirement in DOCUMENTS.items():
            quote = write_meeting_note(source_folder, source_file, requirement)
            answers[extract_marker(source_file)] = extraction_answer(requirement, quote)
        write_script(script_path, answers)

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
                    failed = wait_for_run_status(client, run_id, "failed")
                    # A failed run holds nothing, so the project takes another run.
                    after_failure = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()

                # The same input would fail the same way, so startup resume must
                # leave this run alone — only a killed 'running' run is taken over.
                application.stop()
                application.start()
                with application.client() as client:
                    after_restart = client.get(f"/runs/{run_id}").json()
            finally:
                application.stop()

            engine = create_engine(database_url)
            with engine.connect() as connection:
                proposed = connection.execute(
                    text(
                        "SELECT count(*) FROM register_rows "
                        "WHERE proposed_by_run_id = :run_id"
                    ),
                    {"run_id": run_id},
                ).scalar_one()
            engine.dispose()

    assert proposed == 0
    assert failed["exported"] is False
    assert "answered for [1, 2]" in failed["failure_reason"]
    assert "This run will not restart by itself." in failed["failure_reason"]
    assert after_failure["status"] == "running"
    assert after_restart["status"] == "failed"
