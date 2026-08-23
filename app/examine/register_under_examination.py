from __future__ import annotations

from typing import Any, NamedTuple
from uuid import UUID

from psycopg import AsyncConnection

from app.register.absence_rows import is_absence
from app.register.cells import CELL_NAMES, IN_WRITING, in_writing_says_yes
from app.review.review_queue import POSSIBLE_MATCH_DECISION


async def register_under_examination(
    connection: AsyncConnection,
    project_id: UUID,
    run_id: UUID,
) -> list[dict[str, Any]]:
    """The register as this run leaves it: committed rows plus its own proposals.

    A proposal is examined before it is committed, because a finding a person
    only sees after the export has been approved is a finding raised too late.

    A proposal still waiting on a possible-match answer is not a row of its
    own here. Counting it as one made a seven-row register read as thirteen
    and attached findings to rows that were about to be merged away. It is
    assumed to be the match it was asked about, and what it would write is
    overlaid on the row it would join.

    **Limitation:** if the person later rejects that match, the proposal
    becomes a row of its own that this run never examined, so no finding is
    raised on it in this run. The next run examines it like any other row.
    """
    result = await connection.execute(
        "SELECT id, row_number, " + ", ".join(CELL_NAMES) + " FROM register_rows "
        "WHERE project_id = %s AND (is_committed OR proposed_by_run_id = %s) "
        "AND merged_into_register_row_id IS NULL ORDER BY row_number",
        (project_id, run_id),
    )
    rows = list(await result.fetchall())
    if not rows:
        return []

    lands_on = await _rows_an_unanswered_proposal_would_join(connection, run_id)
    row_by_id = {row["id"]: row for row in rows}
    examined = [row for row in rows if row["id"] not in lands_on]

    cited_cells = await _cited_cells_by_row(
        connection, [row["id"] for row in examined]
    )
    moved = await _cells_this_run_moves(connection, run_id)
    assumed = _cells_an_assumed_match_writes(lands_on, row_by_id)
    return [
        {
            "id": row["id"],
            "row_number": row["row_number"],
            "cells": {name: row[name] for name in CELL_NAMES}
            | moved.values_by_row.get(str(row["id"]), {})
            | assumed.values_by_row.get(str(row["id"]), {}),
            "cited_cells": cited_cells.get(row["id"], frozenset())
            | moved.cited_cells_by_row.get(str(row["id"]), frozenset())
            | assumed.cited_cells_by_row.get(str(row["id"]), frozenset()),
        }
        for row in examined
    ]


class PendingMoves(NamedTuple):
    values_by_row: dict[str, dict[str, str]]
    cited_cells_by_row: dict[str, frozenset[str]]


async def _rows_an_unanswered_proposal_would_join(
    connection: AsyncConnection,
    run_id: UUID,
) -> dict[UUID, UUID]:
    """Each proposal still awaiting a match answer, and the row it would join.

    Both hops are followed. A proposal may be asked about against another
    proposal of this same batch, which may itself be awaiting an answer, and a
    candidate may have been merged away already — a marker is never two hops
    from the row holding the evidence (D09), so one COALESCE reaches it.
    """
    result = await connection.execute(
        "SELECT decisions.proposed_register_row_id AS proposal, "
        "COALESCE(candidate.merged_into_register_row_id, candidate.id) AS candidate "
        "FROM decisions JOIN register_rows AS candidate "
        "ON candidate.id = decisions.candidate_register_row_id "
        "WHERE decisions.run_id = %s AND decisions.kind = %s "
        "AND decisions.outcome IS NULL",
        (run_id, POSSIBLE_MATCH_DECISION),
    )
    awaiting = {
        decision["proposal"]: decision["candidate"]
        for decision in await result.fetchall()
    }
    return {
        proposal: _followed_to_the_end(proposal, awaiting) for proposal in awaiting
    }


def _followed_to_the_end(proposal: UUID, awaiting: dict[UUID, UUID]) -> UUID:
    seen = {proposal}
    joins = awaiting[proposal]
    while joins in awaiting and joins not in seen:
        seen.add(joins)
        joins = awaiting[joins]
    return joins


def _cells_an_assumed_match_writes(
    lands_on: dict[UUID, UUID],
    row_by_id: dict[UUID, dict[str, Any]],
) -> PendingMoves:
    """What approving each unanswered match would leave the joined row holding.

    Only `Written down` moves on a merge (D09), and only towards `Yes`: the
    arriving requirement can say the ask is written down and cannot say it is
    not. Its citation travels with it, or a rule would see the row claim the
    ask is in writing with nothing behind the claim.
    """
    values: dict[str, dict[str, str]] = {}
    cited: dict[str, set[str]] = {}
    for proposal_id, candidate_id in lands_on.items():
        proposal = row_by_id.get(proposal_id)
        if proposal is None or candidate_id not in row_by_id:
            continue
        if not in_writing_says_yes(proposal[IN_WRITING]):
            continue
        values.setdefault(str(candidate_id), {})[IN_WRITING] = proposal[IN_WRITING]
        cited.setdefault(str(candidate_id), set()).add(IN_WRITING)
    return PendingMoves(
        values_by_row=values,
        cited_cells_by_row={
            row_id: frozenset(cells) for row_id, cells in cited.items()
        },
    )


async def _cells_this_run_moves(
    connection: AsyncConnection,
    run_id: UUID,
) -> PendingMoves:
    """What this run's moves will leave each row holding, once Commit runs.

    A move is not written to the row until Commit, so a rule judging the
    stored cells alone would raise a finding against evidence this very batch
    supplied — and a finding a person only sees after approving the export is
    raised too late.

    The citations travel with the values for the same reason. A rule that saw
    `status` reach `Done` but not the testing citation that moved it there
    would report the row as Done with no testing outcome — a finding against
    the very evidence in front of it.
    """
    result = await connection.execute(
        "SELECT pending_moves FROM runs WHERE id = %s", (run_id,)
    )
    stored = await result.fetchone()
    values: dict[str, dict[str, str]] = {}
    cited: dict[str, set[str]] = {}
    # An absence first, then the observation's move on the same cell: a move
    # still awaiting its answer is assumed approved here, exactly as an
    # unanswered possible match is assumed to be the match.
    for move in sorted(
        (stored["pending_moves"] if stored else []) or [], key=lambda m: not is_absence(m)
    ):
        row_id = move["register_row_id"]
        values.setdefault(row_id, {})[move["cell"]] = move["value"]
        if move["citations"]:
            cited.setdefault(row_id, set()).add(move["cell"])
    return PendingMoves(
        values_by_row=values,
        cited_cells_by_row={
            row_id: frozenset(cells) for row_id, cells in cited.items()
        },
    )


async def _cited_cells_by_row(
    connection: AsyncConnection,
    register_row_ids: list[UUID],
) -> dict[UUID, frozenset[str]]:
    result = await connection.execute(
        "SELECT register_row_id, cell_name FROM citations "
        "WHERE register_row_id = ANY(%s)",
        (register_row_ids,),
    )
    cited: dict[UUID, set[str]] = {}
    for citation in await result.fetchall():
        cited.setdefault(citation["register_row_id"], set()).add(
            citation["cell_name"]
        )
    return {row_id: frozenset(cells) for row_id, cells in cited.items()}
