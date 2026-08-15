"""A folder is a project: one project per `source_folder_path`, enforced.

`create_project` already gets-or-creates by folder in application code, but
without a database constraint two callers racing the read-then-write window
could still both insert a row for the same folder. Widening never breaks
anything, so the downgrade only drops the constraint; narrowing can fail
against a database that already holds two projects over one folder, so the
upgrade refuses — naming them — rather than silently merging or deleting
either one, the same way 20260814_0011 refused rather than reguess a status.

Revision ID: 20260815_0013
Revises: 20260815_0012
Create Date: 2026-08-15
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260815_0013"
down_revision: str | None = "20260815_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_NAME = "uq_projects_source_folder_path"


def upgrade() -> None:
    duplicated = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT source_folder_path, array_agg(id) AS project_ids "
                "FROM projects GROUP BY source_folder_path HAVING count(*) > 1"
            )
        )
        .fetchall()
    )
    if duplicated:
        named = "; ".join(
            f"'{row.source_folder_path}' held by {row.project_ids}"
            for row in duplicated
        )
        raise RuntimeError(
            f"more than one project is stored over the same folder: {named}. "
            "A folder is now one project's identity, so this cannot be "
            "narrowed automatically — decide which project each folder "
            "should keep, merge or remove the others by hand, then run this "
            "migration again."
        )

    op.create_unique_constraint(
        CONSTRAINT_NAME, "projects", ["source_folder_path"]
    )


def downgrade() -> None:
    # Widening never violates existing data, so nothing here needs to refuse.
    op.drop_constraint(CONSTRAINT_NAME, "projects", type_="unique")
