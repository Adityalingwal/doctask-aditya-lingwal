from __future__ import annotations

import json
from typing import Any, NoReturn

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.extract.answer import json_object_in
from app.model.call_the_model import call_the_model


NEW_ROW = "new row"
EXISTING_ROW = "existing row"
POSSIBLE_MATCH = "possible match"
OUTCOMES = (NEW_ROW, EXISTING_ROW, POSSIBLE_MATCH)
MATCH_PROMPT_MARKER = "Match these requirements against the register"
INCOMPLETE_ANSWER_FIX = (
    " Nothing was proposed for the register, because a requirement Match did "
    "not answer for is not a new row. Start another run so Match is asked "
    "again; if it keeps answering incompletely, name a stronger model in "
    "config/model.yaml."
)

_INSTRUCTIONS = f"""You decide, for each requirement found in this batch of \
documents, whether the register already has a row for it.

Answer one of three outcomes per requirement:
- "{NEW_ROW}" — no existing row traces this requirement.
- "{EXISTING_ROW}" — an existing row traces exactly this requirement; give its \
row_number.
- "{POSSIBLE_MATCH}" — it may be the same requirement as an existing row but you \
are not certain; give that row_number.

Never merge two requirements you are unsure about. Wrongly merging corrupts the \
register silently, so where there is real doubt answer "{POSSIBLE_MATCH}" and a \
person will decide. Requirements that are close in wording can still be \
different asks — "email notification" and "WhatsApp notification" are two \
requirements, not one.

Answer for every requirement you were sent, exactly once each, and reply with \
nothing but the structured answer your schema defines."""


class MatchOutcome(BaseModel):
    requirement_index: int = Field(
        description="The index of the requirement this answer is about."
    )
    outcome: str = Field(description="One of the three outcomes above.")
    row_number: int | None = Field(
        default=None,
        description=(
            "The register row this requirement matched, or null for a new row."
        ),
    )


class MatchAnswer(BaseModel):
    # Required: a reply without it is a failed Match, not a register in which
    # every requirement quietly became a new row.
    outcomes: list[MatchOutcome]


class IncompleteMatchAnswer(RuntimeError):
    """Match answered about a different set of requirements than it was sent."""


async def match_requirements(
    model_client: BaseChatModel,
    register_rows: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
) -> MatchAnswer:
    answered = await call_the_model(
        model_client, _match_prompt(register_rows, requirements), MatchAnswer
    )
    answer = MatchAnswer.model_validate_json(json_object_in(answered))
    _refuse_an_incomplete_answer(answer, len(requirements))
    return answer


def _refuse_an_incomplete_answer(answer: MatchAnswer, asked_about: int) -> None:
    """Check the answer covers every requirement sent, exactly once, usably.

    The shape being valid says nothing about the content: an answer can be
    well-formed JSON and still leave out the one requirement that mattered.
    """
    answered: set[int] = set()
    for outcome in answer.outcomes:
        index = outcome.requirement_index
        if index in answered:
            _refuse(f"Match answered twice for requirement {index}")
        answered.add(index)

        if outcome.outcome not in OUTCOMES:
            _refuse(
                f"Match answered '{outcome.outcome}' for requirement {index}, "
                f"which is not one of {', '.join(OUTCOMES)}"
            )
        if outcome.outcome == NEW_ROW and outcome.row_number is not None:
            _refuse(
                f"Match answered '{NEW_ROW}' for requirement {index} and still "
                f"named row #{outcome.row_number}"
            )
        if outcome.outcome != NEW_ROW and outcome.row_number is None:
            _refuse(
                f"Match answered '{outcome.outcome}' for requirement {index} "
                "without naming the register row it matched"
            )

    if answered != set(range(asked_about)):
        _refuse(
            f"Match was asked about {asked_about} requirement(s), numbered 0 to "
            f"{asked_about - 1}, and answered for {sorted(answered)}"
        )


def _refuse(cause: str) -> NoReturn:
    raise IncompleteMatchAnswer(f"{cause}.{INCOMPLETE_ANSWER_FIX}")


def _match_prompt(
    register_rows: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
) -> list[BaseMessage]:
    register_view = [
        {"row_number": row["row_number"], "what_was_asked": row["what_was_asked"]}
        for row in register_rows
    ]
    requirement_view = [
        {
            "requirement_index": index,
            "summary": requirement["summary"],
            "source_file": requirement["source_file"],
            "source_words": requirement["source_words"],
        }
        for index, requirement in enumerate(requirements)
    ]
    return [
        SystemMessage(content=_INSTRUCTIONS),
        HumanMessage(
            content=(
                f"{MATCH_PROMPT_MARKER}.\n\n"
                f"Register rows:\n{json.dumps(register_view, indent=2)}\n\n"
                f"Requirements found in this batch:\n"
                f"{json.dumps(requirement_view, indent=2)}"
            )
        ),
    ]
