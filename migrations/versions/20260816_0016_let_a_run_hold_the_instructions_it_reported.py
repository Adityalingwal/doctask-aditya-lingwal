"""Let a run hold the embedded instructions it reported and did not follow.

Until now a line inside a document addressed to whatever processes it next was
written to the log and nowhere else — not in `GET /runs/{id}`, neither export,
nor on the screen. A person who never reads the container logs could not learn
that a document had tried it.

This is information, not a question: the answer is always "do not follow", so
it never becomes a decision and never gates a run.

Revision ID: 20260816_0016
Revises: 20260816_0015
Create Date: 2026-08-16
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260816_0016"
down_revision: str | None = "20260816_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column(
            "reported_instructions",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("runs", "reported_instructions")
