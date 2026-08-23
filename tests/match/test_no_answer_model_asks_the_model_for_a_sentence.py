from __future__ import annotations

from app.examine.examine_register import ExamineAnswer
from app.match.match_requirements import MatchAnswer, ObservationAnswer
from app.model.answer_schema import JSON_SCHEMA_FORMAT, strict_answer_format


# The sentence a person reads is built by the backend from stored data (S9),
# so no answer model may ask a model for one. These assert the contract the
# provider is actually sent — the strict schema — rather than the Python class
# alone, because the schema is what refuses a reply carrying an extra field.
ANSWER_MODELS = (MatchAnswer, ObservationAnswer, ExamineAnswer)


def test_no_answer_model_asks_for_a_question_sentence() -> None:
    for answer_model in ANSWER_MODELS:
        assert "question" not in _property_names(answer_model)


def test_every_answer_the_provider_is_asked_for_refuses_an_extra_field() -> None:
    """A reply carrying `question` is refused rather than quietly ignored.

    Without this the field could come back for a run or two after it left the
    model, and nothing would say so.
    """
    for answer_model in ANSWER_MODELS:
        for definition in _object_definitions(answer_model):
            assert definition["additionalProperties"] is False


def _property_names(answer_model: type) -> set[str]:
    return {
        name
        for definition in _object_definitions(answer_model)
        for name in definition["properties"]
    }


def _object_definitions(answer_model: type) -> list[dict]:
    schema = strict_answer_format(answer_model)[JSON_SCHEMA_FORMAT]["schema"]
    return [
        definition
        for definition in [schema, *schema.get("$defs", {}).values()]
        if "properties" in definition
    ]
