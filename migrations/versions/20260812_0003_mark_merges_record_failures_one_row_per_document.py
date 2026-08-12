"""Mark merged proposals, add the two terminal statuses, key documents per run.

Revision ID: 20260812_0003
Revises: 20260812_0002
Create Date: 2026-08-12
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260812_0003"
down_revision: str | None = "20260812_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RUN_STATUS_CHECK = (
    "status IN ('waiting', 'running', 'waiting for review', 'done', "
    "'closed without export', 'failed', 'ended without changes')"
)
EARLIER_RUN_STATUS_CHECK = (
    "status IN ('waiting', 'running', 'waiting for review', 'done', "
    "'closed without export')"
)


def upgrade() -> None:
    op.add_column(
        "register_rows",
        sa.Column(
            "merged_into_register_row_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_register_rows_merged_into_register_row_id_register_rows",
        "register_rows",
        "register_rows",
        ["merged_into_register_row_id"],
        ["id"],
    )

    op.add_column("runs", sa.Column("failure_reason", sa.Text(), nullable=True))
    op.drop_constraint("ck_runs_status", "runs", type_="check")
    op.create_check_constraint("ck_runs_status", "runs", RUN_STATUS_CHECK)

    # One row per file per run: a re-run of Ingest after a lost checkpoint then
    # cannot write the same document a second time.
    op.create_unique_constraint(
        "uq_documents_run_path",
        "documents",
        ["run_id", "source_path"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_documents_run_path", "documents", type_="unique")

    op.drop_constraint("ck_runs_status", "runs", type_="check")
    op.create_check_constraint("ck_runs_status", "runs", EARLIER_RUN_STATUS_CHECK)
    op.drop_column("runs", "failure_reason")

    op.drop_constraint(
        "fk_register_rows_merged_into_register_row_id_register_rows",
        "register_rows",
        type_="foreignkey",
    )
    op.drop_column("register_rows", "merged_into_register_row_id")
