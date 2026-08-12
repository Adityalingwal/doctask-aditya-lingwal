"""Create the seven slice 1 tables.

Revision ID: 20260812_0001
Revises:
Create Date: 2026-08-12
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260812_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RUN_STATUS_CHECK = (
    "status IN ('waiting', 'running', 'waiting for review', 'done', "
    "'closed without export')"
)
REGISTER_ROW_STATUS_CHECK = (
    "status IN ('Done', 'Partial', 'Never happened', 'Blocked', 'Disputed', "
    "'No evidence yet')"
)
REGISTER_CELL_CHECK = (
    "cell_name IN ('what_was_asked', 'in_writing', 'what_testing_found', "
    "'status', 'blocked_on', 'first_seen', 'last_moved')"
)


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("source_folder_path", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_projects"),
    )

    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("current_stage", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "stage_timings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "estimated_cost_usd",
            sa.Numeric(precision=12, scale=6),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(RUN_STATUS_CHECK, name="ck_runs_status"),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_runs_project_id_projects",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_runs"),
    )
    op.create_index(
        "uq_runs_one_active_per_project",
        "runs",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('running', 'waiting for review')"),
    )
    op.create_index(
        "uq_runs_one_waiting_per_project",
        "runs",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("status = 'waiting'"),
    )

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["runs.id"],
            name="fk_documents_run_id_runs",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
    )

    op.create_table(
        "register_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("what_was_asked", sa.Text(), nullable=False),
        sa.Column("in_writing", sa.Text(), nullable=False),
        sa.Column("what_testing_found", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("blocked_on", sa.Text(), nullable=False),
        sa.Column("first_seen", sa.Text(), nullable=False),
        sa.Column("last_moved", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("proposed_by_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "is_committed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            REGISTER_ROW_STATUS_CHECK,
            name="ck_register_rows_status",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_register_rows_project_id_projects",
        ),
        sa.ForeignKeyConstraint(
            ["proposed_by_run_id"],
            ["runs.id"],
            name="fk_register_rows_proposed_by_run_id_runs",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_register_rows"),
    )

    op.create_table(
        "citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("register_row_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cell_name", sa.Text(), nullable=False),
        sa.Column("source_file", sa.Text(), nullable=False),
        sa.Column("source_place", sa.Text(), nullable=True),
        sa.Column("source_words", sa.Text(), nullable=True),
        sa.Column("absence_statement", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(REGISTER_CELL_CHECK, name="ck_citations_cell_name"),
        sa.CheckConstraint(
            "(source_place IS NOT NULL AND source_words IS NOT NULL "
            "AND absence_statement IS NULL) OR "
            "(source_place IS NULL AND source_words IS NULL "
            "AND absence_statement IS NOT NULL)",
            name="ck_citations_present_or_absent_evidence",
        ),
        sa.ForeignKeyConstraint(
            ["register_row_id"],
            ["register_rows.id"],
            name="fk_citations_register_row_id_register_rows",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_citations"),
    )

    op.create_table(
        "decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_key", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "outcome IN ('approved', 'rejected')",
            name="ck_decisions_outcome",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["runs.id"],
            name="fk_decisions_run_id_runs",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_decisions"),
        sa.UniqueConstraint("run_id", "decision_key", name="uq_decisions_run_key"),
    )

    op.create_table(
        "audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("register_row_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cell_name", sa.Text(), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(REGISTER_CELL_CHECK, name="ck_audit_cell_name"),
        sa.ForeignKeyConstraint(
            ["register_row_id"],
            ["register_rows.id"],
            name="fk_audit_register_row_id_register_rows",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["runs.id"],
            name="fk_audit_run_id_runs",
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["documents.id"],
            name="fk_audit_source_document_id_documents",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit"),
    )


def downgrade() -> None:
    op.drop_table("audit")
    op.drop_table("decisions")
    op.drop_table("citations")
    op.drop_table("register_rows")
    op.drop_table("documents")
    op.drop_index("uq_runs_one_waiting_per_project", table_name="runs")
    op.drop_index("uq_runs_one_active_per_project", table_name="runs")
    op.drop_table("runs")
    op.drop_table("projects")
