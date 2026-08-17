from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from app.match.match_requirements import (
    IncompleteMatchAnswer,
    match_observations,
    match_requirements,
)
from app.model.client import (
    MODEL_CLIENT_ENVIRONMENT_VARIABLE,
    SCRIPTED_CLIENT,
    build_model_client,
)
from app.model.scripted_client import SCRIPT_PATH_ENVIRONMENT_VARIABLE
from tests.runs.application import PROJECT_ROOT, write_script
from tests.documents.register_documents import match_marker, observation_marker


MODEL_CONFIG_PATH = PROJECT_ROOT / "config" / "model.yaml"
REGISTER_ROWS = [{"row_number": 1, "what_was_asked": "an email notification"}]
A_QUESTION = (
    "This ask was raised in meeting notes (meeting-notes-10-mar.md) — row #1. "
    "It is now also written in the client requirements document "
    "(client-requirements-v2.md). Is this the same ask?"
)
AN_OBSERVATION_QUESTION = (
    "Testing feedback (testing-feedback-12-may.md) says: 'the reply suggestion "
    "appears and can be edited'. Is this about row #1 — an email notification?"
)


def _client(tmp_path: Path, marker: str, answer: dict[str, Any]) -> Any:
    script_path = tmp_path / "script.json"
    write_script(script_path, {marker: answer})
    return build_model_client(
        MODEL_CONFIG_PATH,
        {
            MODEL_CLIENT_ENVIRONMENT_VARIABLE: SCRIPTED_CLIENT,
            SCRIPT_PATH_ENVIRONMENT_VARIABLE: str(script_path),
        },
    )


def _match(tmp_path: Path, outcomes: list[dict[str, Any]]) -> None:
    model_client = _client(tmp_path, match_marker(), {"outcomes": outcomes})
    requirements = [
        {
            "summary": f"requirement {index}",
            "source_file": "meeting-note.md",
            "source_words": f"The client asked for requirement {index}.",
            "document_type": "meeting notes",
        }
        for index in range(len(outcomes))
    ]
    asyncio.run(match_requirements(model_client, REGISTER_ROWS, requirements))


def _match_observations(tmp_path: Path, outcomes: list[dict[str, Any]]) -> None:
    model_client = _client(tmp_path, observation_marker(), {"outcomes": outcomes})
    observations = [
        {
            "kind": "testing observation",
            "summary": f"observation {index}",
            "source_file": "testing-feedback.md",
            "source_words": f"Testing reported observation {index}.",
        }
        for index in range(len(outcomes))
    ]
    asyncio.run(match_observations(model_client, REGISTER_ROWS, observations))


@pytest.mark.parametrize("outcome", ["existing row", "possible match"])
def test_a_requirement_matched_to_a_register_row_without_a_question_is_refused(
    tmp_path: Path,
    outcome: str,
) -> None:
    """Certainty does not settle it: a named register row is always a decision.

    A confident 'existing row' against a committed row is downgraded into a
    possible match before the decision is raised, so both outcomes reach the
    same card and both need the sentence the person will read.
    """
    with pytest.raises(IncompleteMatchAnswer) as refusal:
        _match(
            tmp_path,
            [{"requirement_index": 0, "outcome": outcome, "row_number": 1}],
        )

    assert "row #1" in str(refusal.value)
    assert "question" in str(refusal.value)


def test_a_possible_match_inside_this_batch_without_a_question_is_refused(
    tmp_path: Path,
) -> None:
    """No row exists yet, and the person is still asked whether it is one ask."""
    with pytest.raises(IncompleteMatchAnswer) as refusal:
        _match(
            tmp_path,
            [
                {"requirement_index": 0, "outcome": "new row", "row_number": None},
                {
                    "requirement_index": 1,
                    "outcome": "possible match",
                    "row_number": None,
                    "same_as_requirement_index": 0,
                },
            ],
        )

    assert "possible match" in str(refusal.value)
    assert "question" in str(refusal.value)


def test_a_new_row_carrying_a_question_is_refused(tmp_path: Path) -> None:
    """Nothing is put to a person, so a sentence written for one is invented."""
    with pytest.raises(IncompleteMatchAnswer) as refusal:
        _match(
            tmp_path,
            [
                {
                    "requirement_index": 0,
                    "outcome": "new row",
                    "row_number": None,
                    "question": A_QUESTION,
                }
            ],
        )

    assert "question" in str(refusal.value)
    assert "new row" in str(refusal.value)


def test_a_confident_match_inside_this_batch_carrying_a_question_is_refused(
    tmp_path: Path,
) -> None:
    """That one merges with no decision raised, so it carries no sentence."""
    with pytest.raises(IncompleteMatchAnswer) as refusal:
        _match(
            tmp_path,
            [
                {"requirement_index": 0, "outcome": "new row", "row_number": None},
                {
                    "requirement_index": 1,
                    "outcome": "existing row",
                    "row_number": None,
                    "same_as_requirement_index": 0,
                    "question": A_QUESTION,
                },
            ],
        )

    assert "question" in str(refusal.value)


@pytest.mark.parametrize("outcome", ["existing row", "possible match"])
def test_an_observation_about_a_register_row_without_a_question_is_refused(
    tmp_path: Path,
    outcome: str,
) -> None:
    with pytest.raises(IncompleteMatchAnswer) as refusal:
        _match_observations(
            tmp_path,
            [{"observation_index": 0, "outcome": outcome, "row_number": 1}],
        )

    assert "row #1" in str(refusal.value)
    assert "question" in str(refusal.value)


def test_an_observation_about_no_register_row_carrying_a_question_is_refused(
    tmp_path: Path,
) -> None:
    with pytest.raises(IncompleteMatchAnswer) as refusal:
        _match_observations(
            tmp_path,
            [
                {
                    "observation_index": 0,
                    "outcome": "new row",
                    "row_number": None,
                    "question": AN_OBSERVATION_QUESTION,
                }
            ],
        )

    assert "question" in str(refusal.value)
    assert "new row" in str(refusal.value)


def test_a_match_naming_a_register_row_with_its_question_is_accepted(
    tmp_path: Path,
) -> None:
    """The refusals must not swallow the answer they exist to require."""
    _match(
        tmp_path,
        [
            {
                "requirement_index": 0,
                "outcome": "possible match",
                "row_number": 1,
                "question": A_QUESTION,
            }
        ],
    )
    _match_observations(
        tmp_path,
        [
            {
                "observation_index": 0,
                "outcome": "existing row",
                "row_number": 1,
                "question": AN_OBSERVATION_QUESTION,
            }
        ],
    )
