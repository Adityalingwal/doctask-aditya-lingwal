"""Let audit hold an attachment event as well as a cell change.

A finding attaches to a row rather than to a cell, so there is no honest cell
name to write for it. The downgrade drops the attachment rows first, because
the older shape cannot represent an event that names no cell.

Revision ID: 20260813_0005
Revises: 20260813_0004
Create Date: 2026-08-13
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260813_0005"
down_revision: str | None = "20260813_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CELL_CHANGE_EVENT = "cell change"
ATTACHMENT_EVENT = "attachment"
AUDIT_EVENT_KIND_CHECK = (
    f"event_kind IN ('{CELL_CHANGE_EVENT}', '{ATTACHMENT_EVENT}')"
)
EARLIER_REGISTER_CELL_CHECK = (
    "cell_name IN ('what_was_asked', 'in_writing', 'what_testing_found', "
    "'status', 'blocked_on', 'first_seen', 'last_moved')"
)
# cell_name IS NOT NULL is not redundant: without it a null cell_name makes the
# IN test null, the whole condition null, and PostgreSQL accepts a null check.
AUDIT_CELL_NAME_CHECK = (
    f"(event_kind = '{CELL_CHANGE_EVENT}' AND cell_name IS NOT NULL "
    f"AND {EARLIER_REGISTER_CELL_CHECK}) "
    f"OR (event_kind = '{ATTACHMENT_EVENT}' AND cell_name IS NULL)"
)


def upgrade() -> None:
    op.add_column("audit", sa.Column("event_kind", sa.Text(), nullable=True))
    op.execute(f"UPDATE audit SET event_kind = '{CELL_CHANGE_EVENT}'")
    op.alter_column("audit", "event_kind", nullable=False)
    op.alter_column("audit", "cell_name", nullable=True)

    op.drop_constraint("ck_audit_cell_name", "audit", type_="check")
    op.create_check_constraint(
        "ck_audit_event_kind",
        "audit",
        AUDIT_EVENT_KIND_CHECK,
    )
    op.create_check_constraint("ck_audit_cell_name", "audit", AUDIT_CELL_NAME_CHECK)


def downgrade() -> None:
    op.execute(f"DELETE FROM audit WHERE event_kind = '{ATTACHMENT_EVENT}'")

    op.drop_constraint("ck_audit_cell_name", "audit", type_="check")
    op.drop_constraint("ck_audit_event_kind", "audit", type_="check")
    op.create_check_constraint(
        "ck_audit_cell_name",
        "audit",
        EARLIER_REGISTER_CELL_CHECK,
    )
    op.alter_column("audit", "cell_name", nullable=False)
    op.drop_column("audit", "event_kind")
