from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError


MEETING_NOTES = "meeting notes"
CLIENT_REQUIREMENTS_DOCUMENT = "client requirements document"
TESTING_FEEDBACK = "testing feedback"
RELATED_ADDITIONAL_DOCUMENT = "related additional document"
UNRELATED_DOCUMENT = "unrelated"
DOCUMENT_TYPES = (
    MEETING_NOTES,
    CLIENT_REQUIREMENTS_DOCUMENT,
    TESTING_FEEDBACK,
    RELATED_ADDITIONAL_DOCUMENT,
    UNRELATED_DOCUMENT,
)

TESTING_LABELS = ("Passed", "Defect", "Change request", "Unclear")


class QuotedFact(BaseModel):
    summary: str
    quote: str


class QuotedTestingObservation(BaseModel):
    summary: str
    label: str
    quote: str


class QuotedInstruction(BaseModel):
    quote: str


class DocumentDate(BaseModel):
    value: str
    quote: str


class ExtractionAnswer(BaseModel):
    document_type: str
    document_date: DocumentDate | None = None
    requirements: list[QuotedFact] = Field(default_factory=list)
    testing_observations: list[QuotedTestingObservation] = Field(
        default_factory=list
    )
    blockers: list[QuotedFact] = Field(default_factory=list)
    embedded_instructions: list[QuotedInstruction] = Field(default_factory=list)


def parse_extraction_answer(model_reply: str) -> ExtractionAnswer:
    return ExtractionAnswer.model_validate_json(json_object_in(model_reply))


def json_object_in(model_reply: str) -> str:
    """Take the JSON object out of a reply that may be wrapped in prose."""
    opening = model_reply.find("{")
    closing = model_reply.rfind("}")
    if opening < 0 or closing <= opening:
        raise ValueError(
            "the model reply contained no JSON object — the prompt asks for "
            "JSON only, so this reply cannot be read"
        )
    return model_reply[opening : closing + 1]


def describe_unreadable_answer(error: Exception) -> str:
    if isinstance(error, ValidationError):
        first_problem = error.errors()[0]
        location = ".".join(str(part) for part in first_problem["loc"])
        return (
            f"the model's answer did not match the expected shape at "
            f"'{location}' ({first_problem['msg']})"
        )
    if isinstance(error, ValueError):
        return str(error)
    return f"{type(error).__name__}: {error}"
