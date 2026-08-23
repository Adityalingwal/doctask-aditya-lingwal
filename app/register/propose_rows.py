from __future__ import annotations

from typing import Any, NamedTuple
from uuid import UUID, uuid4

from psycopg import AsyncConnection

from app.extract.answer import CLIENT_REQUIREMENTS_DOCUMENT
from app.match.match_requirements import EXISTING_ROW, NEW_ROW
from app.register.cells import (
    CELL_NAMES,
    COLUMN_HEADINGS,
    IN_WRITING,
    IN_WRITING_NOT_KNOWN_YET,
    IN_WRITING_YES,
    STATUS,
    STATUS_REQUESTED,
    TESTING_NOT_KNOWN_YET,
    WHAT_TESTING_FOUND,
    WHAT_WAS_ASKED,
    cells_a_merge_would_write,
    shorten_quote,
)
from app.review.decision_text import (
    DecisionText,
    cells_as_a_person_reads_them,
    possible_match_text,
    proposed_row_label,
    quote_block,
    register_row_label,
)
from app.review.review_queue import raise_possible_match_decision


UNSET_FINGERPRINT = ""


class ProposedRegister(NamedTuple):
    proposed_row_ids: list[UUID]
    gated_row_numbers: list[int]


class MatchSettlement(NamedTuple):
    """What Match settled about one requirement, and the candidate it named.

    Both candidates are carried because a requirement matches either a register
    row that already exists or an earlier requirement of this same batch, and
    the two are settled in different ways. No sentence travels here: every
    word a person reads on the decision is built from stored data below.
    """

    outcome: str
    row_number: int | None
    same_as_requirement_index: int | None


async def committed_rows(
    connection: AsyncConnection,
    project_id: UUID,
) -> list[dict[str, Any]]:
    """The register's committed rows, whole, because a decision quotes them.

    All four cells, not `what_was_asked` alone: the possible-match decision
    shows the candidate row exactly as the register's table shows it.
    """
    result = await connection.execute(
        "SELECT id, row_number, " + ", ".join(CELL_NAMES) + " FROM register_rows "
        "WHERE project_id = %s AND is_committed ORDER BY row_number",
        (project_id,),
    )
    return list(await result.fetchall())


async def propose_rows(
    connection: AsyncConnection,
    run_id: UUID,
    project_id: UUID,
    requirements: list[dict[str, Any]],
    outcome_by_requirement: dict[int, MatchSettlement],
) -> ProposedRegister:
    """Write this batch's requirements as proposed rows, gating uncertain ones.

    Nothing here is settled: a proposed row becomes part of the register only
    when Commit runs after the Delivery Owner has added this run's changes
    to the register.
    """
    proposed_row_ids: list[UUID] = []
    gated_row_numbers: list[int] = []

    async with connection.transaction():
        await _clear_what_this_run_proposed_before(connection, run_id)
        register = await committed_rows(connection, project_id)
        candidate_by_number = {row["row_number"]: row for row in register}
        next_row_number = await _next_row_number(connection, project_id)

        stating_requirement = _which_requirement_states_each_row(
            outcome_by_requirement, len(requirements)
        )
        requirements_of_row: dict[int, list[dict[str, Any]]] = {}
        for index, requirement in enumerate(requirements):
            requirements_of_row.setdefault(stating_requirement[index], []).append(
                requirement
            )

        row_by_requirement: dict[int, dict[str, Any]] = {}
        for stated_by in sorted(requirements_of_row):
            on_this_row = requirements_of_row[stated_by]
            in_writing = _in_writing_cell(_the_requirement_in_writing(on_this_row))
            row_id = await _insert_proposed_row(
                connection,
                run_id,
                project_id,
                next_row_number,
                on_this_row,
                in_writing,
            )
            proposed_row_ids.append(row_id)
            row_by_requirement[stated_by] = {
                "id": row_id,
                "row_number": next_row_number,
                # A candidate may be one of these proposals (S24), and the
                # decision shows a candidate's four cells, so a proposal
                # carries them here rather than being read back.
                WHAT_WAS_ASKED: on_this_row[0]["summary"],
                IN_WRITING: in_writing,
                WHAT_TESTING_FOUND: TESTING_NOT_KNOWN_YET,
                STATUS: STATUS_REQUESTED,
                "is_committed": False,
            }
            next_row_number += 1

        for index in range(len(requirements)):
            settled = outcome_by_requirement[index]
            candidate = _the_candidate_to_ask_about(
                settled,
                candidate_by_number,
                row_by_requirement,
                stating_requirement,
            )
            if candidate is None:
                continue
            proposed = row_by_requirement[index]
            asked = _the_text_of_the_question(candidate, proposed, requirements[index])
            await raise_possible_match_decision(
                connection,
                run_id,
                asked.question,
                asked.parts,
                proposed["id"],
                candidate["id"],
            )
            gated_row_numbers.append(proposed["row_number"])

    return ProposedRegister(
        proposed_row_ids=proposed_row_ids,
        gated_row_numbers=gated_row_numbers,
    )


