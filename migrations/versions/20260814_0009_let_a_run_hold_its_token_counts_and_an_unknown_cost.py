"""Let a run hold its token counts and an unknown cost.

Revision ID: 20260814_0009
Revises: 20260814_0008
Create Date: 2026-08-14
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260814_0009"
down_revision: str | None = "20260814_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column(
            "token_usage",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column("runs", sa.Column("cost_unknown_reason", sa.Text(), nullable=True))
    # A cost of zero cannot be told apart from a cost nobody could estimate, and
    # a run whose model reported no token count must say so rather than show a
    # figure. Every existing row carries the untouched default, which is exactly
    # the unknown this column now represents.
    op.alter_column(
        "runs",
        "estimated_cost_usd",
        existing_type=sa.Numeric(precision=12, scale=6),
        nullable=True,
        server_default=None,
    )
    op.execute("UPDATE runs SET estimated_cost_usd = NULL WHERE estimated_cost_usd = 0")


def downgrade() -> None:
    op.execute("UPDATE runs SET estimated_cost_usd = 0 WHERE estimated_cost_usd IS NULL")
    op.alter_column(
        "runs",
        "estimated_cost_usd",
        existing_type=sa.Numeric(precision=12, scale=6),
        nullable=False,
        server_default=sa.text("0"),
    )
    op.drop_column("runs", "cost_unknown_reason")
    op.drop_column("runs", "token_usage")
