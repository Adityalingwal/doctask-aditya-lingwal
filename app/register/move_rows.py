from __future__ import annotations

from typing import Any, NamedTuple
from uuid import UUID

from langchain_core.language_models import BaseChatModel
from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from app.extract.answer import TestingLabel
from app.match.match_requirements import NEW_ROW, POSSIBLE_MATCH, match_observations
from app.register.audit_entries import write_cell_change
from app.register.cells import (
    BLOCKED_ON,
    CELL_NAMES,
    DATE_UNKNOWN,
    LAST_MOVED,
    STATUS,
    STATUS_BLOCKED,
    STATUS_DISPUTED,
    STATUS_DONE,
    STATUS_NOT_DELIVERED,
    STATUS_PARTIAL,
    WHAT_TESTING_FOUND,
    fingerprint_of_cells,
)
from app.review.review_queue import (
    APPROVED,
    OBSERVATION_MATCH_DECISION,
    raise_observation_match_decision,
)


TESTING_OBSERVATION = "testing observation"
DELIVERY_EVIDENCE = "delivery evidence"
BLOCKER = "blocker"
SKIPPED_OBSERVATION_KIND = "observation"


class ProposedMoves(NamedTuple):
    moved_row_numbers: list[int]
    gated_row_numbers: list[int]
    unmatched: list[dict[str, str]]


async def observations_of_batch(
    connection: AsyncConnection,
    run_id: UUID,
) -> list[dict[str, Any]]:
    """Everything this batch says about work already asked for, in read order."""
    result = await connection.execute(
        "SELECT extraction FROM documents WHERE run_id = %s AND "
        "extraction IS NOT NULL ORDER BY source_path",
        (run_id,),
    )
    observations: list[dict[str, Any]] = []
    for document in await result.fetchall():
        extraction = document["extraction"]
        for kind, list_name in (
            (TESTING_OBSERVATION, "testing_observations"),
            (DELIVERY_EVIDENCE, "delivery_evidence"),
            (BLOCKER, "blockers"),
        ):
            for observed in extraction.get(list_name, []):
                observations.append(
                    {
                        **observed,
                        "kind": kind,
                        "document_date": extraction["document_date"],
                    }
                )
    return observations


async def rows_a_move_may_reach(
    connection: AsyncConnection,
    project_id: UUID,
    run_id: UUID,
) -> list[dict[str, Any]]:
    """The register as this run leaves it: committed rows plus its own proposals.

    A row created and moved inside one batch is the ordinary case when a
    project is added over a folder that already holds all four kinds of
    document, so this run's own proposals have to be reachable too.
    """
    result = await connection.execute(
        "SELECT id, row_number, what_was_asked, status, is_committed "
        "FROM register_rows WHERE project_id = %s "
        "AND (is_committed OR proposed_by_run_id = %s) "
        "AND merged_into_register_row_id IS NULL ORDER BY row_number",
        (project_id, run_id),
    )
    return list(await result.fetchall())


async def propose_moves(
    connection: AsyncConnection,
    model_client: BaseChatModel,
    run_id: UUID,
    project_id: UUID,
) -> ProposedMoves:
    """Work out which row each observation moves, and store the moves on the run.

    Nothing is written to a row here. The register is the committed rows, and
    this run reaches them only through Commit, after the Delivery Owner has
    approved the export.
    """
    observations = await observations_of_batch(connection, run_id)
    if not observations:
        return ProposedMoves([], [], [])

    rows = await rows_a_move_may_reach(connection, project_id, run_id)
    if not rows:
        return ProposedMoves([], [], _unmatched_entries(observations))

    answer = await match_observations(model_client, rows, observations)
    row_by_number = {row["row_number"]: row for row in rows}

    observations_by_row: dict[int, list[dict[str, Any]]] = {}
    ask_about: set[int] = set()
    unmatched: list[dict[str, str]] = []
    for outcome in answer.outcomes:
        observation = observations[outcome.observation_index]
        row = row_by_number.get(outcome.row_number or -1)
        if outcome.outcome == NEW_ROW or row is None:
            unmatched.append(_unmatched_entry(observation))
            continue
        # Doubt goes to a person however new the row is, and attaching this
        # batch's evidence to a committed row changes what that row says —
        # D02 scenario 3. A confident link to a row this same batch proposed
        # is covered by the export gate, like the proposal itself.
        if outcome.outcome == POSSIBLE_MATCH or row["is_committed"]:
            ask_about.add(row["row_number"])
        observations_by_row.setdefault(row["row_number"], []).append(observation)

    return await _store_the_moves(
        connection, run_id, row_by_number, observations_by_row, ask_about, unmatched
    )


