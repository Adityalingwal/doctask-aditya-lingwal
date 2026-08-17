from __future__ import annotations

from typing import Any


def finding_on_row(
    rule_id: str,
    rule_text: str,
    row: dict[str, Any],
    issue: str,
    evidence: str,
    question: str,
) -> dict[str, Any]:
    """One finding, with the question a person is asked frozen into it.

    The sentence is Examine's own and is stored unchanged: months later an
    audit must show what the person actually read when they answered, and a
    sentence composed here would carry a rule code they have never seen.
    """
    return {
        "rule_id": rule_id,
        "rule_text": rule_text,
        "register_row_id": row["id"],
        "issue": issue,
        "evidence": evidence,
        "question": question,
    }