def _the_text_of_the_question(
    candidate: dict[str, Any],
    proposed: dict[str, Any],
    requirement: dict[str, Any],
) -> DecisionText:
    """The whole decision a person reads before two asks are treated as one.

    The candidate may be a row this same run proposed, which is not on the
    register yet and says so (S24). What approving writes is worked out by the
    one rule Commit's merge uses, so the line never promises a cell change
    Commit will not make.
    """
    label = (
        register_row_label(candidate["row_number"])
        if candidate.get("is_committed", True)
        else proposed_row_label(candidate["row_number"])
    )
    return possible_match_text(
        row_number=candidate["row_number"],
        row_label=label,
        cells=cells_as_a_person_reads_them(candidate),
        quote=quote_block(
            requirement["source_file"],
            requirement["place"],
            shorten_quote(requirement["source_words"]),
        ),
        if_approved=[
            {"cell": COLUMN_HEADINGS[cell_name], "value": value}
            for cell_name, value in cells_a_merge_would_write(
                proposed[IN_WRITING], candidate[IN_WRITING]
            ).items()
        ],
        proposed_in_writing=proposed[IN_WRITING],
    )


def _which_requirement_states_each_row(
    outcome_by_requirement: dict[int, MatchSettlement],
    requirement_count: int,
) -> dict[int, int]:
    """Which requirement's row each requirement's evidence belongs on.

    A requirement may be the same as one that was itself the same as an earlier
    one, so the chain is followed to its end. Every link points strictly
    backwards, so it can only end at a requirement that states a row of its own.
    """
    stated_by: dict[int, int] = {}
    for index in range(requirement_count):
        settled = outcome_by_requirement[index]
        if (
            settled.outcome == EXISTING_ROW
            and settled.same_as_requirement_index is not None
        ):
            stated_by[index] = stated_by[settled.same_as_requirement_index]
        else:
            stated_by[index] = index
    return stated_by


def _the_candidate_to_ask_about(
    settled: MatchSettlement,
    candidate_by_number: dict[int, dict[str, Any]],
    row_by_requirement: dict[int, dict[str, Any]],
    stating_requirement: dict[int, int],
) -> dict[str, Any] | None:
    """The row a possible match is raised against, or None when none is asked.

    A confident match against a batch requirement is the one case that raises
    nothing: no row of its own was written, and the whole run still faces the
    export gate, where the merged row and both its citations are visible.
    """
    if settled.outcome == NEW_ROW:
        return None
    if settled.row_number is not None:
        return candidate_by_number.get(settled.row_number)
    if settled.same_as_requirement_index is None or settled.outcome == EXISTING_ROW:
        return None
    # The row the named requirement's evidence actually landed on, never a
    # proposal that merged away before this batch was written.
    return row_by_requirement[stating_requirement[settled.same_as_requirement_index]]


