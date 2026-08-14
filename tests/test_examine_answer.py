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
from tests.runs.application import write_script
from tests.documents.register_documents import examine_marker


MODEL_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "model.yaml"
FROZEN_RULES = [
    {
        "id": "R1",
        "text": "Anything built must have a written requirement.",
        "params": {},
    }
]
REQUIREMENT = "Send an email to the operations team on intake form submit."


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
            "cells": {"what_was_asked": REQUIREMENT, "status": "No evidence yet"},
            "cited_cells": frozenset({"what_was_asked"}),
        }
    ]
    found, _usage = asyncio.run(examine_register(model_client, FROZEN_RULES, rows))
    return found


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
                    "issue": "Only a meeting note asks for this.",
                    "evidence": "Row #1 cites meeting-note.md.",
                }
            ]
        },
    )

    assert found[0]["rule_text"] == FROZEN_RULES[0]["text"]
    assert f"Row #1 ({REQUIREMENT})" in found[0]["question"]


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
                        "evidence": "Row #1.",
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
                        "evidence": "Row #7.",
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
