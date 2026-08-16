from __future__ import annotations

import json
from typing import Any, NoReturn

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.examine.found_issue import finding_on_row
from app.extract.answer import json_object_in
from app.model.call_the_model import call_the_model


EXAMINE_PROMPT_MARKER = "Examine this register against these rules"
UNUSABLE_ANSWER_FIX = (
    " Nothing was recorded as a finding, because a finding that names a rule "
    "or a row the register does not have is invented rather than found. Start "
    "another run so the register is examined again; if the answers keep coming "
    "back this way, name a stronger model in config/model.yaml."
)

_INSTRUCTIONS = """You examine a Requirements-to-Delivery Register against the \
rules this run froze when it started.

Report only what the rules and the register in front of you show. Never invent \
a rule id, a row number, or evidence. Where the register breaks no rule, answer \
with an empty findings list: a weak finding written to look thorough is worse \
than none at all.

You never resolve anything. A finding states the problem and asks a person; it \
never says a cell has been corrected, and nothing you write changes the \
register.

Each finding names:
- rule_id — one of the rule ids you were given, and no other.
- row_number — one of the register rows you were given, and no other.
- issue — what this row shows that this rule does not allow.
- evidence — the words in that row which show it.

Reply with nothing but the structured answer your schema defines."""


class FoundIssue(BaseModel):
    rule_id: str = Field(description="One of the rule ids you were given.")
    row_number: int = Field(
        description="The number of one of the register rows you were given."
    )
    issue: str = Field(
        description="What this row shows that this rule does not allow."
    )
    evidence: str = Field(description="The words in that row which show it.")


class ExamineAnswer(BaseModel):
    # Required: a reply without it is a failed Examine, not a register that
    # nothing was found wrong with.
    findings: list[FoundIssue]


class UnusableExamineAnswer(RuntimeError):
    """Examine answered about a rule or a row it was not given."""


async def examine_register(
    model_client: BaseChatModel,
    rules: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Judge the whole register against the whole rule set in one model call."""
    answered = await call_the_model(
        model_client, _examine_prompt(rules, rows), ExamineAnswer
    )
    answer = ExamineAnswer.model_validate_json(json_object_in(answered))

    rule_text_by_id = {rule["id"]: rule["text"] for rule in rules}
    row_by_number = {row["row_number"]: row for row in rows}
    return [
        finding_on_row(
            found.rule_id,
            rule_text_by_id[found.rule_id],
            row_by_number[found.row_number],
            found.issue,
            found.evidence,
        )
        for found in _refuse_what_was_not_asked_about(
            answer, rule_text_by_id, row_by_number
        )
    ]


def _refuse_what_was_not_asked_about(
    answer: ExamineAnswer,
    rule_text_by_id: dict[str, str],
    row_by_number: dict[int, dict[str, Any]],
) -> list[FoundIssue]:
    """Check every finding names a rule and a row that were actually sent.

    A finding against a rule this run never froze, or a row the register does
    not have, cannot be traced back to anything — it is invented evidence, and
    the whole answer is refused rather than the good half kept.
    """
    for found in answer.findings:
        if found.rule_id not in rule_text_by_id:
            _refuse(
                f"Examine reported a finding against rule {found.rule_id}, "
                f"which this run did not freeze (it froze "
                f"{', '.join(rule_text_by_id) or 'no rules'})"
            )
        if found.row_number not in row_by_number:
            _refuse(
                f"Examine reported a finding on register row "
                f"#{found.row_number}, which was not among the "
                f"{len(row_by_number)} row(s) it was given"
            )
        if not found.issue.strip() or not found.evidence.strip():
            _refuse(
                f"Examine reported a finding against rule {found.rule_id} on "
                f"row #{found.row_number} with no issue or no evidence in it"
            )
    return answer.findings


def _refuse(cause: str) -> NoReturn:
    raise UnusableExamineAnswer(f"{cause}.{UNUSABLE_ANSWER_FIX}")


def _examine_prompt(
    rules: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> list[BaseMessage]:
    register_view = [
        {"row_number": row["row_number"], **row["cells"]} for row in rows
    ]
    return [
        SystemMessage(content=_INSTRUCTIONS),
        HumanMessage(
            content=(
                f"{EXAMINE_PROMPT_MARKER}.\n\n"
                f"Rules:\n{json.dumps(rules, indent=2)}\n\n"
                f"Register rows:\n{json.dumps(register_view, indent=2)}"
            )
        ),
    ]
