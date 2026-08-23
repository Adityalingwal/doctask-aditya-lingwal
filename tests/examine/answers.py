from __future__ import annotations

from typing import Any


R1_ISSUE = (
    "The register row rests on a meeting note; no client requirements document "
    "read for this project states it in writing."
)
R1_EVIDENCE = "Not mentioned"


def examine_answer(findings: list[dict[str, Any]]) -> dict[str, Any]:
    return {"findings": findings}


def one_finding(
    rule_id: str = "R1",
    row_number: int = 1,
    issue: str = R1_ISSUE,
    evidence: str = R1_EVIDENCE,
) -> dict[str, Any]:
    """One finding as Examine now answers: no sentence for a person in it.

    The whole question is built by the backend around the `issue` line, so a
    scripted answer that wrote one would be testing a field that no longer
    reaches anything.
    """
    return {
        "rule_id": rule_id,
        "row_number": row_number,
        "issue": issue,
        "evidence": evidence,
    }