async def _clear_what_this_run_proposed_before(
    connection: AsyncConnection,
    run_id: UUID,
) -> None:
    """Drop this run's own earlier proposals, so a re-run replaces rather than adds.

    Match answers for the whole batch at once, so a half-written batch cannot be
    matched back requirement by requirement. What goes is strictly this run's
    uncommitted rows, their citations and its unanswered decisions; a committed
    row, an answered decision and another run's work are all out of reach.
    """
    await connection.execute(
        "DELETE FROM decisions WHERE run_id = %s AND outcome IS NULL",
        (run_id,),
    )
    await connection.execute(
        "DELETE FROM citations WHERE register_row_id IN (SELECT id FROM "
        "register_rows WHERE proposed_by_run_id = %s AND NOT is_committed)",
        (run_id,),
    )
    await connection.execute(
        "DELETE FROM register_rows WHERE proposed_by_run_id = %s "
        "AND NOT is_committed",
        (run_id,),
    )


async def _next_row_number(connection: AsyncConnection, project_id: UUID) -> int:
    result = await connection.execute(
        "SELECT COALESCE(MAX(row_number), 0) AS highest FROM register_rows "
        "WHERE project_id = %s",
        (project_id,),
    )
    highest = await result.fetchone()
    return int(highest["highest"]) + 1


async def _insert_proposed_row(
    connection: AsyncConnection,
    run_id: UUID,
    project_id: UUID,
    row_number: int,
    requirements_on_row: list[dict[str, Any]],
    in_writing: str,
) -> UUID:
    row_id = uuid4()
    # The batch is ordered by document type, so the first requirement on a row
    # is the one stated earliest in the workflow, whatever the files are named.
    stated_the_ask = requirements_on_row[0]
    written_down = _the_requirement_in_writing(requirements_on_row)

    await connection.execute(
        "INSERT INTO register_rows (id, project_id, what_was_asked, in_writing, "
        "what_testing_found, status, fingerprint, row_number, "
        "proposed_by_run_id, is_committed) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, false)",
        (
            row_id,
            project_id,
            stated_the_ask["summary"],
            in_writing,
            TESTING_NOT_KNOWN_YET,
            STATUS_REQUESTED,
            UNSET_FINGERPRINT,
            row_number,
            run_id,
        ),
    )

    # Every requirement on the row shows its own words, so the row names both
    # documents that stated the one ask rather than whichever was read first.
    for requirement in requirements_on_row:
        await _insert_citation(connection, row_id, WHAT_WAS_ASKED, requirement)
    if written_down is not None:
        await _insert_citation(connection, row_id, IN_WRITING, written_down)
    return row_id


def _the_requirement_in_writing(
    requirements_on_row: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for requirement in requirements_on_row:
        if requirement.get("document_type") == CLIENT_REQUIREMENTS_DOCUMENT:
            return requirement
    return None


def _in_writing_cell(written_down: dict[str, Any] | None) -> str:
    """`Yes` where a requirements document states the ask, and nothing more.

    A new row never claims absence. Whether a requirements document the project
    has read is silent about this ask is settled at Commit by the absence move
    (`app/register/absence_rows.py`), which writes the evidence behind that
    claim; a cell written here could only assert it with none.
    """
    if written_down is not None:
        return IN_WRITING_YES
    return IN_WRITING_NOT_KNOWN_YET


async def _insert_citation(
    connection: AsyncConnection,
    register_row_id: UUID,
    cell_name: str,
    evidence: dict[str, Any],
) -> None:
    await connection.execute(
        "INSERT INTO citations (id, register_row_id, cell_name, source_file, "
        "source_place, source_words) VALUES (%s, %s, %s, %s, %s, %s)",
        (
            uuid4(),
            register_row_id,
            cell_name,
            evidence["source_file"],
            evidence["place"],
            evidence["source_words"],
        ),
    )
