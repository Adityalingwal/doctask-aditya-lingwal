from __future__ import annotations

from pathlib import Path

from app.ingest.locate_quote import PLACE_BEFORE_FIRST_HEADING, locate_quote
from app.ingest.place_in_document import page_number_at
from app.ingest.read_pdf import PAGE_SEPARATOR
from app.ingest.read_text_document import read_text_document
from app.ingest.source_line import SAYS, source_line

# The single character pdfplumber emits for "fi" in a ligatured font.
FI_LIGATURE = "ﬁ"


MEETING_NOTE = """# Intake Portal Meeting Notes

**Date:** 10 March 2026

## Discussion

The client asked for the operations team to receive a notification whenever a
visitor submits the intake form.

## Next steps

Confirm the notification wording with the client before it is built.
"""

# The brief's own confirmed repro for a sentence restated under two headings —
# ordinary in a testing feedback document restating the same finding against
# several requirements.
REPEATED_UNDER_TWO_HEADINGS = (
    "# A\n\nThe login page is not working.\n\n# B\n\nThe login page is not working.\n"
)


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


def test_a_quote_appearing_under_two_headings_names_only_the_first() -> None:
    location = locate_quote(REPEATED_UNDER_TWO_HEADINGS, "The login page is not working.")

    assert location is not None
    # The stored words are read from the first occurrence, so the first
    # occurrence is the place the citation names. A comma-joined pair cannot
    # be written as the one source line every surface prints.
    assert location.place == "A"
    assert location.source_words == "The login page is not working."


def test_the_source_line_of_a_quote_under_two_headings_names_only_the_first() -> None:
    location = locate_quote(REPEATED_UNDER_TWO_HEADINGS, "The login page is not working.")

    assert location is not None
    assert source_line("testing-feedback-12-aug.md", location.place) == (
        'testing-feedback-12-aug.md, under "A"'
    )


def test_the_source_line_says_so_when_a_quote_sits_above_every_heading() -> None:
    location = locate_quote("Plain opening line.\n\n# Later heading\n", "Plain opening")

    assert location is not None
    assert source_line("notes.md", location.place) == (
        "notes.md, before the first heading"
    )


def test_the_source_line_of_a_pdf_quote_names_its_page() -> None:
    document_text = f"Page one text.{PAGE_SEPARATOR}The login page is not working.\n"
    location = locate_quote(
        document_text, "The login page is not working.", page_number_at
    )

    assert location is not None
    assert source_line("scan.pdf", location.place) == "scan.pdf, page 2"


def test_a_decision_appends_says_to_the_same_source_line() -> None:
    # Decisions, evidence and the Skipped tab share one template; only a
    # decision, which shows the words next, ends its line with a colon.
    assert f"{source_line('notes.md', 'Discussion')}{SAYS}" == (
        'notes.md, under "Discussion", says:'
    )


def test_a_quote_appearing_once_still_names_that_one_place() -> None:
    location = locate_quote(
        "# A\n\nThe login page is not working.\n\n# B\n\nEverything else passed.\n",
        "The login page is not working.",
    )

    assert location is not None
    assert location.place == "A"


def test_quote_above_every_heading_says_so_rather_than_naming_a_later_heading() -> None:
    location = locate_quote("Plain opening line.\n\n# Later heading\n", "Plain opening")

    assert location is not None
    assert location.place == PLACE_BEFORE_FIRST_HEADING


def test_empty_quote_is_not_located() -> None:
    assert locate_quote(MEETING_NOTE, "   ") is None


def test_a_curly_apostrophe_in_the_document_matches_a_straight_one_in_the_quote() -> None:
    # The document has the curly apostrophe a live model routinely writes;
    # the quote has the straight one — the same character rendered two ways,
    # exactly as "\n" and a space already are.
    document = "# Scope\n\nthe client’s vendor sent it.\n"
    location = locate_quote(document, "the client's vendor sent it.")

    assert location is not None
    assert location.place == "Scope"


def test_a_ligature_in_a_pdf_does_not_shift_the_place_the_citation_names() -> None:
    # A one-character-to-two-character replacement earlier in the document
    # (ﬁ -> fi) must not shift the offset of anything after it.
    document_text = (
        f"Notes: {FI_LIGATURE}nal review complete.{PAGE_SEPARATOR}"
        "The login page is not working.\n"
    )
    location = locate_quote(
        document_text, "The login page is not working.", page_number_at
    )

    assert location is not None
    assert location.place == "page 2"
    assert location.source_words == "The login page is not working."


def test_the_citation_keeps_the_documents_own_characters_not_the_normalised_ones() -> None:
    # Normalisation is for finding only, never for what is stored — a document
    # written with a curly apostrophe is still quoted with one.
    document = "# Scope\n\nthe client’s vendor sent it.\n"
    location = locate_quote(document, "the client's vendor sent it.")

    assert location is not None
    assert location.source_words == "the client’s vendor sent it."


def test_document_written_in_latin_1_is_still_read(tmp_path: Path) -> None:
    document_path = tmp_path / "notes.md"
    document_path.write_bytes("# Notes\n\nCafé rota agreed.\n".encode("latin-1"))

    assert "Caf" in read_text_document(document_path)
