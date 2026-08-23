from __future__ import annotations

from typing import Any

from app.register.cells import COLUMN_HEADINGS
from app.review.decision_text import finding_text


def finding_on_row(
    rule_id: str,
    rule_text: str,
    row: dict[str, Any],
    issue: str,
    evidence: str,
) -> dict[str, Any]:
    """One finding, with the question a person is asked frozen into it.

    Every line of that question but one is built here from stored data: the
    row as Examine saw it, the rule's own words, the yes/no line, and what
    each answer does. The exception is the issue line, which only the rule can
    say (S27), so it stays the model's own sentence. The whole text is frozen
    because months later an audit must show what the person actually read.
    """
    asked = finding_text(
        row_number=row["row_number"],
        cells={
            COLUMN_HEADINGS[name]: value for name, value in row["cells"].items()
        },
        rule_text=rule_text,
        issue=issue,
    )
    return {
        "rule_id": rule_id,
        "rule_text": rule_text,
        "register_row_id": row["id"],
        "issue": issue,
        "evidence": evidence,
        "question": asked.question,
        "parts": asked.parts,
    }
