from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import AsyncConnection

from app.examine.read_findings import findings_of_run
from app.register.absence_rows import UNANSWERED_VALUE, is_absence
from app.register.cells import (
    CELL_NAMES,
    COLUMN_HEADINGS,
    IN_WRITING,
    STATUS,
    STATUS_DISPUTED,
    WHAT_TESTING_FOUND,
)
from app.register.move_rows import DELIVERY_EVIDENCE, TESTING_OBSERVATION
from app.review.review_queue import (
    APPROVED,
    POSSIBLE_MATCH_DECISION,
    REJECTED,
    decisions_of_run,
)
from app.runs.statuses import WAITING_FOR_REVIEW


# Every sentence the block shows. Each is filled from stored data alone — no
# model is called and nothing is worked out here that Commit will not do.
NEW_ROWS_FROM_ONE_FILE = "{rows}, all from {file}."
ONE_NEW_ROW_FROM_ONE_FILE = "{rows}, from {file}."
NEW_ROWS_FROM_A_PAIR = "{rows} from {files} — an ask stated in both becomes one row."
NEW_ROWS_FROM_SEVERAL_FILES = (
    "{rows} from {files} — an ask stated in more than one becomes one row."
)
ROW_CHANGE = "Row {row_number} · {changes} — {tail}"
ONE_CELL_CHANGE = "{heading} → {value}"
CHANGES_JOINED_BY = " · "
FILES_JOINED_BY = " and "
SOURCE_FILES_TAIL = "{files}."
DISPUTED_TAIL = "{built} claims it was built; {absent} reports it absent."
SILENT_ABOUT_THIS_ROW = "{file} was read and is silent about this row."
DOES_NOT_MENTION_THIS_ASK = "{file} was read and does not mention this ask."
NEW_ROW_AFTER_A_REJECTED_MATCH = (
    'A new row for "{summary}" — you rejected the match with row {row_number}, '
    "so this ask gets its own row, with {in_writing_heading}: {in_writing}."
)
FINDING_ATTACHED = 'Row {row_number} · A finding is attached — "{rule_text}".'
NOTHING_TO_WRITE = "Nothing — the register stays as it is."

NEW_ROWS_ENTRY = "new rows"
ROW_CHANGE_ENTRY = "row change"
ABSENCE_ENTRY = "absence"
NEW_ROW_AFTER_A_REJECTION_ENTRY = "new row after a rejected match"
FINDING_ENTRY = "finding attached"
NOTHING_ENTRY = "nothing"

# The sentence each cell's silence is written with. `Status` rests on more than
# one claim and no absence ever moves it, so it names none.
ABSENCE_TAIL_BY_CELL = {
    WHAT_TESTING_FOUND: SILENT_ABOUT_THIS_ROW,
    IN_WRITING: DOES_NOT_MENTION_THIS_ASK,
}


async def what_add_will_write(
    connection: AsyncConnection,
    run: dict[str, Any],
) -> list[dict[str, Any]] | None:
    """Every line Add would write to the register, read back from stored data.

    A preview of the one press, so it exists only while the run is waiting at
    review; a run that has ended answers nothing, because the block states what
    is about to happen rather than what did. Nothing an unanswered decision
    would settle appears — the screen counts those instead.
    """
    if run["status"] != WAITING_FOR_REVIEW:
        return None

    run_id = run["id"]
    decisions = await decisions_of_run(connection, run_id)
    rows = await _rows_this_run_can_reach(connection, run["project_id"], run_id)
    row_by_id = {str(row["id"]): row for row in rows}
    lands_on = _where_an_approved_merge_sends_a_proposal(decisions)
    citations = await _citations_of(connection, [row["id"] for row in rows])
    moved, silences = await _settled_moves(
        connection, run_id, decisions, row_by_id, lands_on, citations
    )

    # The order a person reads down the block: the rows Commit creates, what
    # each answer settles, what the rules found, and last what a document was
    # read and silent about.
    entries = (
        _new_rows(decisions, rows, citations)
        + _approved_merges(decisions, row_by_id, citations)
        + _rejected_merges(decisions, row_by_id)
        + moved
        + await _approved_findings(connection, run_id)
        + silences
    )
    if entries:
        return entries
    return [{"kind": NOTHING_ENTRY, "text": NOTHING_TO_WRITE}]


