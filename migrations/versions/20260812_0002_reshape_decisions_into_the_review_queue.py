"""Reshape decisions into the review queue and add the columns a run needs.

Revision ID: 20260812_0002
Revises: 20260812_0001
Create Date: 2026-08-12
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260812_0002"
down_revision: str | None = "20260812_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DECISION_KIND_CHECK = "kind IN ('possible match', 'export')"
DECISION_OUTCOME_CHECK = "outcome IS NULL OR outcome IN ('approved', 'rejected')"


def upgrade() -> None:
    op.drop_constraint("uq_decisions_run_key", "decisions", type_="unique")
    op.drop_column("decisions", "decision_key")
    op.add_column("decisions", sa.Column("kind", sa.Text(), nullable=False))
    op.add_column("decisions", sa.Column("question", sa.Text(), nullable=False))
    op.add_column(
        "decisions",
        sa.Column(
            "proposed_register_row_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "decisions",
        sa.Column(
            "candidate_register_row_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_decisions_proposed_register_row_id_register_rows",
        "decisions",
        "register_rows",
        ["proposed_register_row_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_decisions_candidate_register_row_id_register_rows",
        "decisions",
        "register_rows",
        ["candidate_register_row_id"],
        ["id"],
    )
    op.create_check_constraint("ck_decisions_kind", "decisions", DECISION_KIND_CHECK)
    # A pending question is one row with no answer yet, so the answer columns
    # have to be empty until the Delivery Owner decides.
    op.drop_constraint("ck_decisions_outcome", "decisions", type_="check")
    op.alter_column("decisions", "outcome", nullable=True)
    op.create_check_constraint(
        "ck_decisions_outcome",
        "decisions",
        DECISION_OUTCOME_CHECK,
    )
    op.alter_column(
        "decisions",
        "decided_at",
        nullable=True,
        server_default=None,
    )

    op.add_column(
        "runs",
        sa.Column(
            "skipped",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column("runs", sa.Column("ended_early_reason", sa.Text(), nullable=True))
    op.add_column(
        "runs",
        sa.Column(
            "export_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    op.add_column(
        "documents",
        sa.Column(
            "content_hash",
            sa.Text(),
            server_default=sa.text("''"),
            nullable=False,
        ),
    )
    op.alter_column("documents", "content_hash", server_default=None)
    op.add_column(
        "documents",
        sa.Column(
            "extraction",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    op.add_column(
        "register_rows",
        sa.Column(
            "row_number",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.alter_column("register_rows", "row_number", server_default=None)
    op.create_index(
        "uq_register_rows_number_per_project",
        "register_rows",
        ["project_id", "row_number"],
        unique=True,
    )

    # A cell the system filled with an honest "not known yet" statement was
    # caused by no document, and naming one would misattribute it.
    op.alter_column("audit", "source_document_id", nullable=True)


def downgrade() -> None:
    op.alter_column("audit", "source_document_id", nullable=False)

    op.drop_index("uq_register_rows_number_per_project", table_name="register_rows")
    op.drop_column("register_rows", "row_number")

    op.drop_column("documents", "extraction")
    op.drop_column("documents", "content_hash")

    op.drop_column("runs", "export_json")
    op.drop_column("runs", "ended_early_reason")
    op.drop_column("runs", "skipped")

    op.alter_column(
        "decisions",
        "decided_at",
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    op.drop_constraint("ck_decisions_outcome", "decisions", type_="check")
    op.alter_column("decisions", "outcome", nullable=False)
    op.create_check_constraint(
        "ck_decisions_outcome",
        "decisions",
        "outcome IN ('approved', 'rejected')",
    )
    op.drop_constraint("ck_decisions_kind", "decisions", type_="check")
    op.drop_constraint(
        "fk_decisions_candidate_register_row_id_register_rows",
        "decisions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_decisions_proposed_register_row_id_register_rows",
        "decisions",
        type_="foreignkey",
    )
    op.drop_column("decisions", "candidate_register_row_id")
    op.drop_column("decisions", "proposed_register_row_id")
    op.drop_column("decisions", "question")
    op.drop_column("decisions", "kind")
    op.add_column("decisions", sa.Column("decision_key", sa.Text(), nullable=False))
    op.create_unique_constraint(
        "uq_decisions_run_key",
        "decisions",
        ["run_id", "decision_key"],
    )
