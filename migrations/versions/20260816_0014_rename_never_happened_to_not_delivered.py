"""Rename the `Never happened` register status to `Not delivered`.

`Never happened` says nothing about who observed it or when. `Not delivered`
reads one way only, and the cell's citation carries the evidence.

The old constraint is dropped before the stored rows are rewritten, because it
forbids the new value as firmly as the new one forbids the old — rewriting
first fails on any database that actually holds a renamed row, which is the
only case this rename exists for. In practice none does: only `No evidence yet`
has ever been written. The rename still runs rather than assuming that.

Unlike the run-status rename in `20260815_0012`, no index predicate names this
value, so `ck_register_rows_status` is the only place the literal lives. That
was read off a real database with `pg_get_constraintdef`, not taken from the
three migration files that also spell it out.

Revision ID: 20260816_0014
Revises: 20260815_0013
Create Date: 2026-08-16
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260816_0014"
down_revision: str | None = "20260815_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_NAME = "ck_register_rows_status"
EARLIER_STATUS = "Never happened"
RENAMED_STATUS = "Not delivered"

REGISTER_ROW_STATUS_CHECK = (
    "status IN ('Done', 'Partial', 'Not delivered', 'Blocked', 'Disputed', "
    "'No evidence yet')"
)
EARLIER_REGISTER_ROW_STATUS_CHECK = (
    "status IN ('Done', 'Partial', 'Never happened', 'Blocked', 'Disputed', "
    "'No evidence yet')"
)


def upgrade() -> None:
    _rename(EARLIER_STATUS, RENAMED_STATUS, REGISTER_ROW_STATUS_CHECK)


def downgrade() -> None:
    _rename(RENAMED_STATUS, EARLIER_STATUS, EARLIER_REGISTER_ROW_STATUS_CHECK)


def _rename(old_status: str, new_status: str, check: str) -> None:
    op.drop_constraint(CONSTRAINT_NAME, "register_rows", type_="check")
    op.execute(
        sa.text(
            "UPDATE register_rows SET status = :new WHERE status = :old"
        ).bindparams(new=new_status, old=old_status)
    )
    op.create_check_constraint(CONSTRAINT_NAME, "register_rows", check)
