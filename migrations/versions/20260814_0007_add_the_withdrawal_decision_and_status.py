"""Let a row be Withdrawn and let the review queue carry the decision that does it.

A withdrawal is a fourth kind of question in the same queue, answered the same
way, and `Withdrawn` is a seventh row status set only by approving one.

Revision ID: 20260814_0007
Revises: 20260813_0006
Create Date: 2026-08-14
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260814_0007"
down_revision: str | None = "20260813_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DECISION_KIND_CHECK = (
    "kind IN ('possible match', 'export', 'finding', 'withdrawal')"
)
EARLIER_DECISION_KIND_CHECK = "kind IN ('possible match', 'export', 'finding')"
REGISTER_ROW_STATUS_CHECK = (
    "status IN ('Done', 'Partial', 'Never happened', 'Blocked', 'Disputed', "
    "'No evidence yet', 'Withdrawn')"
)
EARLIER_REGISTER_ROW_STATUS_CHECK = (
    "status IN ('Done', 'Partial', 'Never happened', 'Blocked', 'Disputed', "
    "'No evidence yet')"
)


def upgrade() -> None:
    op.drop_constraint("ck_decisions_kind", "decisions", type_="check")
    op.create_check_constraint("ck_decisions_kind", "decisions", DECISION_KIND_CHECK)

    op.drop_constraint("ck_register_rows_status", "register_rows", type_="check")
    op.create_check_constraint(
        "ck_register_rows_status",
        "register_rows",
        REGISTER_ROW_STATUS_CHECK,
    )


def downgrade() -> None:
    # A withdrawn row cannot come back down. The earlier shape has no status
    # that means "the client stopped asking for this", and the two ways to
    # force one are both dishonest: deleting the row destroys the history this
    # decision exists to keep, and any other status claims something the
    # evidence does not support. So this says so and stops.
    withdrawn = (
        op.get_bind()
        .execute(
            sa.text("SELECT COUNT(*) FROM register_rows WHERE status = 'Withdrawn'")
        )
        .scalar()
    )
    if withdrawn:
        raise RuntimeError(
            f"{withdrawn} register row(s) are 'Withdrawn' and the earlier "
            "schema has no status that means it, so this downgrade would have "
            "to either delete those rows or claim something their evidence "
            "does not support. Decide what each of those rows should say "
            "instead, change its status, then run this downgrade again."
        )

    # A withdrawal question a person already answered goes with the constraint,
    # exactly as the findings migration before it drops what it cannot hold.
    op.execute(f"DELETE FROM decisions WHERE NOT ({EARLIER_DECISION_KIND_CHECK})")
    op.drop_constraint("ck_decisions_kind", "decisions", type_="check")
    op.create_check_constraint(
        "ck_decisions_kind",
        "decisions",
        EARLIER_DECISION_KIND_CHECK,
    )

    op.drop_constraint("ck_register_rows_status", "register_rows", type_="check")
    op.create_check_constraint(
        "ck_register_rows_status",
        "register_rows",
        EARLIER_REGISTER_ROW_STATUS_CHECK,
    )
