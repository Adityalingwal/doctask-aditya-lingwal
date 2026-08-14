"""Remove the withdrawal decision, the Withdrawn status, and its document column.

Withdrawal is removed, not disabled: a document is now read once per project,
by name or content, so a document can no longer be re-read to notice it
stopped asking for something. Narrowing both check constraints back can fail
against a database that already holds an answered withdrawal, so this mirrors
20260814_0007's own approach to a narrower constraint: a decision row that
would violate the narrower kind check is deleted (it is a review-queue
question, not register history), and a register row already `Withdrawn` makes
this migration refuse rather than delete or reguess its status, the same way
20260814_0007's downgrade refuses rather than force one into a shape that
cannot represent it.

Revision ID: 20260814_0011
Revises: 20260814_0010
Create Date: 2026-08-15
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260814_0011"
down_revision: str | None = "20260814_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DECISION_KIND_CHECK = "kind IN ('possible match', 'export', 'finding')"
WITH_WITHDRAWAL_DECISION_KIND_CHECK = (
    "kind IN ('possible match', 'export', 'finding', 'withdrawal')"
)
REGISTER_ROW_STATUS_CHECK = (
    "status IN ('Done', 'Partial', 'Never happened', 'Blocked', 'Disputed', "
    "'No evidence yet')"
)
WITH_WITHDRAWN_REGISTER_ROW_STATUS_CHECK = (
    "status IN ('Done', 'Partial', 'Never happened', 'Blocked', 'Disputed', "
    "'No evidence yet', 'Withdrawn')"
)


def upgrade() -> None:
    # A withdrawal question a person already answered goes with the
    # constraint, the same way 20260814_0007's downgrade drops what an
    # earlier shape cannot hold.
    op.execute(f"DELETE FROM decisions WHERE NOT ({DECISION_KIND_CHECK})")
    op.drop_constraint("ck_decisions_kind", "decisions", type_="check")
    op.create_check_constraint("ck_decisions_kind", "decisions", DECISION_KIND_CHECK)

    op.drop_constraint(
        "fk_decisions_source_document_id_documents", "decisions", type_="foreignkey"
    )
    op.drop_column("decisions", "source_document_id")

    # A `Withdrawn` row cannot be quietly narrowed away. Deleting it destroys
    # the history this decision exists to keep, and no other status is honest
    # — exactly why 20260814_0007's own downgrade refuses instead of guessing.
    withdrawn = (
        op.get_bind()
        .execute(
            sa.text("SELECT COUNT(*) FROM register_rows WHERE status = 'Withdrawn'")
        )
        .scalar()
    )
    if withdrawn:
        raise RuntimeError(
            f"{withdrawn} register row(s) are 'Withdrawn' and the new schema "
            "removes that status entirely, so this migration would have to "
            "either delete those rows or claim something their evidence does "
            "not support. Decide what each of those rows should say instead, "
            "change its status, then run this migration again."
        )

    op.drop_constraint("ck_register_rows_status", "register_rows", type_="check")
    op.create_check_constraint(
        "ck_register_rows_status",
        "register_rows",
        REGISTER_ROW_STATUS_CHECK,
    )


def downgrade() -> None:
    # Widening never violates existing data, so nothing here needs to refuse
    # or delete anything.
    op.drop_constraint("ck_register_rows_status", "register_rows", type_="check")
    op.create_check_constraint(
        "ck_register_rows_status",
        "register_rows",
        WITH_WITHDRAWN_REGISTER_ROW_STATUS_CHECK,
    )

    op.add_column(
        "decisions",
        sa.Column(
            "source_document_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
    )
    op.create_foreign_key(
        "fk_decisions_source_document_id_documents",
        "decisions",
        "documents",
        ["source_document_id"],
        ["id"],
    )

    op.drop_constraint("ck_decisions_kind", "decisions", type_="check")
    op.create_check_constraint(
        "ck_decisions_kind",
        "decisions",
        WITH_WITHDRAWAL_DECISION_KIND_CHECK,
    )
