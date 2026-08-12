from __future__ import annotations

import json
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.extract.answer import json_object_in


NEW_ROW = "new row"
EXISTING_ROW = "existing row"
POSSIBLE_MATCH = "possible match"
MATCH_PROMPT_MARKER = "Match these requirements against the register"

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

Reply with a JSON object and nothing else, in this shape:

{{"outcomes": [{{"requirement_index": 0, "outcome": "{NEW_ROW}",
                 "row_number": null}}]}}"""


class MatchOutcome(BaseModel):
    requirement_index: int
    outcome: str
    row_number: int | None = None


class MatchAnswer(BaseModel):
    outcomes: list[MatchOutcome] = Field(default_factory=list)


async def match_requirements(
    model_client: BaseChatModel,
    register_rows: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
) -> MatchAnswer:
    reply = await model_client.ainvoke(_match_prompt(register_rows, requirements))
    return MatchAnswer.model_validate_json(json_object_in(str(reply.content)))


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
