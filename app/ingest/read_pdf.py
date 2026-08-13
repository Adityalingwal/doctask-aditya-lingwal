from __future__ import annotations

from pathlib import Path

import pdfplumber
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from app.ingest.unreadable_document import DocumentUnreadable


PDF_EXTENSION = ".pdf"
# The character a page break has meant in extracted text since long before
# this system; it lets a citation name its page without a second store.
PAGE_SEPARATOR = "\f"


def pdf_page_count(path: Path) -> int:
    """How many pages the PDF has, or why it cannot be opened at all.

    Every PDF passes through here before it is read, so a file no PDF library
    can parse is turned into a reason for this one document rather than an
    exception that ends the whole batch.
    """
    try:
        reader = PdfReader(str(path))
        # Counting the pages of an encrypted PDF fails the same way a damaged
        # one does, so encryption is answered before the count is attempted.
        if reader.is_encrypted:
            raise DocumentUnreadable(
                f"{path.name} is encrypted, so its text cannot be read — open "
                "it with its password, save an unprotected copy into the "
                "project folder, and start another run."
            )
        return len(reader.pages)
    except PyPdfError as damaged:
        raise DocumentUnreadable(
            f"{path.name} could not be opened as a PDF — the file is damaged or "
            "incomplete, or something that is not a PDF was given a .pdf name; "
            "replace it with a working copy in the project folder and start "
            "another run."
        ) from damaged


def read_pdf(path: Path) -> str:
    """Every page's text, page-separated so a citation can name its page."""
    with pdfplumber.open(str(path)) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]

    if not any(page.strip() for page in pages):
        raise DocumentUnreadable(
            f"{path.name} has no text layer, so it is a scanned image rather "
            "than a text document — this system does not run OCR; supply a "
            "text-based export of it and start another run."
        )
    return PAGE_SEPARATOR.join(pages)
