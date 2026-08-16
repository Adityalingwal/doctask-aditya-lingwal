"""Narrow the register row to four cells, and swap `Blocked` for `Handed over`.

`Blocked on`, `First seen` and `Last moved` are removed: no rule and no code
branch reads the first two, and the third fed only a rule of our own. `Blocked`
goes with `Blocked on`, which was the only cell that could say what the work
was waiting for, and `Handed over` arrives in its place — a handover says the
work exists, which is neither `No evidence yet` nor `Done`.

Every stored row's fingerprint moves, because `fingerprint_of_cells` hashes the
cell list and the list is now four names. That is expected and is not
corruption. No fingerprint is recomputed here: the next run that touches a row
writes the right one, and a migration that computes a hash would have to know
the application's rules.

A row currently holding `Blocked` has no status it could honestly become, so
`upgrade()` counts those rows, names them, and refuses — the shape
`20260814_0011` used for `Withdrawn`, going one step further by naming each
row_number the way `20260815_0013` named the project ids it refused on.
`downgrade()` only widens the constraint, so it refuses nothing.

`ck_citations_cell_name` and `ck_audit_cell_name` are deliberately left as they
are. Audit rows naming a dropped cell are history and must survive, and
narrowing the citations check would buy nothing now that no code writes one.

Revision ID: 20260817_0017
Revises: 20260816_0016
Create Date: 2026-08-17
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260817_0017"
down_revision: str | None = "20260816_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_NAME = "ck_register_rows_status"
BLOCKED_STATUS = "Blocked"
DROPPED_CELLS = ("blocked_on", "first_seen", "last_moved")

FOUR_CELL_STATUS_CHECK = (
    "status IN ('Done', 'Partial', 'Not delivered', 'Handed over', "
    "'Disputed', 'No evidence yet')"
)
# The downgrade widens rather than narrows, the way `20260814_0011`'s does:
# it puts `Blocked` back without taking `Handed over` away, because a row
# written since this migration ran may be holding `Handed over` and a
# downgrade that refused on it would be a narrowing with no honest answer.
WIDENED_STATUS_CHECK = (
    "status IN ('Done', 'Partial', 'Not delivered', 'Blocked', 'Handed over', "
    "'Disputed', 'No evidence yet')"
)

# What each restored column says when a downgrade brings it back. The values
# the rows held are gone, so the honest answer is the sentence the system
# wrote when it knew nothing — never a guess at what the cell used to say.
RESTORED_CELL_VALUES = {
    "blocked_on": (
        "Not known yet — no source read so far reports work stopped on this "
        "requirement."
    ),
    "first_seen": "date unknown",
    "last_moved": "date unknown",
}


def upgrade() -> None:
    blocked = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT row_number FROM register_rows WHERE status = :blocked "
                "ORDER BY row_number"
            ).bindparams(blocked=BLOCKED_STATUS)
        )
        .scalars()
        .all()
    )
    if blocked:
        named = ", ".join(f"#{row_number}" for row_number in blocked)
        raise RuntimeError(
            f"{len(blocked)} register row(s) are '{BLOCKED_STATUS}' — {named} — "
            "and the new schema removes that status along with the 'Blocked on' "
            "cell that explained it, so this migration would have to either "
            "rewrite those rows or claim something their evidence does not "
            "support. Decide what each of those rows should say instead, change "
            "its status, then run this migration again."
        )

    op.execute(
        "DELETE FROM citations WHERE cell_name IN ("
        + ", ".join(f"'{cell_name}'" for cell_name in DROPPED_CELLS)
        + ")"
    )
    for cell_name in DROPPED_CELLS:
        op.drop_column("register_rows", cell_name)

    op.drop_constraint(CONSTRAINT_NAME, "register_rows", type_="check")
    op.create_check_constraint(
        CONSTRAINT_NAME, "register_rows", FOUR_CELL_STATUS_CHECK
    )


def downgrade() -> None:
    # Widening never violates existing data, so nothing here needs to refuse.
    op.drop_constraint(CONSTRAINT_NAME, "register_rows", type_="check")
    op.create_check_constraint(
        CONSTRAINT_NAME, "register_rows", WIDENED_STATUS_CHECK
    )

    for cell_name, unknown_value in RESTORED_CELL_VALUES.items():
        op.add_column(
            "register_rows",
            sa.Column(
                cell_name,
                sa.Text(),
                nullable=False,
                server_default=unknown_value,
            ),
        )
        op.alter_column("register_rows", cell_name, server_default=None)
