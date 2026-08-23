from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from app.examine.examine_register import (
    UnusableExamineAnswer,
    examine_register,
)
from app.model.client import (
    MODEL_CLIENT_ENVIRONMENT_VARIABLE,
    SCRIPTED_CLIENT,
    build_model_client,
)
from app.model.scripted_client import SCRIPT_PATH_ENVIRONMENT_VARIABLE
from tests.runs.application import PROJECT_ROOT, write_script
from tests.documents.register_documents import examine_marker


MODEL_CONFIG_PATH = PROJECT_ROOT / "config" / "model.yaml"
FROZEN_RULES = [
    {
        "id": "R1",
        "text": "Anything built must have a written requirement.",
        "params": {},
    }
]
REQUIREMENT = "Send an email to the operations team on intake form submit."
# The whole sentence the model writes, in the shape the Examine prompt asks
# for: the rule in its own words, the row by number and by what it asked for,
# what the row shows, and a yes/no ending. No rule code anywhere in it.
MODEL_ISSUE = "Only a meeting note asks for this."


def _examined(tmp_path: Path, answer: dict[str, Any]) -> list[dict[str, Any]]:
    script_path = tmp_path / "script.json"
    write_script(script_path, {examine_marker(): answer})
    model_client = build_model_client(
        MODEL_CONFIG_PATH,
        {
            MODEL_CLIENT_ENVIRONMENT_VARIABLE: SCRIPTED_CLIENT,
            SCRIPT_PATH_ENVIRONMENT_VARIABLE: str(script_path),
        },
    )
    rows = [
        {
            "id": uuid4(),
            "row_number": 1,
            "cells": {"what_was_asked": REQUIREMENT, "status": "Requested"},
            "cited_cells": frozenset({"what_was_asked"}),
        }
    ]
    return asyncio.run(examine_register(model_client, FROZEN_RULES, rows))


def test_a_finding_takes_its_rule_text_from_the_rules_the_run_froze(
    tmp_path: Path,
) -> None:
    found = _examined(
        tmp_path,
        {
            "findings": [
                {
                    "rule_id": "R1",
                    "row_number": 1,
                    "issue": MODEL_ISSUE,
                    "evidence": "Not mentioned",
                }
            ]
        },
    )

    assert found[0]["rule_text"] == FROZEN_RULES[0]["text"]


def test_a_finding_wraps_the_models_issue_and_writes_every_other_line(
    tmp_path: Path,
) -> None:
    """The model writes one sentence; the backend writes the rest (S9, S27).

    A model-phrased whole question brought JSON escapes and `Row #8` onto the
    screen. Only the issue line depends on the rule, so only the issue line is
    the model's.
    """
    found = _examined(
        tmp_path,
        {
            "findings": [
                {
                    "rule_id": "R1",
                    "row_number": 1,
                    "issue": MODEL_ISSUE,
                    "evidence": "Not mentioned",
                }
            ]
        },
    )

    assert found[0]["issue"] == MODEL_ISSUE
    assert found[0]["question"] == (
        "Register row 1\n"
        f"What was asked: {REQUIREMENT}\n"
        "Status: Requested\n"
        "\n"
        f"Rule: {FROZEN_RULES[0]['text']}\n"
        "\n"
        f"{MODEL_ISSUE}\n"
        "\n"
        "Does row 1 break this rule?\n"
        "\n"
        "Approve → The finding is added to row 1.\n"
        "Reject → The finding is not added."
    )


def test_a_finding_with_an_empty_issue_is_refused(tmp_path: Path) -> None:
    """A blank issue line leaves the one sentence only the rule can say empty."""
    with pytest.raises(UnusableExamineAnswer) as refused:
        _examined(
            tmp_path,
            {
                "findings": [
                    {
                        "rule_id": "R1",
                        "row_number": 1,
                        "issue": "   ",
                        "evidence": "Not mentioned",
                    }
                ]
            },
        )

    assert "no issue or no evidence in it" in str(refused.value)
    assert "Start another run" in str(refused.value)


def test_a_finding_against_a_rule_the_run_never_froze_is_refused(
    tmp_path: Path,
) -> None:
    with pytest.raises(UnusableExamineAnswer) as refused:
        _examined(
            tmp_path,
            {
                "findings": [
                    {
                        "rule_id": "R9",
                        "row_number": 1,
                        "issue": "Invented rule.",
                        "evidence": "Not mentioned",
                    }
                ]
            },
        )

    assert "which this run did not freeze" in str(refused.value)
    assert "Start another run" in str(refused.value)


def test_a_finding_on_a_register_row_that_does_not_exist_is_refused(
    tmp_path: Path,
) -> None:
    with pytest.raises(UnusableExamineAnswer) as refused:
        _examined(
            tmp_path,
            {
                "findings": [
                    {
                        "rule_id": "R1",
                        "row_number": 7,
                        "issue": "Invented row.",
                        "evidence": "Not mentioned",
                    }
                ]
            },
        )

    assert "was not among the 1 row(s) it was given" in str(refused.value)


def test_an_answer_that_reports_no_findings_list_at_all_is_not_read_as_none(
    tmp_path: Path,
) -> None:
    with pytest.raises(Exception) as refused:
        _examined(tmp_path, {"rules_checked": ["R1"]})

    assert "findings" in str(refused.value)
