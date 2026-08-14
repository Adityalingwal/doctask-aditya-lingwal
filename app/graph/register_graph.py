from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict
from uuid import UUID

from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt
from psycopg import AsyncConnection
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from app.extract.answer import (
    PRIMARY_DOCUMENT_TYPES,
    UNRELATED_DOCUMENT,
    UnrecognisedDocumentType,
    describe_unreadable_answer,
)
from app.examine.deliverable_checks import DELIVERABLE_CHECKS, deliverable_findings
from app.examine.examine_register import UnusableExamineAnswer, examine_register
from app.examine.frozen_rules import (
    freeze_rules_for_run,
    frozen_rules_of_run,
    rules_changed_since_the_register_was_last_examined,
)
from app.examine.record_findings import record_findings
from app.examine.register_under_examination import register_under_examination
from app.extract.read_document import locate_extraction, read_one_document
from app.ingest.collect_batch import collect_batch
from app.match.match_requirements import (
    EXISTING_ROW,
    POSSIBLE_MATCH,
    IncompleteMatchAnswer,
    match_requirements,
)
from app.model.call_failure import ModelCallFailed, raise_if_configuration_failure
from app.register.commit_register import commit_register
from app.register.propose_rows import committed_rows, propose_rows
from app.register.withdraw_rows import (
    batch_reads_a_document_a_row_came_from,
    propose_withdrawals,
)
from app.review.review_queue import ensure_export_decision, export_was_approved
from app.run_logging import log_run_event
from app.runs.finished_stages import record_stage_finished
from app.runs.run_records import (
    append_skipped,
    enter_stage,
    read_project,
    read_run,
    set_run_status,
)
from app.runs.statuses import (
    CLOSED_WITHOUT_EXPORT,
    COMMIT_STAGE,
    DONE,
    ENDED_WITHOUT_CHANGES,
    EXAMINE_STAGE,
    EXTRACT_STAGE,
    INGEST_STAGE,
    MATCH_STAGE,
    REVIEW_STAGE,
    RUNNING,
    WAITING_FOR_REVIEW,
)

INGEST_NODE = "ingest"
EXTRACT_NODE = "extract"
MATCH_NODE = "match"
EXAMINE_NODE = "examine"
REVIEW_NODE = "review"
COMMIT_NODE = "commit"
END_EARLY_NODE = "end_early"
CLOSE_WITHOUT_EXPORT_NODE = "close_without_export"

SKIPPED_DOCUMENT_KIND = "document"
NO_READABLE_FILE = (
    "no new or changed file the system can read was waiting in the project "
    "folder — add a document to it, or change one, and start another run."
)
NOTHING_FOUND = (
    "no document in this batch reported a requirement that could be traced to "
    "its own words — nothing was proposed for the register."
)
REGISTER_UNCHANGED = (
    "the register did not change by a single cell — every requirement in this "
    "batch already had a row."
)


class RunState(TypedDict, total=False):
    run_id: str
    project_id: str
    document_ids: list[str]
    next_document_index: int
    requirements_found: int
    reads_a_row_source_again: bool
    examine_changed_rules: bool
    proposed_rows: int
    withdrawals_proposed: int
    findings_raised: int
    ended_early_reason: str
    export_approved: bool


