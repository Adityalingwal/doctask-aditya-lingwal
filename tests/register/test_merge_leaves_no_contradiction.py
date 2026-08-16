from __future__ import annotations

from app.register.cells import (
    IN_WRITING_NOT_FOUND_IN,
    IN_WRITING_NOT_KNOWN_YET,
    IN_WRITING_WRITTEN_IN_OPENING,
    in_writing_says_yes,
)


REQUIREMENTS_FILE = "client-requirements-v1.md"


def test_only_a_written_down_answer_counts_as_in_writing() -> None:
    """The merge asks this of both rows, so a wrong answer would rewrite a cell."""
    assert in_writing_says_yes(f"{IN_WRITING_WRITTEN_IN_OPENING}{REQUIREMENTS_FILE}.")
    assert not in_writing_says_yes(IN_WRITING_NOT_KNOWN_YET)
    assert not in_writing_says_yes(
        IN_WRITING_NOT_FOUND_IN.format(documents=REQUIREMENTS_FILE)
    )