async def _store_the_moves(
    connection: AsyncConnection,
    run_id: UUID,
    row_by_number: dict[int, dict[str, Any]],
    observations_by_row: dict[int, list[dict[str, Any]]],
    ask_about: set[int],
    unmatched: list[dict[str, str]],
) -> ProposedMoves:
    moves: list[dict[str, Any]] = []
    moved_row_numbers: list[int] = []
    gated_row_numbers: list[int] = []

    async with connection.transaction():
        # Extract and this node are both replayed from their start on resume,
        # so the moves are set rather than appended and this run's own
        # unanswered questions are cleared first — a second pass replaces its
        # earlier answer instead of asking twice.
        await connection.execute(
            "DELETE FROM decisions WHERE run_id = %s AND kind = %s "
            "AND outcome IS NULL",
            (run_id, OBSERVATION_MATCH_DECISION),
        )
        for row_number in sorted(observations_by_row):
            row = row_by_number[row_number]
            cells = _cells_the_observations_move(observations_by_row[row_number])
            if not cells:
                continue
            decision_id = None
            if row_number in ask_about:
                decision_id = await raise_observation_match_decision(
                    connection,
                    run_id,
                    _attach_question(row, observations_by_row[row_number]),
                    row["id"],
                )
                gated_row_numbers.append(row_number)
            moved_row_numbers.append(row_number)
            for cell_name, value, citations in cells:
                moves.append(
                    {
                        "register_row_id": str(row["id"]),
                        "cell": cell_name,
                        "value": value,
                        "citations": citations,
                        "decision_id": str(decision_id) if decision_id else None,
                    }
                )
        await connection.execute(
            "UPDATE runs SET pending_moves = %s WHERE id = %s",
            (Jsonb(moves), run_id),
        )
    return ProposedMoves(moved_row_numbers, gated_row_numbers, unmatched)


def _cells_the_observations_move(
    observations: list[dict[str, Any]],
) -> list[tuple[str, str, list[dict[str, str]]]]:
    """Which cells one row's observations move, and the evidence for each."""
    testing = [one for one in observations if one["kind"] == TESTING_OBSERVATION]
    blockers = [one for one in observations if one["kind"] == BLOCKER]

    moved: list[tuple[str, str, list[dict[str, str]]]] = []
    if testing:
        moved.append(
            (WHAT_TESTING_FOUND, _joined(testing), _citations_of(testing))
        )
    if blockers:
        moved.append((BLOCKED_ON, _joined(blockers), _citations_of(blockers)))

    delivery_claimed = any(
        one["kind"] == DELIVERY_EVIDENCE for one in observations
    )
    status = status_after(testing, bool(blockers), delivery_claimed)
    if status is not None:
        moved.append((STATUS, status, _citations_of(testing + blockers)))

    # The date of the document that last changed this row. Several documents
    # can move one row in a batch; the last one read is the one whose date the
    # cell carries, which is why documents are read in a stable order. A
    # handover stating no date still moved this row, so the cell says the date
    # is unknown rather than the row reporting no move at all.
    dated = [one for one in observations if one["document_date"] is not None]
    if dated:
        last_date = dated[-1]["document_date"]
        moved.append((LAST_MOVED, last_date["summary"], [_citation(last_date)]))
    elif observations:
        moved.append((LAST_MOVED, DATE_UNKNOWN, []))
    return moved


def status_after(
    testing: list[dict[str, Any]],
    work_is_stopped: bool,
    delivery_claimed: bool,
) -> str | None:
    """The status this row's evidence lands on, or None when nothing moves it.

    `Change request` and `Unclear` move nothing: a new ask arriving during
    testing is not a verdict on the work, and a note with no verdict is not
    one either. Delivery evidence alone moves nothing for the same reason —
    a handover says the work exists, never that it behaves as asked.

    `Not found` is the one label whose meaning depends on what else was read.
    Testing reporting the work absent while a handover claims it was handed
    over is two claims that oppose each other, which is `Disputed`. The same
    report with no handover behind it contradicts nothing — silence is not a
    claim — so it is `Not delivered`.
    """
    if work_is_stopped:
        return STATUS_BLOCKED
    labels = {one["label"] for one in testing}
    if TestingLabel.NOT_FOUND in labels:
        return STATUS_DISPUTED if delivery_claimed else STATUS_NOT_DELIVERED
    if TestingLabel.DEFECT in labels:
        return STATUS_PARTIAL
    if TestingLabel.PASSED in labels:
        return STATUS_DONE
    return None


def _joined(observations: list[dict[str, Any]]) -> str:
    return " ".join(one["summary"] for one in observations)