def build_register_graph(
    model_client: BaseChatModel,
    pool: AsyncConnectionPool,
    checkpointer: AsyncPostgresSaver,
    project_root: Path,
    accepted_extensions: frozenset[str],
    page_limit: int,
    rules_config_path: Path,
) -> CompiledStateGraph:
    """Wire the six pipeline stages, with everything they need passed in."""

    async def ingest(state: RunState) -> dict[str, Any]:
        run_id = UUID(state["run_id"])
        project_id = UUID(state["project_id"])
        async with pool.connection() as connection:
            await enter_stage(connection, run_id, INGEST_STAGE)
            # Frozen before a single document is read, so that everything
            # downstream judges this run against these rules, not the file.
            await freeze_rules_for_run(connection, run_id, rules_config_path)
            project = await read_project(connection, project_id)
            source_folder = _resolve_folder(project_root, project)
            if not source_folder.is_dir():
                reason = (
                    f"the project's source folder {project['source_folder_path']} "
                    "does not exist — create it, or correct the folder recorded "
                    "on the project, then start another run."
                )
                _log(logging.ERROR, "ingest_folder_missing", reason, run_id)
                await _finish_stage(connection, run_id, INGEST_STAGE)
                return {"document_ids": [], "ended_early_reason": reason}

            batch = await collect_batch(
                connection,
                run_id,
                project_id,
                source_folder,
                accepted_extensions,
                page_limit,
            )
            await append_skipped(connection, run_id, batch.skipped)
            reads_again = await batch_reads_a_document_a_row_came_from(
                connection, run_id, project_id
            )
            examine_changed_rules = (
                not batch.document_ids
                and bool(await committed_rows(connection, project_id))
                and await rules_changed_since_the_register_was_last_examined(
                    connection, run_id, project_id
                )
            )
            await _finish_stage(connection, run_id, INGEST_STAGE)

        _log(
            logging.INFO,
            "ingest_finished",
            f"Ingest took {len(batch.document_ids)} document(s) into the batch "
            f"and skipped {len(batch.skipped)}.",
            run_id,
            skipped=batch.skipped,
        )
        return {
            "document_ids": [str(document_id) for document_id in batch.document_ids],
            "next_document_index": 0,
            "requirements_found": 0,
            "reads_a_row_source_again": reads_again,
            "examine_changed_rules": examine_changed_rules,
        }

    async def extract(state: RunState) -> dict[str, Any]:
        run_id = UUID(state["run_id"])
        index = state["next_document_index"]
        document_id = UUID(state["document_ids"][index])

        async with pool.connection() as connection:
            await enter_stage(connection, run_id, EXTRACT_STAGE)
            result = await connection.execute(
                "SELECT source_path, extracted_text FROM documents WHERE id = %s",
                (document_id,),
            )
            document = await result.fetchone()

        source_file = document["source_path"]
        try:
            answer = await read_one_document(
                model_client, source_file, document["extracted_text"]
            )
        except UnrecognisedDocumentType as unrecognised:
            reason = (
                f"{source_file} was skipped: {unrecognised}. The other "
                "documents in the batch continue and the next run reads this "
                "one again; if the type keeps coming back invented, name a "
                "stronger model in config/model.yaml."
            )
            _log(logging.WARNING, "extract_document_type_unrecognised", reason, run_id)
            async with pool.connection() as connection:
                await append_skipped(
                    connection,
                    run_id,
                    [
                        {
                            "kind": SKIPPED_DOCUMENT_KIND,
                            "file": source_file,
                            "reason": reason,
                        }
                    ],
                )
                await _finish_stage(connection, run_id, EXTRACT_STAGE)
            return {"next_document_index": index + 1}
        except Exception as error:
            # One document degrades the run; a broken setup stops it, because
            # skipping every document would export an empty register instead
            # of the practical explanation.
            raise_if_configuration_failure(error)
            reason = (
                f"{source_file} was skipped after the model call failed "
                f"({describe_unreadable_answer(error)}) — the other documents "
                "in the batch continue, and the next run reads this document "
                "again."
            )
            _log(logging.ERROR, "extract_document_skipped", reason, run_id)
            async with pool.connection() as connection:
                await append_skipped(
                    connection,
                    run_id,
                    [
                        {
                            "kind": SKIPPED_DOCUMENT_KIND,
                            "file": source_file,
                            "reason": reason,
                        }
                    ],
                )
                await _finish_stage(connection, run_id, EXTRACT_STAGE)
            return {"next_document_index": index + 1}

        located = locate_extraction(answer, document["extracted_text"], source_file)
        skipped = list(located.dropped)
        requirements_found = len(located.extraction["requirements"])
        if answer.document_type not in PRIMARY_DOCUMENT_TYPES:
            # A related additional document is still read, labelled and stored
            # for what it adds to a row; what it may not do is put a row in the
            # register by itself.
            requirements_found = 0
        if answer.document_type == UNRELATED_DOCUMENT:
            skipped.append(
                {
                    "kind": SKIPPED_DOCUMENT_KIND,
                    "file": source_file,
                    "reason": (
                        "the document is not about this client engagement, so "
                        "nothing from it was proposed for the register."
                    ),
                }
            )

        async with pool.connection() as connection:
            await connection.execute(
                "UPDATE documents SET extraction = %s WHERE id = %s",
                (Jsonb(located.extraction), document_id),
            )
            await append_skipped(connection, run_id, skipped)
            await _finish_stage(connection, run_id, EXTRACT_STAGE)

        for instruction in located.extraction["embedded_instructions"]:
            _log(
                logging.WARNING,
                "embedded_instruction_reported",
                f"{source_file} contains text addressed to the system; it is "
                "reported and was not followed.",
                run_id,
                place=instruction["place"],
            )
        _log(
            logging.INFO,
            "extract_document_finished",
            f"Extract read {source_file} and traced {requirements_found} "
            f"requirement(s) to its own words.",
            run_id,
            document_type=answer.document_type.value,
            dropped=len(located.dropped),
        )
        return {
            "next_document_index": index + 1,
            "requirements_found": state.get("requirements_found", 0)
            + requirements_found,
        }

    async def match(state: RunState) -> dict[str, Any]:
        run_id = UUID(state["run_id"])
        project_id = UUID(state["project_id"])
        async with pool.connection() as connection:
            await enter_stage(connection, run_id, MATCH_STAGE)
            requirements = await _requirements_of_batch(connection, run_id)
            register = await committed_rows(connection, project_id)

        outcome_by_requirement = await _settle_against_the_register(
            model_client, register, requirements
        )

        async with pool.connection() as connection:
            proposed = await propose_rows(
                connection,
                run_id,
                project_id,
                requirements,
                outcome_by_requirement,
            )
            # After the proposals, so a row already under a possible-match
            # question is not asked about twice.
            withdrawn = await propose_withdrawals(
                connection,
                run_id,
                project_id,
                requirements,
                outcome_by_requirement,
            )
            await _finish_stage(connection, run_id, MATCH_STAGE)

        _log(
            logging.INFO,
            "match_finished",
            f"Match proposed {len(proposed.proposed_row_ids)} row(s), asked the "
            f"Delivery Owner about {len(proposed.gated_row_numbers)} and "
            f"proposed withdrawing {len(withdrawn)}.",
            run_id,
            gated_rows=proposed.gated_row_numbers,
            withdrawal_rows=withdrawn,
        )
        return {
            "proposed_rows": len(proposed.proposed_row_ids),
            "withdrawals_proposed": len(withdrawn),
        }

    async def examine(state: RunState) -> dict[str, Any]:
        run_id = UUID(state["run_id"])
        project_id = UUID(state["project_id"])
        async with pool.connection() as connection:
            await enter_stage(connection, run_id, EXAMINE_STAGE)
            rules = await frozen_rules_of_run(connection, run_id)
            rows = await register_under_examination(connection, project_id, run_id)

        try:
            found = await examine_register(model_client, rules, rows)
        except UnusableExamineAnswer:
            raise  # it already names its own cause and fix
        except Exception as error:
            raise_if_configuration_failure(error)
            # Examine judges the whole register in one call, so there is no
            # single row to drop the way Extract drops one document.
            raise ModelCallFailed(
                "The register could not be examined against this run's rules "
                f"({describe_unreadable_answer(error)}) — no finding was "
                "recorded and nothing was exported. Start another run once the "
                "model is answering."
            ) from error

        found += deliverable_findings(rows)
        async with pool.connection() as connection:
            await record_findings(connection, run_id, found)
            await connection.execute(
                "UPDATE runs SET examined_row_count = %s WHERE id = %s",
                (len(rows), run_id),
            )
            await _finish_stage(connection, run_id, EXAMINE_STAGE)

        _log(
            logging.INFO,
            "examine_finished",
            f"Examine judged {len(rows)} register row(s) against "
            f"{len(rules) + len(DELIVERABLE_CHECKS)} rule(s) and raised "
            f"{len(found)} finding(s).",
            run_id,
            rules_that_ran=[rule["id"] for rule in rules]
            + [check["id"] for check in DELIVERABLE_CHECKS],
        )
        return {"findings_raised": len(found)}

    async def review(state: RunState) -> dict[str, Any]:
        run_id = UUID(state["run_id"])
        project_id = UUID(state["project_id"])
        async with pool.connection() as connection:
            run = await read_run(connection, run_id)

        # LangGraph replays an interrupted node from its start on every
        # resume, so this node cannot otherwise tell a first entry from a
        # post-review replay. review_finished_at is the durable fact that
        # tells them apart: once it is set, raising the export decision,
        # entering the stage, reporting 'waiting for review', and the
        # interrupt itself must not happen again.
        if run["review_finished_at"] is None:
            async with pool.connection() as connection:
                project = await read_project(connection, project_id)
                await ensure_export_decision(
                    connection,
                    run_id,
                    f"Export the Requirements-to-Delivery Register for "
                    f"{project['name']}, with "
                    f"{state.get('proposed_rows', 0)} row(s) proposed by this "
                    "run?",
                )
                await enter_stage(connection, run_id, REVIEW_STAGE)
                await set_run_status(connection, run_id, WAITING_FOR_REVIEW)

            _log(
                logging.INFO,
                "review_waiting",
                "Review is waiting for the Delivery Owner; nothing commits or "
                "exports until every gated decision is answered.",
                run_id,
            )
            interrupt({"run_id": state["run_id"], "stage": REVIEW_STAGE})

        async with pool.connection() as connection:
            await set_run_status(connection, run_id, RUNNING)
            approved = await export_was_approved(connection, run_id)
            # Written here, after review_finished_at is set, rather than at the
            # first call site above: marking Review finished while the Delivery
            # Owner is still being asked would report a state the server has
            # not confirmed.
            await _finish_stage(connection, run_id, REVIEW_STAGE)

        _log(
            logging.INFO,
            "review_finished",
            f"Review finished with the export {'approved' if approved else 'rejected'}.",
            run_id,
        )
        return {"export_approved": approved}

    async def commit(state: RunState) -> dict[str, Any]:
        run_id = UUID(state["run_id"])
        project_id = UUID(state["project_id"])
        async with pool.connection() as connection:
            project = await read_project(connection, project_id)
            async with connection.transaction():
                await enter_stage(connection, run_id, COMMIT_STAGE)
                result = await commit_register(
                    connection,
                    project,
                    run_id,
                    datetime.now(timezone.utc).isoformat(),
                )
                await set_run_status(connection, run_id, DONE)
            await _finish_stage(connection, run_id, COMMIT_STAGE)

        _log(
            logging.INFO,
            "commit_finished",
            f"Commit made {len(result.committed_row_numbers)} row(s) permanent "
            f"and exported the register.",
            run_id,
            committed_rows=result.committed_row_numbers,
            merged_rows=result.merged_row_numbers,
            withdrawn_rows=result.withdrawn_row_numbers,
        )
        return {}

    async def end_early(state: RunState) -> dict[str, Any]:
        run_id = UUID(state["run_id"])
        reason = state.get("ended_early_reason") or _early_reason(state)
        async with pool.connection() as connection:
            await set_run_status(connection, run_id, ENDED_WITHOUT_CHANGES, reason)
        _log(logging.INFO, "run_ended_early", reason, run_id)
        return {"ended_early_reason": reason}

    async def close_without_export(state: RunState) -> dict[str, Any]:
        run_id = UUID(state["run_id"])
        async with pool.connection() as connection:
            await set_run_status(connection, run_id, CLOSED_WITHOUT_EXPORT)
        _log(
            logging.INFO,
            "run_closed_without_export",
            "The Delivery Owner rejected the export, so the run ended without "
            "one and the register is unchanged.",
            run_id,
        )
        return {}

    async def _requirements_of_batch(
        connection: AsyncConnection,
        run_id: UUID,
    ) -> list[dict[str, Any]]:
        result = await connection.execute(
            "SELECT extraction FROM documents WHERE run_id = %s AND "
            "extraction IS NOT NULL ORDER BY source_path",
            (run_id,),
        )
        requirements: list[dict[str, Any]] = []
        for document in await result.fetchall():
            extraction = document["extraction"]
            if extraction["document_type"] not in PRIMARY_DOCUMENT_TYPES:
                continue
            for requirement in extraction["requirements"]:
                requirements.append(
                    {
                        **requirement,
                        "document_type": extraction["document_type"],
                        "document_date": extraction["document_date"],
                    }
                )
        return requirements

    graph: StateGraph = StateGraph(RunState)
    graph.add_node(INGEST_NODE, ingest)
    graph.add_node(EXTRACT_NODE, extract)
    graph.add_node(MATCH_NODE, match)
    graph.add_node(EXAMINE_NODE, examine)
    graph.add_node(REVIEW_NODE, review)
    graph.add_node(COMMIT_NODE, commit)
    graph.add_node(END_EARLY_NODE, end_early)
    graph.add_node(CLOSE_WITHOUT_EXPORT_NODE, close_without_export)

    graph.add_edge(START, INGEST_NODE)
    graph.add_conditional_edges(
        INGEST_NODE,
        _route_after_ingest,
        [EXTRACT_NODE, EXAMINE_NODE, END_EARLY_NODE],
    )
    graph.add_conditional_edges(
        EXTRACT_NODE,
        _route_after_extract,
        [EXTRACT_NODE, MATCH_NODE, END_EARLY_NODE],
    )
    graph.add_conditional_edges(
        MATCH_NODE,
        _route_after_match,
        [EXAMINE_NODE, END_EARLY_NODE],
    )
    graph.add_edge(EXAMINE_NODE, REVIEW_NODE)
    graph.add_conditional_edges(
        REVIEW_NODE,
        _route_after_review,
        [COMMIT_NODE, CLOSE_WITHOUT_EXPORT_NODE],
    )
    graph.add_edge(COMMIT_NODE, END)
    graph.add_edge(END_EARLY_NODE, END)
    graph.add_edge(CLOSE_WITHOUT_EXPORT_NODE, END)
    return graph.compile(checkpointer=checkpointer)


