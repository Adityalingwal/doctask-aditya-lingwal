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

from app.extract.answer import UNRELATED_DOCUMENT, describe_unreadable_answer
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
from app.review.review_queue import ensure_export_decision, export_was_approved
from app.run_logging import log_run_event
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
    proposed_rows: int
    ended_early_reason: str
    export_approved: bool


def build_register_graph(
    model_client: BaseChatModel,
    pool: AsyncConnectionPool,
    checkpointer: AsyncPostgresSaver,
    project_root: Path,
    accepted_extensions: frozenset[str],
) -> CompiledStateGraph:
    """Wire the five slice 1b stages, with everything they need passed in."""

    async def ingest(state: RunState) -> dict[str, Any]:
        run_id = UUID(state["run_id"])
        project_id = UUID(state["project_id"])
        async with pool.connection() as connection:
            await enter_stage(connection, run_id, INGEST_STAGE)
            project = await read_project(connection, project_id)
            source_folder = _resolve_folder(project_root, project)
            if not source_folder.is_dir():
                reason = (
                    f"the project's source folder {project['source_folder_path']} "
                    "does not exist — create it, or correct the folder recorded "
                    "on the project, then start another run."
                )
                _log(logging.ERROR, "ingest_folder_missing", reason, run_id)
                return {"document_ids": [], "ended_early_reason": reason}

            batch = await collect_batch(
                connection,
                run_id,
                project_id,
                source_folder,
                accepted_extensions,
            )
            await append_skipped(connection, run_id, batch.skipped)

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
            return {"next_document_index": index + 1}

        located = locate_extraction(answer, document["extracted_text"], source_file)
        skipped = list(located.dropped)
        requirements_found = len(located.extraction["requirements"])
        if answer.document_type == UNRELATED_DOCUMENT:
            requirements_found = 0
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
            document_type=answer.document_type,
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

        try:
            answer = await match_requirements(model_client, register, requirements)
        except IncompleteMatchAnswer:
            raise  # it already names its own cause and fix
        except Exception as error:
            raise_if_configuration_failure(error)
            # Match answers for the whole batch in one call, so there is no
            # single document to skip the way Extract skips one.
            raise ModelCallFailed(
                "Match could not be answered for this batch "
                f"({describe_unreadable_answer(error)}) — no register row was "
                "proposed. Start another run once the model is answering."
            ) from error
        # A confident match still goes to the Delivery Owner: attaching this
        # batch's evidence to a committed row is not the system's to decide.
        outcome_by_requirement = {
            outcome.requirement_index: (
                POSSIBLE_MATCH if outcome.outcome == EXISTING_ROW else outcome.outcome,
                outcome.row_number,
            )
            for outcome in answer.outcomes
        }

        async with pool.connection() as connection:
            proposed = await propose_rows(
                connection,
                run_id,
                project_id,
                requirements,
                outcome_by_requirement,
            )

        _log(
            logging.INFO,
            "match_finished",
            f"Match proposed {len(proposed.proposed_row_ids)} row(s) and asked "
            f"the Delivery Owner about {len(proposed.gated_row_numbers)}.",
            run_id,
            gated_rows=proposed.gated_row_numbers,
        )
        return {"proposed_rows": len(proposed.proposed_row_ids)}

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
                    f"{project['name']}, with {state['proposed_rows']} row(s) "
                    "proposed by this run?",
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

        _log(
            logging.INFO,
            "commit_finished",
            f"Commit made {len(result.committed_row_numbers)} row(s) permanent "
            f"and exported the register.",
            run_id,
            committed_rows=result.committed_row_numbers,
            merged_rows=result.merged_row_numbers,
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
            if extraction["document_type"] == UNRELATED_DOCUMENT:
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
    graph.add_node(REVIEW_NODE, review)
    graph.add_node(COMMIT_NODE, commit)
    graph.add_node(END_EARLY_NODE, end_early)
    graph.add_node(CLOSE_WITHOUT_EXPORT_NODE, close_without_export)

    graph.add_edge(START, INGEST_NODE)
    graph.add_conditional_edges(
        INGEST_NODE,
        _route_after_ingest,
        [EXTRACT_NODE, END_EARLY_NODE],
    )
    graph.add_conditional_edges(
        EXTRACT_NODE,
        _route_after_extract,
        [EXTRACT_NODE, MATCH_NODE, END_EARLY_NODE],
    )
    graph.add_conditional_edges(
        MATCH_NODE,
        _route_after_match,
        [REVIEW_NODE, END_EARLY_NODE],
    )
    graph.add_conditional_edges(
        REVIEW_NODE,
        _route_after_review,
        [COMMIT_NODE, CLOSE_WITHOUT_EXPORT_NODE],
    )
    graph.add_edge(COMMIT_NODE, END)
    graph.add_edge(END_EARLY_NODE, END)
    graph.add_edge(CLOSE_WITHOUT_EXPORT_NODE, END)
    return graph.compile(checkpointer=checkpointer)


def _route_after_ingest(state: RunState) -> str:
    return EXTRACT_NODE if state.get("document_ids") else END_EARLY_NODE


def _route_after_extract(state: RunState) -> str:
    if state["next_document_index"] < len(state["document_ids"]):
        return EXTRACT_NODE
    return MATCH_NODE if state.get("requirements_found") else END_EARLY_NODE


def _route_after_match(state: RunState) -> str:
    return REVIEW_NODE if state.get("proposed_rows") else END_EARLY_NODE


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
