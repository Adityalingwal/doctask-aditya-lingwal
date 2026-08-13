from __future__ import annotations

from typing import Any, NamedTuple

from langchain_core.language_models import BaseChatModel

from app.extract.answer import ExtractionAnswer, parse_extraction_answer
from app.extract.prompt import extraction_prompt
from app.ingest.locate_quote import locate_quote
from app.register.cells import shorten_quote


REQUIREMENT_KIND = "requirement"
TESTING_OBSERVATION_KIND = "testing observation"
BLOCKER_KIND = "blocker"
EMBEDDED_INSTRUCTION_KIND = "embedded instruction"
DOCUMENT_DATE_KIND = "document date"


class LocatedExtraction(NamedTuple):
    extraction: dict[str, Any]
    dropped: list[dict[str, str]]


async def read_one_document(
    model_client: BaseChatModel,
    source_file: str,
    document_text: str,
) -> ExtractionAnswer:
    reply = await model_client.ainvoke(extraction_prompt(source_file, document_text))
    return parse_extraction_answer(str(reply.content))


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

    def located(summary: str, quote: str, kind: str) -> dict[str, str] | None:
        location = locate_quote(document_text, quote)
        if location is None:
            dropped.append(
                {
                    "kind": kind,
                    "summary": summary,
                    "quote": quote,
                    "reason": (
                        f"the quoted words were not found in {source_file} — "
                        "the model did not copy them exactly, so this "
                        f"{kind} was dropped; add it by hand if it is real."
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
        "document_date": None,
        "requirements": [],
        "testing_observations": [],
        "blockers": [],
        "embedded_instructions": [],
    }

    if answer.document_date is not None:
        dated = located(
            answer.document_date.value,
            answer.document_date.quote,
            DOCUMENT_DATE_KIND,
        )
        if dated is not None:
            extraction["document_date"] = dated

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
                {**found, "label": observation.label}
            )

    for blocker in answer.blockers:
        found = located(blocker.summary, blocker.quote, BLOCKER_KIND)
        if found is not None:
            extraction["blockers"].append(found)

    for instruction in answer.embedded_instructions:
        found = located(
            instruction.quote, instruction.quote, EMBEDDED_INSTRUCTION_KIND
        )
        if found is not None:
            extraction["embedded_instructions"].append(found)

    return LocatedExtraction(extraction=extraction, dropped=dropped)
