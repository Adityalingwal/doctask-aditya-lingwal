from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

from app.ingest.read_docx import DOCX_EXTENSION, read_docx
from app.ingest.read_pdf import PDF_EXTENSION, pdf_page_count, read_pdf
from app.ingest.read_text_document import (
    MARKDOWN_EXTENSION,
    TEXT_EXTENSION,
    read_text_document,
)
from app.ingest.unreadable_document import DocumentUnreadable


class SourceReader(NamedTuple):
    read_text: Callable[[Path], str]
    # Only a format that genuinely paginates can report a page count. Markdown,
    # plain text and Word have no pages, and claiming one for them would invent
    # the very locator the citation contract forbids.
    count_pages: Callable[[Path], int] | None


_READERS: dict[str, SourceReader] = {
    MARKDOWN_EXTENSION: SourceReader(read_text_document, None),
    TEXT_EXTENSION: SourceReader(read_text_document, None),
    DOCX_EXTENSION: SourceReader(read_docx, None),
    PDF_EXTENSION: SourceReader(read_pdf, pdf_page_count),
}

READER_EXTENSIONS = frozenset(_READERS)


def read_source_document(path: Path, page_limit: int) -> str:
    """The text of one supported document, or why this system will not read it.

    Every reader passes the page limit here, so a paginated format added later
    is limited by the same gate rather than by a check of its own.
    """
    reader = _READERS[path.suffix.lower()]
    if reader.count_pages is not None:
        pages = reader.count_pages(path)
        if pages > page_limit:
            raise DocumentUnreadable(
                f"{pages} pages — this system reads up to {page_limit} pages."
            )
    return reader.read_text(path)
