"""Rename `runs.skipped` to `runs.not_used`.

The column holds three different weights of thing: a file an earlier run had
already read, a file that was never read, and a quote that was not found in its
file, so the requirement it carried was dropped. Only the first two are skips
at all — the third names a file that *was* read. `not_used` is the one word
true of all three, and the tab, the payload field and this column now say it
together rather than each saying its own thing.

Nothing but the name changes. The stored entries are jsonb and are not
rewritten: `ALTER TABLE ... RENAME COLUMN` carries the value, the `NOT NULL`
and the `'[]'::jsonb` default across untouched, and the downgrade is the exact
reverse. No constraint and no index names this column — read off a real
database at this revision with `pg_get_constraintdef` over `pg_constraint` and
`pg_indexes` for `runs`: the only check is `ck_runs_status`, and both partial
unique indexes are on `project_id` and `status`.

Revision ID: 20260818_0020
Revises: 20260817_0019
Create Date: 2026-08-18
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op


revision: str = "20260818_0020"
down_revision: str | None = "20260817_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EARLIER_COLUMN = "skipped"
RENAMED_COLUMN = "not_used"


def upgrade() -> None:
    op.alter_column("runs", EARLIER_COLUMN, new_column_name=RENAMED_COLUMN)


def downgrade() -> None:
    op.alter_column("runs", RENAMED_COLUMN, new_column_name=EARLIER_COLUMN)
