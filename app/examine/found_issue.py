from __future__ import annotations

from typing import Any


def finding_on_row(
    rule_id: str,
    rule_text: str,
    row: dict[str, Any],
    issue: str,
    evidence: str,
) -> dict[str, Any]:
    """One finding, with the question a person is asked frozen into it.

    The sentence is the record: months later an audit must show what the person
    actually read when they answered, not a pointer to a rule file that may
    have been edited since.
    """
    question = (
        f"{rule_id} — {rule_text} Row #{row['row_number']} "
        f"({row['cells']['what_was_asked']}): {issue} "
        "Attach this finding to the row?"
    )
    return {
        "rule_id": rule_id,
        "rule_text": rule_text,
        "register_row_id": row["id"],
        "issue": issue,
        "evidence": evidence,
        "question": question,
    }
