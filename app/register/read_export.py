from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import AsyncConnection

from app.refusal import NotPossibleNow, UnusableRequest
from app.register.export_register import (
    EXPORT_FORMATS,
    MARKDOWN_FORMAT,
    export_as_markdown,
)
from app.runs.run_records import require_run


async def read_export(
    connection: AsyncConnection,
    run_id: UUID,
    export_format: str,
) -> dict[str, Any] | str:
    """The register one run exported, in the format the caller asked for."""
    if export_format not in EXPORT_FORMATS:
        raise UnusableRequest(
            f"'{export_format}' is not an export format — ask for "
            f"{' or '.join(EXPORT_FORMATS)}."
        )
    run = await require_run(connection, run_id)
    if run["export_json"] is None:
        raise NotPossibleNow(
            "this run has exported nothing — the register is exported only "
            "after the Delivery Owner approves the export decision and POST "
            f"/runs/{run_id}/finish-review commits the run."
        )
    if export_format == MARKDOWN_FORMAT:
        return export_as_markdown(run["export_json"])
    return run["export_json"]
