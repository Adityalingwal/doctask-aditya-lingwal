from __future__ import annotations

from app.register.cells import (
    DATE_UNKNOWN,
    IN_WRITING_NOT_FOUND_IN,
    IN_WRITING_NOT_KNOWN_YET,
    IN_WRITING_WRITTEN_IN_OPENING,
    in_writing_says_yes,
)
from app.register.document_dates import earlier_of, earliest_dated


REQUIREMENTS_FILE = "client-requirements-v1.md"
MEETING_NOTE = "meeting-notes-10-mar.md"


def _requirement(source_file: str, written_date: str | None) -> dict[str, object]:
    return {
        "summary": "an email to the operations team on submit",
        "source_file": source_file,
        "document_date": (
            None
            if written_date is None
            else {"summary": written_date, "source_file": source_file, "place": "line 3"}
        ),
    }


def test_a_date_nobody_can_place_never_hands_the_row_a_later_date() -> None:
    """Read order claims nothing; picking the only readable date claims an order.

    A document writing "sometime in March" states a date this system cannot
    place. Preferring the one document it *can* place would let the row report
    a first-seen date its own evidence never supports.
    """
    unplaceable_first = [
        _requirement(MEETING_NOTE, "sometime in March"),
        _requirement(REQUIREMENTS_FILE, "12 March 2026"),
    ]

    earliest = earliest_dated(unplaceable_first)

    assert earliest is not None
    assert earliest["source_file"] == MEETING_NOTE


def test_two_placeable_dates_still_give_the_earlier_one() -> None:
    read_in_file_name_order = [
        _requirement(REQUIREMENTS_FILE, "12 March 2026"),
        _requirement(MEETING_NOTE, "10 March 2026"),
    ]

    earliest = earliest_dated(read_in_file_name_order)

    assert earliest is not None
    assert earliest["source_file"] == MEETING_NOTE


def test_a_requirement_stating_no_date_does_not_block_the_others() -> None:
    """No date at all is not an unplaceable date — it makes no claim to weigh."""
    one_undated = [
        _requirement(REQUIREMENTS_FILE, None),
        _requirement(MEETING_NOTE, "10 March 2026"),
    ]

    earliest = earliest_dated(one_undated)

    assert earliest is not None
    assert earliest["source_file"] == MEETING_NOTE


def test_a_merge_takes_the_earlier_date_and_keeps_what_it_cannot_place() -> None:
    assert earlier_of("12 March 2026", "10 March 2026") == "10 March 2026"
    assert earlier_of("10 March 2026", "12 March 2026") == "10 March 2026"
    assert earlier_of("12 March 2026", DATE_UNKNOWN) == "12 March 2026"
    assert earlier_of(DATE_UNKNOWN, "12 March 2026") == DATE_UNKNOWN


def test_only_a_written_down_answer_counts_as_in_writing() -> None:
    """The merge asks this of both rows, so a wrong answer would rewrite a cell."""
    assert in_writing_says_yes(f"{IN_WRITING_WRITTEN_IN_OPENING}{REQUIREMENTS_FILE}.")
    assert not in_writing_says_yes(IN_WRITING_NOT_KNOWN_YET)
    assert not in_writing_says_yes(
        IN_WRITING_NOT_FOUND_IN.format(documents=REQUIREMENTS_FILE)
    )