async def _finish_stage(
    connection: AsyncConnection,
    run_id: UUID,
    stage: str,
) -> None:
    """Mark one stage finished where its pass ends, keyed by the stage name.

    Written at the end rather than at the start, so a stage killed part way
    leaves no mark for a resumed pass to have to undo, and keyed so a
    re-entered node overwrites its own mark instead of writing a second one.
    """
    await record_stage_finished(connection, run_id, stage)


async def _settle_against_the_register(
    model_client: BaseChatModel,
    register: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
) -> dict[int, tuple[str, int | None]]:
    """What Match says about each requirement this batch found.

    A batch that found none is never sent to the model: there is nothing to
    match, and it reached this stage only because a document it read again may
    have stopped asking for something.
    """
    if not requirements:
        return {}
    try:
        answer = await match_requirements(model_client, register, requirements)
    except IncompleteMatchAnswer:
        raise  # it already names its own cause and fix
    except Exception as error:
        raise_if_configuration_failure(error)
        # Match answers for the whole batch in one call, so there is no single
        # document to skip the way Extract skips one.
        raise ModelCallFailed(
            "Match could not be answered for this batch "
            f"({describe_unreadable_answer(error)}) — no register row was "
            "proposed. Start another run once the model is answering."
        ) from error
    # A confident match still goes to the Delivery Owner: attaching this
    # batch's evidence to a committed row is not the system's to decide.
    return {
        outcome.requirement_index: (
            POSSIBLE_MATCH if outcome.outcome == EXISTING_ROW else outcome.outcome,
            outcome.row_number,
        )
        for outcome in answer.outcomes
    }


