from __future__ import annotations

from app.register.cells import (
    IN_WRITING_NOT_KNOWN_YET,
    IN_WRITING_YES,
    NOT_MENTIONED,
    in_writing_says_yes,
)


def test_only_a_written_down_answer_counts_as_in_writing() -> None:
    """The merge asks this of both rows, so a wrong answer would rewrite a cell."""
    assert in_writing_says_yes(IN_WRITING_YES)
    assert not in_writing_says_yes(IN_WRITING_NOT_KNOWN_YET)
    assert not in_writing_says_yes(NOT_MENTIONED)
