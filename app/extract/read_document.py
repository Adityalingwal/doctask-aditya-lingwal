from __future__ import annotations

from typing import Any, NamedTuple

from langchain_core.language_models import BaseChatModel

from app.extract.answer import ExtractionAnswer, parse_extraction_answer
from app.extract.prompt import extraction_prompt
from app.ingest.locate_quote import locate_quote
from app.ingest.place_in_document import place_finder_for
from app.model.call_the_model import call_the_model
from app.register.cells import shorten_quote
from app.runs.skipped_kinds import NOT_ATTACHED_KIND



class LocatedExtraction(NamedTuple):
    extraction: dict[str, Any]
    dropped: list[dict[str, Any]]


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
    dropped: list[dict[str, Any]] = []
    place_of = place_finder_for(source_file)

    # `source_line` is null and stays null: the words are not in the file, so
    # there is no place to name, and the reason names the file instead (S12).
    def located(summary: str, quote: str) -> dict[str, str] | None:
        location = locate_quote(document_text, quote, place_of)
        if location is None:
            dropped.append(
                {
                    "kind": NOT_ATTACHED_KIND,
                    "file": source_file,
                    "summary": summary,
                    "quote": quote,
                    "source_line": None,
                    "reason": (
                        f"The model said this comes from {source_file}, but "
                        "those words are not in the file."
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
        found = located(requirement.summary, requirement.quote)
        if found is not None:
            extraction["requirements"].append(found)

    for observation in answer.testing_observations:
        found = located(observation.summary, observation.quote)
        if found is not None:
            extraction["testing_observations"].append(
                {**found, "label": observation.label.value}
            )

    for delivered in answer.delivery_evidence:
        found = located(delivered.summary, delivered.quote)
        if found is not None:
            extraction["delivery_evidence"].append(found)

    for instruction in answer.embedded_instructions:
        found = located(instruction.quote, instruction.quote)
        if found is not None:
            extraction["embedded_instructions"].append(found)

    return LocatedExtraction(extraction=extraction, dropped=dropped)
