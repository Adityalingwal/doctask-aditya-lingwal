"""Rename four run statuses so the screen can show the stored value verbatim.

The screen no longer translates a status into a friendlier label — it prints
the stored word. Four stored words read badly to a person, so the words
change instead: 'ended without changes' -> 'no changes', 'closed without
export' -> 'export rejected', 'waiting for review' -> 'needs review', and
'waiting' -> 'queued'. 'running', 'done' and 'failed' are unchanged.

The check constraint is narrowed after the data is rewritten, and both
partial unique indexes on `runs` — the project's durable lock — are rebuilt,
because their `postgresql_where` clauses name the renamed statuses as
literals. A stale literal there would not fail any test; it would just let a
second run start on a project that already holds one.

Revision ID: 20260815_0012
Revises: 20260814_0011
Create Date: 2026-08-15
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260815_0012"
down_revision: str | None = "20260814_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RENAMED_STATUSES = (
    ("waiting", "queued"),
    ("waiting for review", "needs review"),
    ("closed without export", "export rejected"),
    ("ended without changes", "no changes"),
)

RUN_STATUS_CHECK = (
    "status IN ('queued', 'running', 'needs review', 'done', "
    "'export rejected', 'failed', 'no changes')"
)
EARLIER_RUN_STATUS_CHECK = (
    "status IN ('waiting', 'running', 'waiting for review', 'done', "
    "'closed without export', 'failed', 'ended without changes')"
)


def upgrade() -> None:
    op.drop_constraint("ck_runs_status", "runs", type_="check")
    for old_status, new_status in RENAMED_STATUSES:
        op.execute(
            sa.text("UPDATE runs SET status = :new WHERE status = :old").bindparams(
                new=new_status, old=old_status
            )
        )
    op.create_check_constraint("ck_runs_status", "runs", RUN_STATUS_CHECK)

    op.drop_index("uq_runs_one_active_per_project", table_name="runs")
    op.create_index(
        "uq_runs_one_active_per_project",
        "runs",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('running', 'needs review')"),
    )
    op.drop_index("uq_runs_one_waiting_per_project", table_name="runs")
    op.create_index(
        "uq_runs_one_waiting_per_project",
        "runs",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("status = 'queued'"),
    )


def downgrade() -> None:
    op.drop_index("uq_runs_one_waiting_per_project", table_name="runs")
    op.create_index(
        "uq_runs_one_waiting_per_project",
        "runs",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("status = 'waiting'"),
    )
    op.drop_index("uq_runs_one_active_per_project", table_name="runs")
    op.create_index(
        "uq_runs_one_active_per_project",
        "runs",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('running', 'waiting for review')"),
    )

    op.drop_constraint("ck_runs_status", "runs", type_="check")
    for old_status, new_status in RENAMED_STATUSES:
        op.execute(
            sa.text("UPDATE runs SET status = :old WHERE status = :new").bindparams(
                old=old_status, new=new_status
            )
        )
    op.create_check_constraint("ck_runs_status", "runs", EARLIER_RUN_STATUS_CHECK)
