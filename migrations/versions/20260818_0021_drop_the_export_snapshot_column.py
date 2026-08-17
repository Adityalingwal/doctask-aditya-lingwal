"""Drop `runs.export_json` — the register is read live, and the snapshot goes.

`export_json` held a copy of the whole register, written by Commit and read by
the screen and the MCP tool. Both now read `register_rows` live through one
core function, Commit writes no copy, and `collect_batch`'s already-read rule
— the column's one non-display reader — tests `runs.status = 'done'` instead,
which the commit node writes in the same transaction that commits the rows.
Nothing else names the column: read off a real database at revision
`20260818_0020`, `pg_get_constraintdef` over `pg_constraint` for `runs` shows
only `ck_runs_status`, `pg_indexes` shows only the two partial unique indexes
on `project_id` and `status`, and `pg_views` holds no view of ours.

The downgrade re-adds the column nullable and empty. It cannot restore the
snapshots: they were copies made at commit time, dropped here with the column,
and nothing holds the register as it stood at each of those moments. A
downgraded application still commits and reads correctly — the old code fills
the column again on each new commit — but every run committed before the
downgrade reports no export.

Revision ID: 20260818_0021
Revises: 20260818_0020
Create Date: 2026-08-18
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260818_0021"
down_revision: str | None = "20260818_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DROPPED_COLUMN = "export_json"


def upgrade() -> None:
    op.drop_column("runs", DROPPED_COLUMN)


def downgrade() -> None:
    op.add_column(
        "runs",
        sa.Column(
            DROPPED_COLUMN,
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
