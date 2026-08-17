from __future__ import annotations

from typing import Any, NamedTuple

from langchain_core.language_models import BaseChatModel

from app.extract.answer import ExtractionAnswer, parse_extraction_answer
from app.extract.prompt import extraction_prompt
from app.ingest.locate_quote import locate_quote
from app.ingest.place_in_document import place_finder_for
from app.model.call_the_model import call_the_model
from app.register.cells import shorten_quote
from app.runs.not_used_kinds import DROPPED_KIND


REQUIREMENT_KIND = "requirement"
TESTING_OBSERVATION_KIND = "testing observation"
DELIVERY_EVIDENCE_KIND = "delivery evidence"
EMBEDDED_INSTRUCTION_KIND = "embedded instruction"


class LocatedExtraction(NamedTuple):
    extraction: dict[str, Any]
    dropped: list[dict[str, str]]


async def read_one_document(
    model_client: BaseChatModel,
    source_file: str,
    document_text: str,
) -> ExtractionAnswer:
    answered = await call_the_model(
        model_client, extraction_prompt(source_file, document_text), ExtractionAnswer
    )
    return parse_extraction_answer(answered)


def locate_extraction(
    answer: ExtractionAnswer,
    document_text: str,
    source_file: str,
) -> LocatedExtraction:
    """Derive each quote's place from the document, dropping what is not there.

    A quote the code cannot find in the source is either invented or
    paraphrased. Either way its evidence cannot be verified, so what it
    supports is dropped rather than committed as an unsupported claim.
    """
    dropped: list[dict[str, str]] = []
    place_of = place_finder_for(source_file)

    # The entry's own kind and the kind of quote that was dropped are two
    # different things: every entry here is a dropped one, and the sentence
    # still has to name what was dropped.
    def located(summary: str, quote: str, quote_kind: str) -> dict[str, str] | None:
        location = locate_quote(document_text, quote, place_of)
        if location is None:
            dropped.append(
                {
                    "kind": DROPPED_KIND,
                    "file": source_file,
                    "summary": summary,
                    "quote": quote,
                    "reason": (
                        "These words were not found in the file, so this "
                        f"{quote_kind} was dropped."
                    ),
                }
            )
            return None
        return {
            "summary": summary,
            "source_file": source_file,
            "place": location.place,
            "source_words": shorten_quote(location.source_words),
        }

    extraction: dict[str, Any] = {
        "document_type": answer.document_type.value,
        "source_file": source_file,
        "requirements": [],
        "testing_observations": [],
        "delivery_evidence": [],
        "embedded_instructions": [],
    }

    for requirement in answer.requirements:
        found = located(requirement.summary, requirement.quote, REQUIREMENT_KIND)
        if found is not None:
            extraction["requirements"].append(found)

    for observation in answer.testing_observations:
        found = located(
            observation.summary, observation.quote, TESTING_OBSERVATION_KIND
        )
        if found is not None:
            extraction["testing_observations"].append(
                {**found, "label": observation.label.value}
            )

    for delivered in answer.delivery_evidence:
        found = located(delivered.summary, delivered.quote, DELIVERY_EVIDENCE_KIND)
        if found is not None:
            extraction["delivery_evidence"].append(found)

    for instruction in answer.embedded_instructions:
        found = located(
            instruction.quote, instruction.quote, EMBEDDED_INSTRUCTION_KIND
        )
        if found is not None:
            extraction["embedded_instructions"].append(found)

    return LocatedExtraction(extraction=extraction, dropped=dropped)
