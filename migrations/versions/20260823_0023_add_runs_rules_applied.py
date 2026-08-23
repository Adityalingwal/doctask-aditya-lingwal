"""Let a run record which of its frozen rules Examine actually sent to the model.

`rules_snapshot` holds every rule the run froze and stays the fingerprint
source. Once a rule only runs when the document kinds it names have been read,
the frozen set and the applied set are no longer the same list, and the
register has to know which rules a run actually judged it against — a rule that
did not run leaves an earlier run's finding standing.

Nullable, because a run that never reached Examine applied no rules and has not
answered the question; an empty list is the different answer "Examine ran and
no rule applied".

Revision ID: 20260823_0023
Revises: 20260823_0022
Create Date: 2026-08-23
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260823_0023"
down_revision: str | None = "20260823_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ADDED_COLUMN = "rules_applied"


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column(
            ADDED_COLUMN,
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("runs", ADDED_COLUMN)
