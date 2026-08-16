from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, ValidationError


class DocumentType(StrEnum):
    MEETING_NOTES = "meeting notes"
    CLIENT_REQUIREMENTS_DOCUMENT = "client requirements document"
    TESTING_FEEDBACK = "testing feedback"
    HANDOVER_SUMMARY = "handover summary"
    UNRELATED = "unrelated"


MEETING_NOTES = DocumentType.MEETING_NOTES.value
CLIENT_REQUIREMENTS_DOCUMENT = DocumentType.CLIENT_REQUIREMENTS_DOCUMENT.value
TESTING_FEEDBACK = DocumentType.TESTING_FEEDBACK.value
HANDOVER_SUMMARY = DocumentType.HANDOVER_SUMMARY.value
UNRELATED_DOCUMENT = DocumentType.UNRELATED.value
DOCUMENT_TYPES = tuple(document_type.value for document_type in DocumentType)
REQUIREMENTS = "requirements"
TESTING_OBSERVATIONS = "testing_observations"
DELIVERY_EVIDENCE = "delivery_evidence"
BLOCKERS = "blockers"
QUOTED_LISTS = (REQUIREMENTS, TESTING_OBSERVATIONS, DELIVERY_EVIDENCE, BLOCKERS)

# Which of those four lists each document type may fill at all. The prompt
# states this table and the generated schema carries it in the field
# descriptions; a filled list where the table says empty is a wrong answer
# rather than something Python quietly zeroes.
LISTS_A_TYPE_MAY_FILL: dict[DocumentType, frozenset[str]] = {
    DocumentType.MEETING_NOTES: frozenset({REQUIREMENTS, BLOCKERS}),
    DocumentType.CLIENT_REQUIREMENTS_DOCUMENT: frozenset({REQUIREMENTS, BLOCKERS}),
    DocumentType.TESTING_FEEDBACK: frozenset({TESTING_OBSERVATIONS, BLOCKERS}),
    DocumentType.HANDOVER_SUMMARY: frozenset({DELIVERY_EVIDENCE, BLOCKERS}),
    DocumentType.UNRELATED: frozenset(),
}


class TestingLabel(StrEnum):
    PASSED = "Passed"
    DEFECT = "Defect"
    # Testing looked and found nothing built. Without it neither `Not
    # delivered` nor `Disputed` can ever be reached: `Defect` means the work
    # exists and is wrong, which is the `Partial` line.
    NOT_FOUND = "Not found"
    CHANGE_REQUEST = "Change request"
    UNCLEAR = "Unclear"


TESTING_LABELS = tuple(label.value for label in TestingLabel)


class UnrecognisedDocumentType(ValueError):
    """The model reported a document type outside the declared set."""

    def __init__(self, reported_type: str) -> None:
        self.reported_type = reported_type
        super().__init__(
            f"document type not recognised — the model called it "
            f"'{reported_type}', which is not one of "
            f"{', '.join(DOCUMENT_TYPES)}"
        )


# Every field carries its own meaning as a description, because the generated
# schema is what the model is actually asked for. The prompt explains judgement
# — what a label means, what counts as a blocker — and never the shape.
_SUMMARY_MEANING = "One short sentence stating this fact in your own words."
_QUOTE_MEANING = (
    "The document's own words supporting it, copied character for character."
)


class ListTheDocumentTypeMayNotFill(ValueError):
    """The model filled a list the document type it reported may not report."""

    def __init__(self, reported_type: str, list_name: str) -> None:
        self.reported_type = reported_type
        self.list_name = list_name
        super().__init__(
            f"a '{reported_type}' may not report {list_name}, and the model "
            f"returned {list_name} on one — this document is skipped and the "
            "rest of the batch continues; if it keeps happening, name a "
            "stronger model in config/model.yaml"
        )


class QuotedFact(BaseModel):
    summary: str = Field(description=_SUMMARY_MEANING)
    quote: str = Field(description=_QUOTE_MEANING)


class QuotedTestingObservation(BaseModel):
    summary: str = Field(description=_SUMMARY_MEANING)
    label: TestingLabel = Field(
        description="Which kind of verdict testing reached about this."
    )
    quote: str = Field(description=_QUOTE_MEANING)


class QuotedInstruction(BaseModel):
    quote: str = Field(
        description=(
            "The instructing text itself, copied character for character."
        )
    )


class DocumentDate(BaseModel):
    value: str = Field(description="The date as the document writes it.")
    quote: str = Field(description=_QUOTE_MEANING)


class ExtractionAnswer(BaseModel):
    document_type: DocumentType = Field(
        description="Which kind of document this one is."
    )
    document_date: DocumentDate | None = Field(
        default=None,
        description=(
            "The date this document states about itself, or null when it "
            "states none."
        ),
    )
    requirements: list[QuotedFact] = Field(
        default_factory=list,
        description="One entry for each thing the client asked for.",
    )
    testing_observations: list[QuotedTestingObservation] = Field(
        default_factory=list,
        description="One entry for each thing testing reported about the work.",
    )
    delivery_evidence: list[QuotedFact] = Field(
        default_factory=list,
        description=(
            "One entry for each piece of work this document reports as handed "
            "over."
        ),
    )
    blockers: list[QuotedFact] = Field(
        default_factory=list,
        description=(
            "One entry for each piece of work this document says is stopped."
        ),
    )
    embedded_instructions: list[QuotedInstruction] = Field(
        default_factory=list,
        description=(
            "One entry for each line addressing whoever, or whatever, "
            "processes this document."
        ),
    )


def parse_extraction_answer(model_reply: str) -> ExtractionAnswer:
    try:
        answer = ExtractionAnswer.model_validate_json(json_object_in(model_reply))
    except ValidationError as invalid:
        # An invented type is a different problem from a malformed answer: one
        # document is skipped for a reason a person can act on, rather than
        # reported as the model failing to answer at all.
        for problem in invalid.errors():
            if problem["loc"] == ("document_type",):
                raise UnrecognisedDocumentType(str(problem["input"])) from invalid
        raise
    _refuse_a_list_this_type_may_not_fill(answer)
    return answer


def _refuse_a_list_this_type_may_not_fill(answer: ExtractionAnswer) -> None:
    """Refuse the whole answer rather than emptying the list it should not hold.

    Silently zeroing it would turn a wrong answer into a quiet one: nobody
    would learn that a testing document came back claiming to state new asks.
    """
    allowed = LISTS_A_TYPE_MAY_FILL[answer.document_type]
    filled = [name for name in QUOTED_LISTS if getattr(answer, name)]
    for list_name in filled:
        if list_name not in allowed:
            raise ListTheDocumentTypeMayNotFill(
                answer.document_type.value, list_name
            )


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
