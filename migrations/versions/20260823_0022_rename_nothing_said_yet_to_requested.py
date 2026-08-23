"""Rename the `Nothing said yet` register status to `Requested`.

A reader meets this cell before they have read anything else about the row, and
`Nothing said yet` asks them to work out what the silence is about. `Requested`
says the one thing that is actually known: the client asked for this, and no
document has spoken about delivery or testing yet. `Not built` was rejected —
no document read so far makes that claim, and the status must never say more
than the evidence does. Third rename of this status: `No evidence yet` became
`Nothing said yet` at `20260817_0018`, and that becomes `Requested` here.

The old constraint is dropped before the stored rows are rewritten, the way
`20260817_0018` does it: the old check forbids the new value as firmly as the
new one forbids the old, so rewriting first fails on exactly the databases this
rename exists for.

`ck_register_rows_status` is the only place the literal lives; the four indexes
on `register_rows`, `citations` and `audit` are plain btree indexes with no
predicate, as `20260817_0018` recorded off a real database.

Revision ID: 20260823_0022
Revises: 20260818_0021
Create Date: 2026-08-23
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260823_0022"
down_revision: str | None = "20260818_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_NAME = "ck_register_rows_status"
EARLIER_STATUS = "Nothing said yet"
RENAMED_STATUS = "Requested"

REGISTER_ROW_STATUS_CHECK = (
    "status IN ('Done', 'Partial', 'Not delivered', 'Handed over', "
    "'Disputed', 'Requested')"
)
EARLIER_REGISTER_ROW_STATUS_CHECK = (
    "status IN ('Done', 'Partial', 'Not delivered', 'Handed over', "
    "'Disputed', 'Nothing said yet')"
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
