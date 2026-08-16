"""Let a run hold the row moves it proposes, and ask about one it is unsure of.

A testing observation or a piece of delivery evidence moves a row that already
exists. The move cannot be written when it is worked out: the register is the
committed rows, and this run's changes reach them only after the Delivery Owner
approves the export. So the move is worked out before Examine — which has to
judge the register as this run leaves it — stored on the run, and applied
inside Commit's own transaction.

`observation match` joins the decision kinds for the same reason a possible
match is asked about: attaching this batch's evidence to a committed row
changes what that row says, and D02 scenario 3 gates exactly that. It cannot
reuse `possible match`, which names a proposed row an observation does not
have.

Revision ID: 20260816_0015
Revises: 20260816_0014
Create Date: 2026-08-16
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260816_0015"
down_revision: str | None = "20260816_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DECISION_KIND_CHECK = (
    "kind IN ('possible match', 'export', 'finding', 'observation match')"
)
EARLIER_DECISION_KIND_CHECK = "kind IN ('possible match', 'export', 'finding')"


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column(
            "pending_moves",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.drop_constraint("ck_decisions_kind", "decisions", type_="check")
    op.create_check_constraint("ck_decisions_kind", "decisions", DECISION_KIND_CHECK)


def downgrade() -> None:
    # A question a person already answered goes with the constraint that can no
    # longer hold it, the same way 20260814_0011's upgrade drops what an
    # earlier shape cannot represent.
    op.execute(f"DELETE FROM decisions WHERE NOT ({EARLIER_DECISION_KIND_CHECK})")
    op.drop_constraint("ck_decisions_kind", "decisions", type_="check")
    op.create_check_constraint(
        "ck_decisions_kind", "decisions", EARLIER_DECISION_KIND_CHECK
    )
    op.drop_column("runs", "pending_moves")
