from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import NamedTuple
from uuid import UUID, uuid4

from psycopg import AsyncConnection

from app.ingest.read_markdown import MARKDOWN_EXTENSION, read_markdown
from app.runs.statuses import DONE


READER_EXTENSIONS = frozenset({MARKDOWN_EXTENSION})
SKIPPED_FILE_KIND = "file"


class CollectedBatch(NamedTuple):
    document_ids: list[UUID]
    skipped: list[dict[str, str]]


async def collect_batch(
    connection: AsyncConnection,
    run_id: UUID,
    project_id: UUID,
    source_folder: Path,
    accepted_extensions: frozenset[str],
) -> CollectedBatch:
    """Take every new or changed file waiting in the project's folder."""
    document_ids: list[UUID] = []
    skipped: list[dict[str, str]] = []

    for path in sorted(_top_level_files(source_folder)):
        extension = path.suffix.lower()
        if extension not in accepted_extensions:
            skipped.append(
                _skipped(
                    path.name,
                    f"unsupported format — {extension or 'no extension'} is not "
                    "listed in config/formats.yaml; add it there and add a "
                    "reader for it.",
                )
            )
            continue
        if extension not in READER_EXTENSIONS:
            skipped.append(
                _skipped(
                    path.name,
                    f"no reader for {extension} in this release — only "
                    f"{MARKDOWN_EXTENSION} documents are read so far.",
                )
            )
            continue

        try:
            text = await asyncio.to_thread(read_markdown, path)
        except OSError as error:
            skipped.append(
                _skipped(
                    path.name,
                    f"could not be read from {source_folder} ({error.strerror}) "
                    "— check the file is still present and readable, then run "
                    "again.",
                )
            )
            continue

        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if await _already_read_unchanged(
            connection, project_id, path.name, content_hash
        ):
            skipped.append(
                _skipped(
                    path.name,
                    "unchanged since the last completed run — an unchanged "
                    "document is never read or sent to a model again.",
                )
            )
            continue

        document_id = uuid4()
        await connection.execute(
            "INSERT INTO documents "
            "(id, run_id, source_path, extracted_text, content_hash) "
            "VALUES (%s, %s, %s, %s, %s)",
            (document_id, run_id, path.name, text, content_hash),
        )
        document_ids.append(document_id)

    return CollectedBatch(document_ids=document_ids, skipped=skipped)


def _top_level_files(source_folder: Path) -> list[Path]:
    return [path for path in source_folder.iterdir() if path.is_file()]


def _skipped(file_name: str, reason: str) -> dict[str, str]:
    return {"kind": SKIPPED_FILE_KIND, "file": file_name, "reason": reason}


async def _already_read_unchanged(
    connection: AsyncConnection,
    project_id: UUID,
    source_path: str,
    content_hash: str,
) -> bool:
    # Only a run that finished with an export counts as having read a document:
    # a run closed without export left no rows behind, so its documents must be
    # readable again.
    result = await connection.execute(
        "SELECT 1 FROM documents "
        "JOIN runs ON runs.id = documents.run_id "
        "WHERE runs.project_id = %s AND runs.status = %s "
        "AND documents.source_path = %s AND documents.content_hash = %s "
        "LIMIT 1",
        (project_id, DONE, source_path, content_hash),
    )
    return await result.fetchone() is not None