def _new_rows(
    decisions: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    citations: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """The rows Commit creates, and the documents that stated them.

    A proposal a possible match points at is left out whichever way that
    question goes: approved it merges into a row that already exists, and
    rejected it gets a sentence of its own naming the match that was turned
    down.
    """
    asked_about = {
        str(decision["proposed_register_row_id"])
        for decision in decisions
        if decision["kind"] == POSSIBLE_MATCH_DECISION
        and decision["proposed_register_row_id"] is not None
    }
    born = [
        row
        for row in rows
        if not row["is_committed"] and str(row["id"]) not in asked_about
    ]
    if not born:
        return []

    files = _distinct(
        citation["source_file"]
        for row in born
        for citation in citations.get(str(row["id"]), [])
    )
    return [
        {
            "kind": NEW_ROWS_ENTRY,
            "text": _new_rows_sentence(len(born), files),
            "row_count": len(born),
            "row_numbers": [row["row_number"] for row in born],
            "source_files": files,
        }
    ]


def _new_rows_sentence(count: int, files: list[str]) -> str:
    counted = f"{count} new row{'' if count == 1 else 's'}"
    if len(files) == 1:
        template = (
            ONE_NEW_ROW_FROM_ONE_FILE if count == 1 else NEW_ROWS_FROM_ONE_FILE
        )
        return template.format(rows=counted, file=files[0])
    template = NEW_ROWS_FROM_A_PAIR if len(files) == 2 else NEW_ROWS_FROM_SEVERAL_FILES
    return template.format(rows=counted, files=FILES_JOINED_BY.join(files))


def _approved_merges(
    decisions: list[dict[str, Any]],
    row_by_id: dict[str, dict[str, Any]],
    citations: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """What an approved possible match writes on the row it lands on.

    The cells come from the decision's own `if_approved`, which is the list
    Commit's merge works from, so the promise and the write cannot disagree. A
    merge that writes no cell moves only evidence, and evidence is not a line
    here.
    """
    entries: list[dict[str, Any]] = []
    for decision in _answered(decisions, POSSIBLE_MATCH_DECISION, APPROVED):
        changes = (decision["parts"] or {}).get("if_approved") or []
        if not changes:
            continue
        proposal = row_by_id.get(str(decision["proposed_register_row_id"]))
        files = _distinct(
            _file_behind(citations, proposal, _cell_named(change["cell"]))
            for change in changes
        )
        entries.append(
            _row_change_entry(decision["row_number"], changes, files, disputed=None)
        )
    return entries


def _rejected_merges(
    decisions: list[dict[str, Any]],
    row_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """A rejected match is not silence: the ask gets a row of its own."""
    entries: list[dict[str, Any]] = []
    for decision in _answered(decisions, POSSIBLE_MATCH_DECISION, REJECTED):
        proposal = row_by_id.get(str(decision["proposed_register_row_id"]))
        if proposal is None:
            continue
        entries.append(
            {
                "kind": NEW_ROW_AFTER_A_REJECTION_ENTRY,
                "text": NEW_ROW_AFTER_A_REJECTED_MATCH.format(
                    summary=proposal["what_was_asked"],
                    row_number=decision["row_number"],
                    in_writing_heading=COLUMN_HEADINGS[IN_WRITING],
                    in_writing=proposal[IN_WRITING],
                ),
                "summary": proposal["what_was_asked"],
                "rejected_match_with_row": decision["row_number"],
                "in_writing": proposal[IN_WRITING],
            }
        )
    return entries


async def _settled_moves(
    connection: AsyncConnection,
    run_id: UUID,
    decisions: list[dict[str, Any]],
    row_by_id: dict[str, dict[str, Any]],
    lands_on: dict[str, str],
    citations: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Every move this run's answers have settled, and every silence it writes.

    A move whose question is unanswered is not here at all — predicting it
    would answer for the person. A move whose question was rejected writes
    nothing, and one raised against a row this run proposed was never gated.
    """
    moves = await _pending_moves(connection, run_id)
    outcome_of = {str(decision["id"]): decision["outcome"] for decision in decisions}
    settled: list[dict[str, Any]] = []
    for move in moves:
        decision_id = move["decision_id"]
        if decision_id is not None and outcome_of.get(decision_id) != APPROVED:
            continue
        settled.append(
            {**move, "register_row_id": _resolved(move["register_row_id"], lands_on)}
        )

    written_cells = {
        (move["register_row_id"], move["cell"])
        for move in settled
        if not is_absence(move)
    } | _cells_an_approved_merge_writes(decisions, lands_on)
    gated_cells = _cells_an_unanswered_decision_would_write(decisions, moves, lands_on)

    observed = [move for move in settled if not is_absence(move)]
    absences = [
        move
        for move in settled
        if is_absence(move)
        and (move["register_row_id"], move["cell"]) not in written_cells
        and (move["register_row_id"], move["cell"]) not in gated_cells
        and _still_unanswered_on_the_row(row_by_id, move)
    ]
    return (
        _moves_as_entries(observed, row_by_id, citations),
        _absences_as_entries(absences, row_by_id),
    )


def _moves_as_entries(
    moves: list[dict[str, Any]],
    row_by_id: dict[str, dict[str, Any]],
    citations: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """One line per row, its cells in the order the register's columns run."""
    by_row: dict[str, list[dict[str, Any]]] = {}
    for move in moves:
        by_row.setdefault(move["register_row_id"], []).append(move)

    entries: list[dict[str, Any]] = []
    for register_row_id in sorted(by_row, key=lambda one: _number_of(row_by_id, one)):
        on_this_row = sorted(
            by_row[register_row_id], key=lambda one: CELL_NAMES.index(one["cell"])
        )
        row = row_by_id.get(register_row_id)
        if row is None:
            continue
        changes = [
            {"cell": COLUMN_HEADINGS[move["cell"]], "value": move["value"]}
            for move in on_this_row
        ]
        files = _distinct(
            citation["source_file"]
            for move in on_this_row
            for citation in move["citations"]
        )
        entries.append(
            _row_change_entry(
                row["row_number"],
                changes,
                files,
                disputed=_the_two_sides_of_a_dispute(on_this_row, citations, row),
            )
        )
    return entries


def _absences_as_entries(
    absences: list[dict[str, Any]],
    row_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for move in sorted(
        absences,
        key=lambda one: (_number_of(row_by_id, one["register_row_id"]), one["cell"]),
    ):
        row = row_by_id.get(move["register_row_id"])
        if row is None:
            continue
        source_file = move["citations"][0]["source_file"]
        entries.append(
            {
                "kind": ABSENCE_ENTRY,
                "text": ROW_CHANGE.format(
                    row_number=row["row_number"],
                    changes=ONE_CELL_CHANGE.format(
                        heading=COLUMN_HEADINGS[move["cell"]], value=move["value"]
                    ),
                    tail=ABSENCE_TAIL_BY_CELL[move["cell"]].format(file=source_file),
                ),
                "row_number": row["row_number"],
                "changes": [
                    {"cell": COLUMN_HEADINGS[move["cell"]], "value": move["value"]}
                ],
                "source_files": [source_file],
            }
        )
    return entries


async def _approved_findings(
    connection: AsyncConnection,
    run_id: UUID,
) -> list[dict[str, Any]]:
    return [
        {
            "kind": FINDING_ENTRY,
            "text": FINDING_ATTACHED.format(
                row_number=finding["row_number"], rule_text=finding["rule_text"]
            ),
            "row_number": finding["row_number"],
            "rule_text": finding["rule_text"],
        }
        for finding in await findings_of_run(connection, run_id, approved_only=True)
    ]


def _row_change_entry(
    row_number: int,
    changes: list[dict[str, str]],
    files: list[str],
    disputed: tuple[list[str], list[str]] | None,
) -> dict[str, Any]:
    if disputed is not None:
        built, absent = disputed
        tail = DISPUTED_TAIL.format(
            built=FILES_JOINED_BY.join(built), absent=FILES_JOINED_BY.join(absent)
        )
    else:
        tail = SOURCE_FILES_TAIL.format(files=FILES_JOINED_BY.join(files))
    return {
        "kind": ROW_CHANGE_ENTRY,
        "text": ROW_CHANGE.format(
            row_number=row_number,
            changes=CHANGES_JOINED_BY.join(
                ONE_CELL_CHANGE.format(heading=change["cell"], value=change["value"])
                for change in changes
            ),
            tail=tail,
        ),
        "row_number": row_number,
        "changes": changes,
        "source_files": files,
    }


def _the_two_sides_of_a_dispute(
    moves: list[dict[str, Any]],
    citations: dict[str, list[dict[str, Any]]],
    row: dict[str, Any],
) -> tuple[list[str], list[str]] | None:
    """Which document claims the work was built, and which reports it absent.

    `Disputed` is the one status that exists because two documents oppose each
    other, so the line names both. The claim that it was built comes either
    from this batch's own delivery evidence or, where the handover was read in
    an earlier run, from the citation still standing behind the row's status.
    Where neither is there to name, the caller falls back to the plain list of
    sources rather than inventing a second side.
    """
    disputing = next(
        (
            move
            for move in moves
            if move["cell"] == STATUS and move["value"] == STATUS_DISPUTED
        ),
        None,
    )
    if disputing is None:
        return None

    absent = _distinct(
        citation["source_file"]
        for citation in disputing["citations"]
        if citation.get("kind") == TESTING_OBSERVATION
    )
    built = _distinct(
        citation["source_file"]
        for citation in disputing["citations"]
        if citation.get("kind") == DELIVERY_EVIDENCE
    )
    if not built:
        arriving = {citation["source_file"] for citation in disputing["citations"]}
        built = _distinct(
            citation["source_file"]
            for citation in citations.get(str(row["id"]), [])
            if citation["cell_name"] == STATUS
            and citation["source_file"] not in arriving
        )
    if not absent or not built:
        return None
    return built, absent


def _where_an_approved_merge_sends_a_proposal(
    decisions: list[dict[str, Any]],
) -> dict[str, str]:
    """Each proposal an approved match merges away, and the row it lands on."""
    return {
        str(decision["proposed_register_row_id"]): str(
            decision["candidate_register_row_id"]
        )
        for decision in _answered(decisions, POSSIBLE_MATCH_DECISION, APPROVED)
    }


def _cells_an_approved_merge_writes(
    decisions: list[dict[str, Any]],
    lands_on: dict[str, str],
) -> set[tuple[str, str]]:
    """A cell an approved merge fills is not then reported as a silence."""
    written: set[tuple[str, str]] = set()
    for decision in _answered(decisions, POSSIBLE_MATCH_DECISION, APPROVED):
        register_row_id = _resolved(str(decision["candidate_register_row_id"]), lands_on)
        for change in (decision["parts"] or {}).get("if_approved") or []:
            written.add((register_row_id, _cell_named(change["cell"])))
    return written


def _cells_an_unanswered_decision_would_write(
    decisions: list[dict[str, Any]],
    moves: list[dict[str, Any]],
    lands_on: dict[str, str],
) -> set[tuple[str, str]]:
    """Cells a question still open may fill, so no silence is predicted there.

    Showing the absence would be predicting the rejection, which is the one
    thing this block must never do.
    """
    open_decisions = {
        str(decision["id"])
        for decision in decisions
        if decision["outcome"] is None
    }
    gated = {
        (_resolved(move["register_row_id"], lands_on), move["cell"])
        for move in moves
        if move["decision_id"] in open_decisions
    }
    for decision in decisions:
        if (
            decision["kind"] != POSSIBLE_MATCH_DECISION
            or decision["outcome"] is not None
            or decision["candidate_register_row_id"] is None
        ):
            continue
        register_row_id = _resolved(str(decision["candidate_register_row_id"]), lands_on)
        for change in (decision["parts"] or {}).get("if_approved") or []:
            gated.add((register_row_id, _cell_named(change["cell"])))
    return gated


def _still_unanswered_on_the_row(
    row_by_id: dict[str, dict[str, Any]],
    move: dict[str, Any],
) -> bool:
    """Whether the cell this silence would fill is still waiting for an answer.

    The same test `write_absence` makes at Commit: a cell already holding a
    verdict is left alone, and one already reading `Not mentioned` moves
    nothing, so neither is a line here.
    """
    row = row_by_id.get(move["register_row_id"])
    if row is None:
        return False
    return row[move["cell"]] == UNANSWERED_VALUE[move["cell"]]


def _answered(
    decisions: list[dict[str, Any]],
    kind: str,
    outcome: str,
) -> list[dict[str, Any]]:
    return [
        decision
        for decision in decisions
        if decision["kind"] == kind and decision["outcome"] == outcome
    ]


def _cell_named(heading: str) -> str:
    return next(
        name for name, shown in COLUMN_HEADINGS.items() if shown == heading
    )


def _file_behind(
    citations: dict[str, list[dict[str, Any]]],
    row: dict[str, Any] | None,
    cell_name: str,
) -> str | None:
    if row is None:
        return None
    return next(
        (
            citation["source_file"]
            for citation in citations.get(str(row["id"]), [])
            if citation["cell_name"] == cell_name
        ),
        None,
    )


def _resolved(register_row_id: str, lands_on: dict[str, str]) -> str:
    """The row a proposal's evidence ends up on, following approved merges."""
    seen: set[str] = set()
    while register_row_id in lands_on and register_row_id not in seen:
        seen.add(register_row_id)
        register_row_id = lands_on[register_row_id]
    return register_row_id


def _number_of(row_by_id: dict[str, dict[str, Any]], register_row_id: str) -> int:
    row = row_by_id.get(register_row_id)
    return row["row_number"] if row is not None else 0


def _distinct(files: Any) -> list[str]:
    kept: list[str] = []
    for file in files:
        if file is not None and file not in kept:
            kept.append(file)
    return kept


async def _rows_this_run_can_reach(
    connection: AsyncConnection,
    project_id: UUID,
    run_id: UUID,
) -> list[dict[str, Any]]:
    result = await connection.execute(
        "SELECT id, row_number, is_committed, " + ", ".join(CELL_NAMES) + " "
        "FROM register_rows WHERE project_id = %s "
        "AND (is_committed OR proposed_by_run_id = %s) "
        "AND merged_into_register_row_id IS NULL ORDER BY row_number",
        (project_id, run_id),
    )
    return list(await result.fetchall())


async def _citations_of(
    connection: AsyncConnection,
    register_row_ids: list[UUID],
) -> dict[str, list[dict[str, Any]]]:
    result = await connection.execute(
        "SELECT register_row_id, cell_name, source_file FROM citations "
        "WHERE register_row_id = ANY(%s)",
        (register_row_ids,),
    )
    held: dict[str, list[dict[str, Any]]] = {}
    for citation in await result.fetchall():
        held.setdefault(str(citation["register_row_id"]), []).append(citation)
    return held


async def _pending_moves(
    connection: AsyncConnection,
    run_id: UUID,
) -> list[dict[str, Any]]:
    result = await connection.execute(
        "SELECT pending_moves FROM runs WHERE id = %s", (run_id,)
    )
    stored = await result.fetchone()
    return (stored["pending_moves"] if stored else []) or []
