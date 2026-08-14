from __future__ import annotations

from pathlib import Path

from app.ingest.locate_quote import PLACE_BEFORE_FIRST_HEADING, locate_quote
from app.ingest.read_text_document import read_text_document


MEETING_NOTE = """# Intake Portal Meeting Notes

**Date:** 10 March 2026

## Discussion

The client asked for the operations team to receive a notification whenever a
visitor submits the intake form.

## Next steps

The client asked for the operations team to receive a notification whenever a
visitor submits the intake form.
"""


def test_quote_broken_across_lines_is_found_under_its_own_heading() -> None:
    location = locate_quote(
        MEETING_NOTE,
        "receive a notification whenever a visitor submits the intake form",
    )

    assert location is not None
    assert location.place == "Discussion"


def test_located_quote_carries_the_source_own_words_not_the_model_wording() -> None:
    location = locate_quote(
        MEETING_NOTE,
        "notification whenever a   visitor submits",
    )

    assert location is not None
    assert location.source_words == "notification whenever a\nvisitor submits"


def test_quote_the_model_invented_is_not_located() -> None:
    assert locate_quote(MEETING_NOTE, "the client wants search on old records") is None


def test_repeated_words_resolve_to_their_first_occurrence() -> None:
    location = locate_quote(MEETING_NOTE, "The client asked for the operations team")

    assert location is not None
    assert location.place == "Discussion"


def test_quote_above_every_heading_says_so_rather_than_naming_a_later_heading() -> None:
    location = locate_quote("Plain opening line.\n\n# Later heading\n", "Plain opening")

    assert location is not None
    assert location.place == PLACE_BEFORE_FIRST_HEADING


def test_empty_quote_is_not_located() -> None:
    assert locate_quote(MEETING_NOTE, "   ") is None


def test_document_written_in_latin_1_is_still_read(tmp_path: Path) -> None:
    document_path = tmp_path / "notes.md"
    document_path.write_bytes("# Notes\n\nCafé rota agreed.\n".encode("latin-1"))

    assert "Caf" in read_text_document(document_path)
