from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import AsyncConnection

from app.refusal import UnusableRequest
from app.register.export_register import (
    MARKDOWN_FORMAT,
    REGISTER_FORMATS,
    build_register_document,
    register_as_markdown,
)
from app.runs.run_records import require_project


async def read_register(
    connection: AsyncConnection,
    project_id: UUID,
    register_format: str,
) -> dict[str, Any] | str:
    """One project's register, read live from its committed rows."""
    if register_format not in REGISTER_FORMATS:
        raise UnusableRequest(
            f"'{register_format}' is not a register format — ask for "
            f"{' or '.join(REGISTER_FORMATS)}."
        )
    project = await require_project(connection, project_id)
    register = await build_register_document(connection, project)
    if register_format == MARKDOWN_FORMAT:
        return register_as_markdown(register)
    return register
