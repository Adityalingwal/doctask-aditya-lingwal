"""Allow a reviewed client scope exclusion to be recorded on a row.

An explicit statement that work is outside approved scope is neither a
positive requirement nor evidence that delivery failed. The existing Status
cell answers where an ask stands, so `Excluded` records that boundary without
adding a fifth register cell.

Revision ID: 20260825_0026
Revises: 20260823_0025
Create Date: 2026-08-25
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op


revision: str = "20260825_0026"
down_revision: str | None = "20260823_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_NAME = "ck_register_rows_status"
WITH_EXCLUDED = (
    "status IN ('Done', 'Partial', 'Not delivered', 'Handed over', "
    "'Disputed', 'Requested', 'Excluded')"
)
WITHOUT_EXCLUDED = (
    "status IN ('Done', 'Partial', 'Not delivered', 'Handed over', "
    "'Disputed', 'Requested')"
)


def upgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "register_rows", type_="check")
    op.create_check_constraint(CONSTRAINT_NAME, "register_rows", WITH_EXCLUDED)


def downgrade() -> None:
    op.execute(
        "UPDATE register_rows SET status = 'Requested' WHERE status = 'Excluded'"
    )
    op.drop_constraint(CONSTRAINT_NAME, "register_rows", type_="check")
    op.create_check_constraint(CONSTRAINT_NAME, "register_rows", WITHOUT_EXCLUDED)
