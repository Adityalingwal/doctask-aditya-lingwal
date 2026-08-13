"""Add the findings table and the rules each run froze when it started.

A finding carries no answer of its own: it names the decision that gates it and
the answer is read from decisions.outcome, so one answer can be changed until
review finishes without a second copy to keep in step.

Revision ID: 20260813_0006
Revises: 20260813_0005
Create Date: 2026-08-13
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260813_0006"
down_revision: str | None = "20260813_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DECISION_KIND_CHECK = "kind IN ('possible match', 'export', 'finding')"
EARLIER_DECISION_KIND_CHECK = "kind IN ('possible match', 'export')"


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column(
            "rules_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column("runs", sa.Column("rules_fingerprint", sa.Text(), nullable=True))
    op.add_column(
        "runs",
        sa.Column("examined_row_count", sa.Integer(), nullable=True),
    )

    op.drop_constraint("ck_decisions_kind", "decisions", type_="check")
    op.create_check_constraint("ck_decisions_kind", "decisions", DECISION_KIND_CHECK)

    op.create_table(
        "findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("register_row_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", sa.Text(), nullable=False),
        sa.Column("rule_text", sa.Text(), nullable=False),
        sa.Column("issue", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("decision_key", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["runs.id"],
            name="fk_findings_run_id_runs",
        ),
        sa.ForeignKeyConstraint(
            ["register_row_id"],
            ["register_rows.id"],
            name="fk_findings_register_row_id_register_rows",
        ),
        sa.ForeignKeyConstraint(
            ["decision_key"],
            ["decisions.id"],
            name="fk_findings_decision_key_decisions",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_findings"),
        sa.UniqueConstraint("decision_key", name="uq_findings_decision_key"),
    )


def downgrade() -> None:
    op.drop_table("findings")

    op.execute(f"DELETE FROM decisions WHERE NOT ({EARLIER_DECISION_KIND_CHECK})")
    op.drop_constraint("ck_decisions_kind", "decisions", type_="check")
    op.create_check_constraint(
        "ck_decisions_kind",
        "decisions",
        EARLIER_DECISION_KIND_CHECK,
    )

    op.drop_column("runs", "examined_row_count")
    op.drop_column("runs", "rules_fingerprint")
    op.drop_column("runs", "rules_snapshot")
