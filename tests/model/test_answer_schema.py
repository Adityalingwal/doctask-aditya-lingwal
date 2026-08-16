from __future__ import annotations

import asyncio
import json
from typing import Any

from app.extract.answer import DOCUMENT_TYPES, ExtractionAnswer, TESTING_LABELS
from app.extract.read_document import read_one_document
from app.model.answer_schema import strict_answer_format
from app.model.scripted_client import ScriptedChatModel


def _extraction_schema() -> dict[str, Any]:
    return strict_answer_format(ExtractionAnswer)["json_schema"]["schema"]


def _scripted_client(answer: dict[str, Any]) -> ScriptedChatModel:
    return ScriptedChatModel(
        messages=iter(()),
        script=[{"when_prompt_contains": "DOCUMENT", "answer": json.dumps(answer)}],
    )


def test_the_extraction_schema_is_generated_from_the_pydantic_model() -> None:
    schema = _extraction_schema()

    # Not one field hand-copied: whatever the model validates is what the
    # provider is asked for, so adding a field cannot leave the two disagreeing.
    assert set(schema["properties"]) == set(ExtractionAnswer.model_fields)
    assert set(schema["required"]) == set(ExtractionAnswer.model_fields)
    assert schema["additionalProperties"] is False

    format_asked_for = strict_answer_format(ExtractionAnswer)
    assert format_asked_for["type"] == "json_schema"
    assert format_asked_for["json_schema"]["strict"] is True


def test_the_generated_schema_carries_every_declared_value_and_no_default() -> None:
    schema = _extraction_schema()
    definitions = json.dumps(schema["$defs"])

    for document_type in DOCUMENT_TYPES:
        assert document_type in definitions
    for label in TESTING_LABELS:
        assert label in definitions
    # A default is how "this key may be missing" is written, and strict mode
    # refuses a schema carrying one.
    assert "default" not in json.dumps(schema)


def test_every_nested_object_in_the_schema_refuses_an_undeclared_key() -> None:
    schema = _extraction_schema()

    for name, definition in schema["$defs"].items():
        if "properties" not in definition:
            continue
        assert definition["additionalProperties"] is False, name
        assert set(definition["required"]) == set(definition["properties"]), name


def test_the_answer_still_parses_without_a_live_key() -> None:
    # The scripted client returns plain text and knows nothing about
    # response_format, so the parse path has to keep working without one.
    answer = asyncio.run(
        read_one_document(
            _scripted_client(
                {
                    "document_type": "testing feedback",
                    "requirements": [],
                    "testing_observations": [
                        {
                            "summary": "The intake form submits correctly.",
                            "label": "Passed",
                            "quote": "The intake form submits correctly",
                        }
                    ],
                    "delivery_evidence": [],
                    "embedded_instructions": [],
                }
            ),
            "testing-feedback.md",
            "The intake form submits correctly and rejects an incomplete entry.",
        )
    )

    assert answer.document_type == "testing feedback"
    assert answer.testing_observations[0].label == "Passed"
