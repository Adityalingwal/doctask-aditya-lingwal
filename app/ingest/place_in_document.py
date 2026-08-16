from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from app.ingest.locate_quote import nearest_heading_above
from app.ingest.read_pdf import PAGE_SEPARATOR, PDF_EXTENSION
from app.ingest.read_text_document import MARKDOWN_EXTENSION


def page_number_at(document_text: str, character_offset: int) -> str:
    pages_before = document_text[:character_offset].count(PAGE_SEPARATOR)
    return f"page {pages_before + 1}"


# A citation may only name a place its own reader produced: pages exist in a
# PDF and headings are written into Markdown itself. These are the two shapes a
# place can take, which is why these are the two formats this system reads.
_PLACE_FINDERS: dict[str, Callable[[str, int], str]] = {
    MARKDOWN_EXTENSION: nearest_heading_above,
    PDF_EXTENSION: page_number_at,
}


def place_finder_for(source_file: str) -> Callable[[str, int], str]:
    return _PLACE_FINDERS[Path(source_file).suffix.lower()]
