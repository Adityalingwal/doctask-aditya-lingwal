from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import NamedTuple
from uuid import UUID, uuid4

from psycopg import AsyncConnection

from app.extract.answer import UNRELATED_DOCUMENT
from app.ingest.read_source_document import READER_EXTENSIONS, read_source_document
from app.ingest.unreadable_document import DocumentUnreadable
from app.runs.not_used_kinds import ALREADY_READ_KIND, NOT_READ_KIND


UNREADABLE_FORMAT = "Not a format this system reads. It reads .md and .pdf."


class CollectedBatch(NamedTuple):
    document_ids: list[UUID]
    not_used: list[dict[str, str]]


async def collect_batch(
    connection: AsyncConnection,
    run_id: UUID,
    project_id: UUID,
    source_folder: Path,
    accepted_extensions: frozenset[str],
    page_limit: int,
) -> CollectedBatch:
    """Take every file this project has never read before, by name or content."""
    document_ids: list[UUID] = []
    not_used: list[dict[str, str]] = []

    # One transaction, so a killed process never leaves half a batch behind.
    async with connection.transaction():
        for path in sorted(_top_level_files(source_folder)):
            extension = path.suffix.lower()
            if extension not in accepted_extensions or extension not in READER_EXTENSIONS:
                not_used.append(
                    _not_used_entry(NOT_READ_KIND, path.name, UNREADABLE_FORMAT)
                )
                continue

            try:
                text = await asyncio.to_thread(
                    read_source_document, path, page_limit
                )
            except DocumentUnreadable as unreadable:
                not_used.append(
                    _not_used_entry(NOT_READ_KIND, path.name, str(unreadable))
                )
                continue
            except OSError as error:
                not_used.append(
                    _not_used_entry(
                        NOT_READ_KIND,
                        path.name,
                        f"Could not be opened ({error.strerror}).",
                    )
                )
                continue

            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            matched = await _already_read_by_name_or_content(
                connection, project_id, path.name, content_hash
            )
            if matched is not None:
                not_used.append(
                    _not_used_entry(
                        ALREADY_READ_KIND, path.name, _already_read_reason(matched)
                    )
                )
                continue

            document_ids.append(
                await _write_document(
                    connection, run_id, path.name, text, content_hash
                )
            )

    return CollectedBatch(document_ids=document_ids, not_used=not_used)


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


def _not_used_entry(kind: str, file_name: str, reason: str) -> dict[str, str]:
    return {"kind": kind, "file": file_name, "reason": reason}


async def _already_read_by_name_or_content(
    connection: AsyncConnection,
    project_id: UUID,
    source_path: str,
    content_hash: str,
) -> str | None:
    """Which of this file's name or content an earlier, finished read matches.

    A document is finished with when Extract read it and nothing is left to
    do with what it said: either that run exported its register, or the
    document held nothing the register could ever take. Demanding an export
    in the second case would send an unrelated document to the model again,
    and pay for it, on every run for as long as the file sits in the folder.
    The second half asks what Match asks of the same column.

    Either the name or the content alone is enough to count as already read —
    a document that failed extraction has no row here at all (`extraction IS
    NOT NULL` excludes it), so the next run reads it again regardless of which
    half would otherwise have matched.
    """
    result = await connection.execute(
        "SELECT bool_or(documents.source_path = %s) AS name_matched, "
        "bool_or(documents.content_hash = %s) AS content_matched "
        "FROM documents "
        "JOIN runs ON runs.id = documents.run_id "
        "WHERE runs.project_id = %s "
        "AND documents.extraction IS NOT NULL "
        "AND (runs.export_json IS NOT NULL "
        "OR documents.extraction ->> 'document_type' = %s "
        "OR jsonb_array_length(documents.extraction -> 'requirements') = 0) "
        "AND (documents.source_path = %s OR documents.content_hash = %s)",
        (
            source_path,
            content_hash,
            project_id,
            UNRELATED_DOCUMENT,
            source_path,
            content_hash,
        ),
    )
    row = await result.fetchone()
    name_matched = bool(row and row["name_matched"])
    content_matched = bool(row and row["content_matched"])
    if name_matched and content_matched:
        return "both"
    if name_matched:
        return "name"
    if content_matched:
        return "content"
    return None


def _already_read_reason(matched: str) -> str:
    if matched == "both":
        return "Already read, and unchanged since."
    return "Read before — an edited or renamed file is not read again."
