from __future__ import annotations

from pathlib import Path

from app.ingest.locate_quote import PLACE_BEFORE_FIRST_HEADING
from app.ingest.read_pdf import PDF_EXTENSION


# A decision quotes the document and then shows the words, so its line ends in
# a colon. Evidence and the Skipped tab name the place alone. One suffix, so
# the two never drift into two templates.
SAYS = ", says:"


def source_line(source_file: str, source_place: str) -> str:
    """Where a quote sits, in the one sentence every surface prints.

    Decisions, evidence and the Skipped tab all name a place, and a second
    template would let one screen call a heading a section while another calls
    it a page. Markdown and PDF differ here and nowhere else: a PDF place is
    already the words `page 3`, and a Markdown place is a heading or the
    marker for the text above the first one.
    """
    if Path(source_file).suffix.lower() == PDF_EXTENSION:
        return f"{source_file}, {source_place}"
    if source_place == PLACE_BEFORE_FIRST_HEADING:
        return f"{source_file}, {PLACE_BEFORE_FIRST_HEADING}"
    return f'{source_file}, under "{source_place}"'
