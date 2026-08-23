"""Rename `runs.not_used` back to `runs.skipped`.

One word now carries the whole list, on the tab, in the payload and here:
`Skipped`, with each entry saying which kind of skip it is — `read before`,
`not read`, or `not attached`. The 2026-08-18 rename to `not_used` was made
because "skipped" read wrongly for a quote out of a file that *was* read; the
kind words answer that instead, and a person reading the tab never meets two
names for one thing.

Nothing but the name changes. The stored entries are jsonb and are not
rewritten: `ALTER TABLE ... RENAME COLUMN` carries the value, the `NOT NULL`
and the `'[]'::jsonb` default across untouched, and the downgrade is the exact
reverse. Migration 0020, which did the opposite rename, is left alone.

The kind words stored inside old entries are not rewritten either: no database
older than this branch is kept or shipped, so a fresh clone writes the new
words from the first run.

Revision ID: 20260823_0024
Revises: 20260823_0023
Create Date: 2026-08-23
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op


revision: str = "20260823_0024"
down_revision: str | None = "20260823_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EARLIER_COLUMN = "not_used"
RENAMED_COLUMN = "skipped"


def upgrade() -> None:
    op.alter_column("runs", EARLIER_COLUMN, new_column_name=RENAMED_COLUMN)


def downgrade() -> None:
    op.alter_column("runs", RENAMED_COLUMN, new_column_name=EARLIER_COLUMN)
