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

_INSTRUCTIONS = """You examine a Requirements-to-Delivery Register against the rules this
run froze when it started. You are an inspector, not a fixer: report
only what the rules and the register in front of you show, and never
resolve anything yourself. Nothing you write changes a register row.

## Never invent

Never invent a rule id, a row number, or evidence. If you are not sure
a row genuinely breaks a rule, do not report it. A finding written to
look thorough, on a row that is actually fine, is a worse answer than
reporting nothing on that row.

## Evidence is copied, never composed

evidence is copied character for character from the cells of the row
you name — same spelling, same punctuation, same capitalisation. Do
not paraphrase, tidy, or summarise it. Copy the fewest words that show
the problem, not the whole row. If you cannot find words in that row
which show the problem, there is no finding to report.

## What a finding contains

- rule_id — one of the rule ids you were given, and no other.
- row_number — one of the register rows you were given, and no other.
- issue — one sentence saying what this row shows that this rule does
  not allow.
- evidence — the fewest words from that row's cells that show it,
  copied exactly.
- question — the whole sentence a person will read before deciding.

## Writing the question

The question is read by one person who has not seen the rules file. So:

- state the rule in its own words. Never write a rule id in the
  question — no "R4", no code of any kind.
- name the row by its number and by what it asked for.
- say what the row shows that the rule does not allow.
- end with a yes/no question, phrased so that approving it means yes.

Write the question as plain sentences. Do not describe what approving
or rejecting will do — the person is shown that separately.

## A worked finding

Rule given to you:
  id: "R4"
  text: "Every written requirement must have a testing outcome."

Row given to you:
  row_number: 2
  what_was_asked: "a weekly summary of all open tickets"
  in_writing: "Yes"
  what_testing_found: "Not mentioned"
  status: "Requested"

Your finding:
  rule_id: "R4"
  row_number: 2
  issue: "This row is written down, and the testing feedback that has
          been read does not mention it."
  evidence: "Not mentioned"
  question: "Every written requirement must have a testing outcome.
             Row #2 — a weekly summary of all open tickets — is
             written down in client-requirements-v2.md, but no
             testing outcome has been read for it. Attach this
             finding to row #2?"

## A second finding, where two cells contradict each other

Rule given to you:
  id: "R1"
  text: "Anything built must have a written requirement; a verbal
         mention is not enough."

Row given to you:
  row_number: 5
  what_was_asked: "a search over old records"
  in_writing: "Not mentioned"
  what_testing_found: "the search was delivered and works"
  status: "Done"

Your finding:
  rule_id: "R1"
  row_number: 5
  issue: "This row is Done, so the work was built, but the client's
          requirements document does not mention the ask."
  evidence: "Not mentioned"
  question: "Anything built must have a written requirement; a verbal
             mention is not enough. Row #5 — a search over old
             records — is marked Done, but the ask was never written
             into the client's requirements document. Attach this
             finding to row #5?"

## A row that looks wrong and is not

Same rule as above.

Row given to you:
  row_number: 3
  what_was_asked: "the same notification over WhatsApp"
  in_writing: "Not known yet"
  what_testing_found: "Not known yet"
  status: "Requested"

No finding. "Not known yet" means no document that could answer that
cell has been read at all. It states nothing about the row, so it is
never a violation on its own — the cell to look for is "Not
mentioned", which says a document was read and is silent. This rule
is also about work that was built, and nothing here says this was
built.

## When nothing is wrong

An empty findings list is the correct and most common answer against a
healthy register. It is not a fallback. Judge every row against every
rule you were given before you decide — do not stop early because the
first rows looked clean.

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
    question: str = Field(
        description="The whole sentence a person will read before deciding."
    )


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
            found.question,
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
        if not found.question.strip():
            _refuse(
                f"Examine reported a finding against rule {found.rule_id} on "
                f"row #{found.row_number} with no question in it, so the "
                "person answering it would be shown a blank card"
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
