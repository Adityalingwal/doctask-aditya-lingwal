from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import NamedTuple
from uuid import UUID, uuid4

from psycopg import AsyncConnection

from app.extract.answer import UNRELATED_DOCUMENT
from app.ingest.read_markdown import MARKDOWN_EXTENSION, read_markdown


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

    # One transaction, so a killed process never leaves half a batch behind.
    async with connection.transaction():
        for path in sorted(_top_level_files(source_folder)):
            extension = path.suffix.lower()
            if extension not in accepted_extensions:
                skipped.append(
                    _skipped(
                        path.name,
                        f"unsupported format — {extension or 'no extension'} is "
                        "not listed in config/formats.yaml; add it there and add "
                        "a reader for it.",
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
                        f"could not be read from {source_folder} "
                        f"({error.strerror}) — check the file is still present "
                        "and readable, then run again.",
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
                        "unchanged since an earlier run read it and finished "
                        "with what it said — an unchanged document is never "
                        "read or sent to a model again.",
                    )
                )
                continue

            document_ids.append(
                await _write_document(
                    connection, run_id, path.name, text, content_hash
                )
            )

    return CollectedBatch(document_ids=document_ids, skipped=skipped)


async def _write_document(
    connection: AsyncConnection,
    run_id: UUID,
    source_path: str,
    text: str,
    content_hash: str,
) -> UUID:
    """Write one document of this run's batch, or take back the one already there.

    Ingest runs again whole when its checkpoint was lost, and this run may
    already have written this file. The unique key makes a second row
    impossible, and the existing row still goes into the batch — Extract has
    not read it yet.
    """
    result = await connection.execute(
        "INSERT INTO documents "
        "(id, run_id, source_path, extracted_text, content_hash) "
        "VALUES (%s, %s, %s, %s, %s) "
        "ON CONFLICT (run_id, source_path) DO UPDATE SET "
        "extracted_text = EXCLUDED.extracted_text, "
        "content_hash = EXCLUDED.content_hash "
        "RETURNING id",
        (uuid4(), run_id, source_path, text, content_hash),
    )
    written = await result.fetchone()
    return written["id"]


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
    # A document is finished with when Extract read it and nothing is left to
    # do with what it said: either that run exported its register, or the
    # document held nothing the register could ever take. Demanding an export
    # in the second case would send an unrelated document to the model again,
    # and pay for it, on every run for as long as the file sits in the folder.
    # The second half asks what Match asks of the same column.
    result = await connection.execute(
        "SELECT 1 FROM documents "
        "JOIN runs ON runs.id = documents.run_id "
        "WHERE runs.project_id = %s "
        "AND documents.extraction IS NOT NULL "
        "AND (runs.export_json IS NOT NULL "
        "OR documents.extraction ->> 'document_type' = %s "
        "OR jsonb_array_length(documents.extraction -> 'requirements') = 0) "
        "AND documents.source_path = %s AND documents.content_hash = %s "
        "LIMIT 1",
        (project_id, UNRELATED_DOCUMENT, source_path, content_hash),
    )
    return await result.fetchone() is not None
