from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, ValidationError


class DocumentType(StrEnum):
    MEETING_NOTES = "meeting notes"
    CLIENT_REQUIREMENTS_DOCUMENT = "client requirements document"
    TESTING_FEEDBACK = "testing feedback"
    RELATED_ADDITIONAL_DOCUMENT = "related additional document"
    UNRELATED = "unrelated"


MEETING_NOTES = DocumentType.MEETING_NOTES.value
CLIENT_REQUIREMENTS_DOCUMENT = DocumentType.CLIENT_REQUIREMENTS_DOCUMENT.value
TESTING_FEEDBACK = DocumentType.TESTING_FEEDBACK.value
RELATED_ADDITIONAL_DOCUMENT = DocumentType.RELATED_ADDITIONAL_DOCUMENT.value
UNRELATED_DOCUMENT = DocumentType.UNRELATED.value
DOCUMENT_TYPES = tuple(document_type.value for document_type in DocumentType)
# Only the three types the client's own workflow produces may put a row in the
# register; the other two are read for what they add to rows already there.
PRIMARY_DOCUMENT_TYPES = (
    MEETING_NOTES,
    CLIENT_REQUIREMENTS_DOCUMENT,
    TESTING_FEEDBACK,
)

TESTING_LABELS = ("Passed", "Defect", "Change request", "Unclear")


class UnrecognisedDocumentType(ValueError):
    """The model reported a document type outside the declared set."""

    def __init__(self, reported_type: str) -> None:
        self.reported_type = reported_type
        super().__init__(
            f"document type not recognised — the model called it "
            f"'{reported_type}', which is not one of "
            f"{', '.join(DOCUMENT_TYPES)}"
        )


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
    document_type: DocumentType
    document_date: DocumentDate | None = None
    requirements: list[QuotedFact] = Field(default_factory=list)
    testing_observations: list[QuotedTestingObservation] = Field(
        default_factory=list
    )
    blockers: list[QuotedFact] = Field(default_factory=list)
    embedded_instructions: list[QuotedInstruction] = Field(default_factory=list)


def parse_extraction_answer(model_reply: str) -> ExtractionAnswer:
    try:
        return ExtractionAnswer.model_validate_json(json_object_in(model_reply))
    except ValidationError as invalid:
        # An invented type is a different problem from a malformed answer: one
        # document is skipped for a reason a person can act on, rather than
        # reported as the model failing to answer at all.
        for problem in invalid.errors():
            if problem["loc"] == ("document_type",):
                raise UnrecognisedDocumentType(str(problem["input"])) from invalid
        raise


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
