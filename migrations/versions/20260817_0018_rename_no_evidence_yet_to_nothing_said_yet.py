"""Rename the `No evidence yet` register status to `Nothing said yet`.

`No evidence yet` reads like a sibling of `Not delivered` when the two are
opposites: one says the documents have been read and none of them spoke about
this ask, the other says testing looked and reported the work absent. Every
other status in the column says who said what, and `Nothing said yet` says it
too.

The old constraint is dropped before the stored rows are rewritten, the way
`20260816_0014` does it: the old check forbids the new value as firmly as the
new one forbids the old, so rewriting first fails on exactly the databases this
rename exists for.

`ck_register_rows_status` is the only place the literal lives. That was read
off a real database at `20260817_0017` with `pg_get_constraintdef` and
`pg_indexes`, not taken from the migration files that also spell it out: the
four indexes on `register_rows`, `citations` and `audit` are plain btree
indexes with no predicate, so none of them names a status.

Revision ID: 20260817_0018
Revises: 20260817_0017
Create Date: 2026-08-17
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260817_0018"
down_revision: str | None = "20260817_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_NAME = "ck_register_rows_status"
EARLIER_STATUS = "No evidence yet"
RENAMED_STATUS = "Nothing said yet"

REGISTER_ROW_STATUS_CHECK = (
    "status IN ('Done', 'Partial', 'Not delivered', 'Handed over', "
    "'Disputed', 'Nothing said yet')"
)
EARLIER_REGISTER_ROW_STATUS_CHECK = (
    "status IN ('Done', 'Partial', 'Not delivered', 'Handed over', "
    "'Disputed', 'No evidence yet')"
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
