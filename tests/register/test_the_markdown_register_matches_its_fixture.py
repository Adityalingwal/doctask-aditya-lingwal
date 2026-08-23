from __future__ import annotations

from pathlib import Path
from typing import Any

from app.register.cells import CELL_NAMES
from app.register.export_register import register_as_markdown


FIXTURE = Path(__file__).parent / "fixtures" / "register.md"
TESTING_OUTCOME_RULE = "Every written requirement must have a testing outcome."
WRITTEN_REQUIREMENT_RULE = (
    "Anything built must have a written requirement; a verbal mention is not "
    "enough."
)
ABSENCE_LINE = (
    "testing-feedback-12-aug.md was read, and it does not mention this ask."
)
ISSUE_LINE = (
    "testing-feedback-12-aug.md was read, and it says nothing about this "
    "requirement."
)


def _register(**overrides: Any) -> dict[str, Any]:
    """One register holding both shapes the file has to render.

    Row 1 has a quote supporting two cells and no finding; row 2 has an
    absence line and one finding. Between them they exercise every branch the
    renderer has.
    """
    return {
        "project": {"id": "0f3f0f6a-4f8a-4a4a-9c1e-3f6b2d5a7c11", "name": "Helpline AI"},
        "exported_at": "2026-08-23T11:02:00+00:00",
        "columns": list(CELL_NAMES),
        "rows": [
            {
                "row_number": 1,
                "fingerprint": "a1b2c3",
                "cells": {
                    "what_was_asked": (
                        "BrightCart wants an AI system that answers "
                        "support-line calls."
                    ),
                    "in_writing": "Yes",
                    "what_testing_found": (
                        "The voice agent answered every question it was asked."
                    ),
                    "status": "Done",
                },
                "evidence": [
                    {
                        "source_line": 'client-requirements-v1.md, under "Requirements"',
                        "quote": "An AI system that answers the support line.",
                        "absence": None,
                        "cells": ["What was asked", "Written down"],
                    },
                    {
                        "source_line": "testing-feedback-12-aug.md, page 3",
                        "quote": "The voice agent answered every question we tried.",
                        "absence": None,
                        "cells": ["What testing found", "Status"],
                    },
                ],
                "findings": [],
            },
            {
                "row_number": 2,
                "fingerprint": "d4e5f6",
                "cells": {
                    "what_was_asked": "Support must work in Hindi and English.",
                    "in_writing": "Yes",
                    "what_testing_found": "Not mentioned",
                    "status": "Requested",
                },
                "evidence": [
                    {
                        "source_line": (
                            "meeting-notes-02-jul.md, before the first heading"
                        ),
                        "quote": "Support has to work in Hindi as well as English.",
                        "absence": None,
                        "cells": ["What was asked"],
                    },
                    {
                        "source_line": 'client-requirements-v1.md, under "Requirements"',
                        "quote": "The bot must answer in Hindi and in English.",
                        "absence": None,
                        "cells": ["Written down"],
                    },
                    {
                        "source_line": None,
                        "quote": None,
                        "absence": ABSENCE_LINE,
                        "cells": ["What testing found"],
                    },
                ],
                "findings": [
                    {
                        "finding_id": "7a1b2c3d-4444-4e55-8666-777788889999",
                        "row_number": 2,
                        "rule_id": "R4",
                        "rule_text": TESTING_OUTCOME_RULE,
                        "issue": ISSUE_LINE,
                        "evidence": "Not mentioned",
                        "question": "Does row 2 break this rule?",
                        "raised_by_run": 4,
                    }
                ],
            },
        ],
        "rules": {
            "run_number": 5,
            "rows_examined": 7,
            "rules": [
                {"id": "R4", "text": TESTING_OUTCOME_RULE},
                {"id": "R1", "text": WRITTEN_REQUIREMENT_RULE},
            ],
        },
        **overrides,
    }


def test_the_markdown_register_matches_its_fixture() -> None:
    """The whole file, character for character — it is what a client is sent."""
    assert register_as_markdown(_register()) == FIXTURE.read_text(encoding="utf-8")


def test_a_row_with_no_finding_prints_no_findings_block() -> None:
    """"No findings" on every clean row is noise a reader has to skim (item 43)."""
    rendered = register_as_markdown(_register())

    assert rendered.count("**Findings**") == 1
    assert "No findings" not in rendered


def test_the_rules_section_says_so_plainly_when_no_rule_applied() -> None:
    """An empty findings list means nothing at all unless the rules are named."""
    rendered = register_as_markdown(
        _register(rules={"run_number": 5, "rows_examined": 7, "rules": []})
    )

    assert "No rules applied" in rendered
    assert "applied 0 rules" not in rendered


def test_one_rule_against_one_row_is_counted_in_the_singular() -> None:
    rendered = register_as_markdown(
        _register(
            rules={
                "run_number": 3,
                "rows_examined": 1,
                "rules": [{"id": "R4", "text": TESTING_OUTCOME_RULE}],
            }
        )
    )

    assert "Run 3 applied 1 rule against 1 row" in rendered


def test_a_register_no_run_has_committed_to_still_says_what_it_holds() -> None:
    rendered = register_as_markdown(
        _register(rows=[], exported_at=None, rules=None)
    )

    assert "Nothing has been added to this register yet." in rendered
    assert "No rules applied" in rendered
