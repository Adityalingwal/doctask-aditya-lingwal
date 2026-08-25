from __future__ import annotations

import re
from pathlib import Path

from app.examine.examine_register import _INSTRUCTIONS as EXAMINE_INSTRUCTIONS
from app.match.match_requirements import _INSTRUCTIONS as MATCH_INSTRUCTIONS
from app.match.match_requirements import (
    _OBSERVATION_INSTRUCTIONS as OBSERVATION_INSTRUCTIONS,
)


README = Path(__file__).resolve().parents[1] / "README.md"
# Each limitation has exactly one home, and it is this file. PROGRESS points
# here and DECISIONS keeps one line; a second full wording anywhere else is
# how two documents start disagreeing about what the system does.
LIMITATIONS_WITH_ONE_HOME = (
    # 36 — a handover only ever sets `Handed over`.
    "Partial",
    # S10 — a testing observation that reached no row runs against no rule.
    "Skipped tab",
    # S27 — a model-judged rule may not raise the same finding twice.
    "may not raise the same finding again",
)
WATCHER_TIMING = ("2s", "5s")


def test_the_readme_names_every_limitation_that_lives_only_here() -> None:
    readme = README.read_text(encoding="utf-8")

    for limitation in LIMITATIONS_WITH_ONE_HOME:
        assert limitation in readme


def test_the_readme_states_the_watcher_timing_the_shipped_config_uses() -> None:
    """A reader waiting for a run must not be told the wrong number."""
    readme = README.read_text(encoding="utf-8")

    for interval in WATCHER_TIMING:
        assert interval in readme
    assert "(4s)" not in readme
    assert "(10s)" not in readme


def test_the_readme_uses_the_current_skipped_tab_name() -> None:
    readme = README.read_text(encoding="utf-8")

    assert "**Skipped** tab" in readme
    assert re.search(r"\*\*Not\s+used\*\*\s+tab", readme) is None


def test_the_readme_uses_the_status_word_the_register_writes() -> None:
    readme = README.read_text(encoding="utf-8")

    assert "Requested" in readme
    assert "Nothing said yet" not in readme


def test_no_prompt_asks_the_model_to_write_a_question_a_person_reads() -> None:
    """Every worked example teaches the fields the model still answers with.

    An example showing a whole question is an instruction to write one, and
    the backend now writes them all (S9).
    """
    for instructions in (
        MATCH_INSTRUCTIONS,
        OBSERVATION_INSTRUCTIONS,
        EXAMINE_INSTRUCTIONS,
    ):
        assert "Row #" not in instructions
        assert "Attach this finding" not in instructions
        assert "question:" not in instructions


def test_the_examine_prompt_teaches_a_read_and_silent_document_not_an_unread_one() -> None:
    """Item 25: `Not known yet` alone is never a finding.

    The worked example used to teach exactly that, and the demo raised six
    findings against silence because of it.
    """
    assert "Not mentioned" in EXAMINE_INSTRUCTIONS
    assert "testing-feedback-12-aug.md was read" in EXAMINE_INSTRUCTIONS
    assert (
        '"Not known yet" means no document that could answer that'
        in EXAMINE_INSTRUCTIONS
    )
