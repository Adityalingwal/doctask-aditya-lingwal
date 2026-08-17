from __future__ import annotations

from typing import Any


R1_ISSUE = (
    "The register row rests on a meeting note; no client requirements document "
    "read for this project states it in writing."
)
R1_EVIDENCE = "Row #1 cites meeting-note.md only."
# The model writes this sentence itself, so a fixture has to write one too:
# the rule in its own words, the row by number, and a yes/no ending — and no
# rule code, which the person reading it has never seen.
R1_QUESTION = (
    "Anything built must have a written requirement; a verbal mention is not "
    "enough. Row #{row_number} rests on a meeting note, and no client "
    "requirements document read for this project states it in writing. "
    "Attach this finding to row #{row_number}?"
)


def examine_answer(findings: list[dict[str, Any]]) -> dict[str, Any]:
    return {"findings": findings}


def one_finding(
    rule_id: str = "R1",
    row_number: int = 1,
    issue: str = R1_ISSUE,
    evidence: str = R1_EVIDENCE,
    question: str | None = None,
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "row_number": row_number,
        "issue": issue,
        "evidence": evidence,
        "question": question or R1_QUESTION.format(row_number=row_number),
    }
