"""Record on the decision which document stopped asking for a requirement.

A row can be cited to more than one document. Without this column the approved
withdrawal has to work out afterwards which of them dropped the requirement,
and it can pick the wrong one — writing an absence against a document that is
still asking.

Revision ID: 20260814_0008
Revises: 20260814_0007
Create Date: 2026-08-14
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260814_0008"
down_revision: str | None = "20260814_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "decisions",
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_decisions_source_document_id_documents",
        "decisions",
        "documents",
        ["source_document_id"],
        ["id"],
    )


def downgrade() -> None:
    # Only a withdrawal ever fills this column, and 20260814_0007 already
    # refuses to downgrade while a withdrawn row exists, so there is nothing
    # here to preserve.
    op.drop_constraint(
        "fk_decisions_source_document_id_documents", "decisions", type_="foreignkey"
    )
    op.drop_column("decisions", "source_document_id")