def _citations_of(observations: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [_citation(one) for one in observations]


def _citation(observed: dict[str, Any]) -> dict[str, str]:
    return {
        "source_file": observed["source_file"],
        "place": observed["place"],
        "source_words": observed["source_words"],
    }


def _attach_question(
    row: dict[str, Any],
    observations: list[dict[str, Any]],
) -> str:
    # The sentence is the record: an audit must show what the person actually
    # read when they answered, not a pointer to a row that has moved on since.
    reported = "; ".join(
        f"{one['summary']} (from {one['source_file']})" for one in observations
    )
    return (
        f"Attach to row #{row['row_number']} — {row['what_was_asked']}: "
        f"{reported}?"
    )


def _unmatched_entries(observations: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [_unmatched_entry(observation) for observation in observations]


def _unmatched_entry(observation: dict[str, Any]) -> dict[str, str]:
    return {
        "kind": SKIPPED_OBSERVATION_KIND,
        "file": observation["source_file"],
        "summary": observation["summary"],
        "reason": (
            f"This {observation['kind']} is about no requirement the register "
            "traces, so it was reported rather than attached to a row."
        ),
    }


async def apply_moves(
    connection: AsyncConnection,
    run_id: UUID,
    document_id_by_file: dict[str, UUID],
) -> list[int]:
    """Write this run's approved moves onto their rows, inside Commit.

    A move whose question was rejected is left where it is: the run record
    keeps it, and the register does not take it.
    """
    result = await connection.execute(
        "SELECT pending_moves FROM runs WHERE id = %s", (run_id,)
    )
    stored = await result.fetchone()
    moves = stored["pending_moves"] if stored else []
    if not moves:
        return []

    rejected = await _rejected_decision_ids(connection, run_id)
    moved_row_numbers: list[int] = []
    for register_row_id, its_moves in _by_row(moves, rejected).items():
        row_number = await _write_one_rows_moves(
            connection, register_row_id, its_moves, run_id, document_id_by_file
        )
        if row_number is not None:
            moved_row_numbers.append(row_number)
    return sorted(moved_row_numbers)


def _by_row(
    moves: list[dict[str, Any]],
    rejected: set[str],
) -> dict[str, list[dict[str, Any]]]:
    by_row: dict[str, list[dict[str, Any]]] = {}
    for move in moves:
        if move["decision_id"] in rejected:
            continue
        by_row.setdefault(move["register_row_id"], []).append(move)
    return by_row


async def _rejected_decision_ids(
    connection: AsyncConnection,
    run_id: UUID,
) -> set[str]:
    result = await connection.execute(
        "SELECT id FROM decisions WHERE run_id = %s AND kind = %s "
        "AND (outcome IS NULL OR outcome <> %s)",
        (run_id, OBSERVATION_MATCH_DECISION, APPROVED),
    )
    return {str(decision["id"]) for decision in await result.fetchall()}


async def _write_one_rows_moves(
    connection: AsyncConnection,
    register_row_id: str,
    moves: list[dict[str, Any]],
    run_id: UUID,
    document_id_by_file: dict[str, UUID],
) -> int | None:
    row = await _row_the_move_reaches(connection, UUID(register_row_id))
    if row is None:
        return None

    for move in moves:
        old_value = row[move["cell"]]
        if old_value == move["value"]:
            continue
        await connection.execute(
            f"UPDATE register_rows SET {move['cell']} = %s WHERE id = %s",
            (move["value"], row["id"]),
        )
        await _replace_the_citations(connection, row["id"], move)
        if row["is_committed"]:
            # A row this run proposed has its whole first history written when
            # it is committed, so a second entry here would say the same thing
            # twice. A row that was already committed gets its before-and-after.
            await write_cell_change(
                connection,
                row["id"],
                move["cell"],
                old_value,
                move["value"],
                run_id,
                _source_document(move, document_id_by_file),
            )

    if row["is_committed"]:
        moved = await _row_the_move_reaches(connection, row["id"])
        await connection.execute(
            "UPDATE register_rows SET fingerprint = %s WHERE id = %s",
            (fingerprint_of_cells({name: moved[name] for name in CELL_NAMES}), row["id"]),
        )
    return row["row_number"]


async def _row_the_move_reaches(
    connection: AsyncConnection,
    register_row_id: UUID,
) -> dict[str, Any] | None:
    """The row this move lands on, following an approved merge to its candidate."""
    result = await connection.execute(
        "SELECT id, row_number, is_committed, merged_into_register_row_id, "
        + ", ".join(CELL_NAMES)
        + " FROM register_rows WHERE id = %s",
        (register_row_id,),
    )
    row = await result.fetchone()
    if row is None:
        return None
    if row["merged_into_register_row_id"] is None:
        return row
    return await _row_the_move_reaches(connection, row["merged_into_register_row_id"])


async def _replace_the_citations(
    connection: AsyncConnection,
    register_row_id: UUID,
    move: dict[str, Any],
) -> None:
    """The old citation supported a value this cell no longer holds, so it goes."""
    await connection.execute(
        "DELETE FROM citations WHERE register_row_id = %s AND cell_name = %s",
        (register_row_id, move["cell"]),
    )
    for citation in move["citations"]:
        await connection.execute(
            "INSERT INTO citations (id, register_row_id, cell_name, source_file, "
            "source_place, source_words) VALUES (gen_random_uuid(), %s, %s, %s, %s, %s)",
            (
                register_row_id,
                move["cell"],
                citation["source_file"],
                citation["place"],
                citation["source_words"],
            ),
        )


def _source_document(
    move: dict[str, Any],
    document_id_by_file: dict[str, UUID],
) -> UUID | None:
    if not move["citations"]:
        return None
    return document_id_by_file.get(move["citations"][0]["source_file"])
