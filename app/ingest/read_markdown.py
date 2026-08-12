from __future__ import annotations

from pathlib import Path


MARKDOWN_EXTENSION = ".md"
PRIMARY_ENCODING = "utf-8"
FALLBACK_ENCODING = "latin-1"


def read_markdown(path: Path) -> str:
    raw_bytes = path.read_bytes()
    try:
        return raw_bytes.decode(PRIMARY_ENCODING)
    except UnicodeDecodeError:
        # latin-1 maps every byte, so a document that is not UTF-8 still reads
        # rather than stopping the run.
        return raw_bytes.decode(FALLBACK_ENCODING)
