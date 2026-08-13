from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.ingest.locate_quote import HEADING_MARKER


DOCX_EXTENSION = ".docx"
HEADING_STYLE_PREFIX = "Heading"
CELL_SEPARATOR = " | "


def read_docx(path: Path) -> str:
    """Paragraphs and table cells, in the order Word stores them."""
    lines: list[str] = []
    for content in Document(str(path)).iter_inner_content():
        if isinstance(content, Paragraph):
            lines.append(_paragraph_line(content))
        elif isinstance(content, Table):
            lines.extend(
                CELL_SEPARATOR.join(cell.text.strip() for cell in row.cells)
                for row in content.rows
            )
    return "\n".join(lines)


def _paragraph_line(paragraph: Paragraph) -> str:
    # Word stores no page numbers, so a heading is the only place a citation
    # can honestly name. Marking one the way Markdown does lets a single
    # place-finder serve both formats instead of two that can drift apart.
    style = paragraph.style
    if style is not None and style.name.startswith(HEADING_STYLE_PREFIX):
        return f"{HEADING_MARKER} {paragraph.text}"
    return paragraph.text
