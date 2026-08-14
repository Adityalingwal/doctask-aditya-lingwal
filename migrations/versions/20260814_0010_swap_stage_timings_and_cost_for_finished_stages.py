"""Swap stage_timings and the cost/usage columns for finished_stages.

Revision ID: 20260814_0010
Revises: 20260814_0009
Create Date: 2026-08-14
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260814_0010"
down_revision: str | None = "20260814_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column(
            "finished_stages",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.drop_column("runs", "stage_timings")
    op.drop_column("runs", "token_usage")
    op.drop_column("runs", "estimated_cost_usd")
    op.drop_column("runs", "cost_unknown_reason")


def downgrade() -> None:
    # A downgrade cannot recover which stages a run had finished, or the
    # durations and token counts this slice removed — the data is gone either
    # way, so the columns come back empty rather than reconstructed.
    op.add_column(
        "runs",
        sa.Column(
            "stage_timings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "runs",
        sa.Column(
            "token_usage",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "runs",
        sa.Column(
            "estimated_cost_usd",
            sa.Numeric(precision=12, scale=6),
            nullable=True,
        ),
    )
    op.add_column("runs", sa.Column("cost_unknown_reason", sa.Text(), nullable=True))
    op.drop_column("runs", "finished_stages")