def _route_after_ingest(state: RunState) -> str:
    if state.get("document_ids"):
        return EXTRACT_NODE
    # No document changed, but the rules this run froze are not the ones the
    # register was last judged against, so it is examined again.
    return EXAMINE_NODE if state.get("examine_changed_rules") else END_EARLY_NODE


def _route_after_extract(state: RunState) -> str:
    if state["next_document_index"] < len(state["document_ids"]):
        return EXTRACT_NODE
    if state.get("requirements_found") or state.get("reads_a_row_source_again"):
        return MATCH_NODE
    return END_EARLY_NODE


def _route_after_match(state: RunState) -> str:
    if state.get("proposed_rows") or state.get("withdrawals_proposed"):
        return EXAMINE_NODE
    return END_EARLY_NODE


def _route_after_review(state: RunState) -> str:
    return COMMIT_NODE if state.get("export_approved") else CLOSE_WITHOUT_EXPORT_NODE


def _early_reason(state: RunState) -> str:
    if not state.get("document_ids"):
        return NO_READABLE_FILE
    if not state.get("requirements_found"):
        return NOTHING_FOUND
    return REGISTER_UNCHANGED


def _resolve_folder(project_root: Path, project: dict[str, Any]) -> Path:
    recorded = Path(project["source_folder_path"])
    return recorded if recorded.is_absolute() else project_root / recorded


def _log(level: int, event: str, message: str, run_id: UUID, **fields: Any) -> None:
    log_run_event(level, event, message, str(run_id), **fields)
