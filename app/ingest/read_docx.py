from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.ingest.unreadable_document import DocumentUnreadable


DOCX_EXTENSION = ".docx"


def read_docx(path: Path) -> str:
    """Paragraphs and table cells, in the order Word stores them.

    Nothing is added to the text. A citation quotes these words back and the
    model reads them as evidence, so a separator or marker invented here would
    become evidence the document does not contain. Each cell takes its own
    line, which is why a quote spanning two cells is not found and its
    requirement is dropped rather than supported by assembled words.
    """
    try:
        document = Document(str(path))
    except (PackageNotFoundError, BadZipFile) as damaged:
        raise DocumentUnreadable(
            "This Word file could not be opened — it is damaged, or not a "
            ".docx."
        ) from damaged

    lines: list[str] = []
    for content in document.iter_inner_content():
        if isinstance(content, Paragraph):
            lines.append(content.text)
        elif isinstance(content, Table):
            lines.extend(
                cell.text.strip() for row in content.rows for cell in row.cells
            )
    return "\n".join(lines)
