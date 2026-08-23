from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import AsyncConnection

from app.extract.answer import UNRELATED_DOCUMENT
from app.runs.statuses import DONE, ENDED_WITHOUT_CHANGES


# The read-once rule as one SQL condition, so every reader of it asks the same
# question. Ingest decides whether to read a file again, Commit decides whose
# silence a row must record, and Examine decides whether a rule may run yet —
# three answers that have to rest on one definition of "this project has read
# it". The condition is written once here and never restated.
READ_BY_THE_PROJECT = (
    "runs.project_id = %s "
    "AND documents.extraction IS NOT NULL "
    "AND (runs.status = %s "
    "OR documents.extraction ->> 'document_type' = %s "
    "OR (jsonb_array_length(documents.extraction -> 'requirements') = 0 "
    "AND runs.status = %s))"
)


def read_by_the_project_parameters(project_id: UUID) -> tuple[Any, ...]:
    """The values `READ_BY_THE_PROJECT` binds, in the order it names them."""
    return (project_id, DONE, UNRELATED_DOCUMENT, ENDED_WITHOUT_CHANGES)


def where_the_project_has_read(
    project_id: UUID,
    include_run_id: UUID | None,
) -> tuple[str, tuple[Any, ...]]:
    """The read-once condition, optionally widened to one run's own batch.

    A run's status is not `done` until Commit writes it, in the same
    transaction that commits the rows, so without the widening the stages that
    have just read a document — Match, Examine, Commit — cannot see it at all.
    """
    parameters = read_by_the_project_parameters(project_id)
    if include_run_id is None:
        return READ_BY_THE_PROJECT, parameters
    return (
        f"({READ_BY_THE_PROJECT} OR (runs.project_id = %s "
        "AND documents.run_id = %s AND documents.extraction IS NOT NULL))",
        (*parameters, project_id, include_run_id),
    )


async def documents_read_by_project(
    connection: AsyncConnection,
    project_id: UUID,
    kind: str,
    include_run_id: UUID | None = None,
) -> list[dict[str, Any]]:
    """Every document of one kind this project has read, in file-name order."""
    condition, parameters = where_the_project_has_read(project_id, include_run_id)
    result = await connection.execute(
        "SELECT DISTINCT documents.source_path, documents.id, documents.run_id "
        "FROM documents JOIN runs ON runs.id = documents.run_id "
        f"WHERE {condition} "
        "AND documents.extraction ->> 'document_type' = %s "
        "ORDER BY documents.source_path",
        (*parameters, kind),
    )
    return [
        {
            "source_path": document["source_path"],
            "document_id": document["id"],
            "run_id": document["run_id"],
        }
        for document in await result.fetchall()
    ]


async def kinds_read_by_project(
    connection: AsyncConnection,
    project_id: UUID,
    include_run_id: UUID | None = None,
) -> set[str]:
    """Which kinds of document this project has read, this run's batch included."""
    condition, parameters = where_the_project_has_read(project_id, include_run_id)
    result = await connection.execute(
        "SELECT DISTINCT documents.extraction ->> 'document_type' AS kind "
        "FROM documents JOIN runs ON runs.id = documents.run_id "
        f"WHERE {condition}",
        parameters,
    )
    return {document["kind"] for document in await result.fetchall()}
