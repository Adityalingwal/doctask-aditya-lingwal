from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, get_args

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, text

from app.match.match_requirements import (
    EXISTING_ROW,
    NEW_ROW,
    POSSIBLE_MATCH,
    IncompleteMatchAnswer,
    ObservationAnswer,
    Outcome,
    _refuse_an_incomplete_observation_answer,
    match_observations,
    match_requirements,
)
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
    observation_marker,
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
            "document_type": "meeting notes",
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


def test_an_incomplete_observation_answer_is_refused(tmp_path: Path) -> None:
    # Observations are answered under their own index, and an observation left
    # unanswered is not "no row is about it" — it is an answer never received.
    answer = ObservationAnswer.model_validate(
        {
            "outcomes": [
                {
                    "observation_index": 0,
                    "outcome": "new row",
                    "row_number": None,
                }
            ]
        }
    )

    with pytest.raises(IncompleteMatchAnswer) as refusal:
        _refuse_an_incomplete_observation_answer(answer, 2)

    assert "2 observation(s)" in str(refusal.value)
    assert "observation" in str(refusal.value)


def _observations_answered_by_the_model(
    tmp_path: Path,
    answer: dict[str, Any],
    observation_count: int,
) -> None:
    """Send a batch of observations to Match and take back the scripted answer."""
    script_path = tmp_path / "script.json"
    write_script(script_path, {observation_marker(): answer})
    model_client = build_model_client(
        MODEL_CONFIG_PATH,
        {
            MODEL_CLIENT_ENVIRONMENT_VARIABLE: SCRIPTED_CLIENT,
            SCRIPT_PATH_ENVIRONMENT_VARIABLE: str(script_path),
        },
    )
    observations = [
        {
            "kind": "testing observation",
            "summary": f"observation {index}",
            "source_file": "testing-feedback.md",
            "source_words": f"Testing reported observation {index}.",
        }
        for index in range(observation_count)
    ]
    rows = [{"row_number": 1, "what_was_asked": "an email notification"}]
    asyncio.run(match_observations(model_client, rows, observations))


def test_the_outcome_words_are_the_same_in_the_type_and_in_the_constants() -> None:
    # A Literal cannot be built out of the constants, so the three words are
    # written twice. This is what stops the two copies drifting apart.
    assert get_args(Outcome) == (NEW_ROW, EXISTING_ROW, POSSIBLE_MATCH)


def test_an_invented_outcome_is_refused_without_a_live_key(tmp_path: Path) -> None:
    # Refused either by the answer's own schema or by our content check —
    # which of the two catches it is an implementation detail, and no live key
    # is needed for either.
    answer = {
        "outcomes": [
            {
                "requirement_index": 0,
                "outcome": "merged it into row 1",
                "row_number": 1,
            }
        ]
    }

    with pytest.raises((IncompleteMatchAnswer, ValidationError)) as refusal:
        _answered_by_the_model(tmp_path, answer, 1)

    assert "merged it into row 1" in str(refusal.value)


def test_an_invented_observation_outcome_is_refused_without_a_live_key(
    tmp_path: Path,
) -> None:
    """The observation answer carries the three outcomes too, and only them.

    The two answer models are separate, so an outcome check applied to one of
    them says nothing about the other; this is the test that would still pass
    on a half-applied change only because nothing else looks at observations.
    """
    answer = {
        "outcomes": [
            {
                "observation_index": 0,
                "outcome": "attached it to row 1",
                "row_number": 1,
            }
        ]
    }

    with pytest.raises((IncompleteMatchAnswer, ValidationError)) as refusal:
        _observations_answered_by_the_model(tmp_path, answer, 1)

    assert "attached it to row 1" in str(refusal.value)


def test_new_row_naming_a_batch_index_is_refused(tmp_path: Path) -> None:
    # "new row" and "this is the same as requirement 0" are two different
    # answers, and an answer that gives both says neither.
    answer = {
        "outcomes": [
            {"requirement_index": 0, "outcome": "new row", "row_number": None},
            {
                "requirement_index": 1,
                "outcome": "new row",
                "row_number": None,
                "same_as_requirement_index": 0,
            },
        ]
    }

    with pytest.raises(IncompleteMatchAnswer) as refusal:
        _answered_by_the_model(tmp_path, answer, 2)

    assert "still named requirement 0" in str(refusal.value)


def test_an_answer_naming_both_a_row_number_and_a_batch_index_is_refused(
    tmp_path: Path,
) -> None:
    answer = {
        "outcomes": [
            {"requirement_index": 0, "outcome": "new row", "row_number": None},
            {
                "requirement_index": 1,
                "outcome": "existing row",
                "row_number": 3,
                "same_as_requirement_index": 0,
            },
        ]
    }

    with pytest.raises(IncompleteMatchAnswer) as refusal:
        _answered_by_the_model(tmp_path, answer, 2)

    assert "named both row #3 and requirement 0" in str(refusal.value)


def test_an_answer_naming_neither_for_a_match_outcome_is_refused(
    tmp_path: Path,
) -> None:
    answer = {
        "outcomes": [
            {
                "requirement_index": 0,
                "outcome": "possible match",
                "row_number": None,
                "same_as_requirement_index": None,
            }
        ]
    }

    with pytest.raises(IncompleteMatchAnswer) as refusal:
        _answered_by_the_model(tmp_path, answer, 1)

    assert "the earlier requirement in this batch it is the same as" in str(
        refusal.value
    )


def test_a_requirement_may_not_be_matched_against_a_later_requirement(
    tmp_path: Path,
) -> None:
    """Two requirements naming each other resolve to nothing at all.

    Pointing forward is refused rather than quietly reordered: the batch is a
    list, and a merge that has to be untangled before it can be read is not a
    merge anybody can check.
    """
    answer = {
        "outcomes": [
            {
                "requirement_index": 0,
                "outcome": "existing row",
                "row_number": None,
                "same_as_requirement_index": 1,
            },
            {"requirement_index": 1, "outcome": "new row", "row_number": None},
        ]
    }

    with pytest.raises(IncompleteMatchAnswer) as refusal:
        _answered_by_the_model(tmp_path, answer, 2)

    assert "requirement 1, which does not come before it" in str(refusal.value)


def test_a_batch_index_outside_this_batch_is_refused(tmp_path: Path) -> None:
    answer = {
        "outcomes": [
            {
                "requirement_index": 0,
                "outcome": "existing row",
                "row_number": None,
                "same_as_requirement_index": -1,
            }
        ]
    }

    with pytest.raises(IncompleteMatchAnswer) as refusal:
        _answered_by_the_model(tmp_path, answer, 1)

    assert "requirement -1, which is not in this batch" in str(refusal.value)
