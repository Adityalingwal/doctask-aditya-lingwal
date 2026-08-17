"""Rename the `export rejected` run status to `discarded`.

`export rejected` names the machinery a person never sees; the button they
press says `Discard this run's changes`, and the status the screen prints
verbatim should say the same thing back. Stored rows are rewritten because
`discarded` means exactly what `export rejected` meant.

The old constraint is dropped before the stored rows are rewritten, the way
`20260816_0014` does it: the old check forbids the new value as firmly as the
new one forbids the old, so rewriting first fails on exactly the databases this
rename exists for.

Unlike the run-status rename in `20260815_0012`, neither partial unique index
on `runs` needs rebuilding: read off a real database at `20260817_0018` with
`pg_get_constraintdef` and `pg_indexes`, `uq_runs_one_active_per_project`
names only `running` and `needs review` and `uq_runs_one_waiting_per_project`
only `queued`, so `ck_runs_status` is the one place this literal lives.

Revision ID: 20260817_0019
Revises: 20260817_0018
Create Date: 2026-08-17
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260817_0019"
down_revision: str | None = "20260817_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_NAME = "ck_runs_status"
EARLIER_STATUS = "export rejected"
RENAMED_STATUS = "discarded"

RUN_STATUS_CHECK = (
    "status IN ('queued', 'running', 'needs review', 'done', "
    "'discarded', 'failed', 'no changes')"
)
EARLIER_RUN_STATUS_CHECK = (
    "status IN ('queued', 'running', 'needs review', 'done', "
    "'export rejected', 'failed', 'no changes')"
)


def upgrade() -> None:
    _rename(EARLIER_STATUS, RENAMED_STATUS, RUN_STATUS_CHECK)


def downgrade() -> None:
    _rename(RENAMED_STATUS, EARLIER_STATUS, EARLIER_RUN_STATUS_CHECK)


def _rename(old_status: str, new_status: str, check: str) -> None:
    op.drop_constraint(CONSTRAINT_NAME, "runs", type_="check")
    op.execute(
        sa.text("UPDATE runs SET status = :new WHERE status = :old").bindparams(
            new=new_status, old=old_status
        )
    )
    op.create_check_constraint(CONSTRAINT_NAME, "runs", check)
