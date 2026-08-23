"""Let a decision hold the parts its sentence was built from.

Every sentence a person reads on a decision card is now built in the backend
from stored data. `question` keeps the whole text, frozen at the moment it was
raised, so the audit still shows what was read. `parts` keeps the same text
taken apart — the row block, the quotes, the yes/no line and what each answer
does — so the screen and an MCP caller can lay it out without composing any
wording of their own, and neither has to rebuild the sentence out of cells
that have since moved.

Nullable, because the export gate is answered by pressing a button rather than
by reading a card: it has one fixed question and no parts at all.

Revision ID: 20260823_0025
Revises: 20260823_0024
Create Date: 2026-08-23
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260823_0025"
down_revision: str | None = "20260823_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ADDED_COLUMN = "parts"


def upgrade() -> None:
    op.add_column(
        "decisions",
        sa.Column(
            ADDED_COLUMN,
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("decisions", ADDED_COLUMN)
