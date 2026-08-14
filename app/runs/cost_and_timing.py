from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, NamedTuple
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from app.model.call_the_model import ReportedUsage
from app.model.client import CostRates
from app.runs.statuses import (
    COMMIT_STAGE,
    EXAMINE_STAGE,
    EXTRACT_STAGE,
    INGEST_STAGE,
    MATCH_STAGE,
    REVIEW_STAGE,
)


STAGE_KEY = "stage"
SECONDS_KEY = "seconds"
STARTED_AT_KEY = "started_at"
PROMPT_TOKENS_KEY = "prompt_tokens"
COMPLETION_TOKENS_KEY = "completion_tokens"
STAGE_ORDER = (
    INGEST_STAGE,
    EXTRACT_STAGE,
    MATCH_STAGE,
    EXAMINE_STAGE,
    REVIEW_STAGE,
    COMMIT_STAGE,
)
SECONDS_PLACES = 3
COST_PLACES = Decimal("0.000001")
ESTIMATE_NOTE = (
    "An estimate: the tokens the model reported for this run, multiplied by "
    "the rates in config/model.yaml. It is not a bill and not a measured "
    "provider charge."
)
NO_MODEL_CALL_REASON = (
    "no model call recorded a token count for this run, so there is nothing to "
    "estimate a cost from."
)


class TokenTotals(NamedTuple):
    prompt_tokens: int | None
    completion_tokens: int | None
    calls_reporting_usage: int
    calls_without_usage: int


def extract_key(document_id: UUID) -> str:
    """One Extract entry per document, so a re-entered node replaces its own.

    Extract checkpoints per document (D12), so a killed node may read one
    document again. Keyed by that document, the second pass overwrites the
    first entry instead of adding to it.
    """
    return f"{EXTRACT_STAGE}:{document_id}"


async def record_stage_duration(
    connection: AsyncConnection,
    run_id: UUID,
    key: str,
    stage: str,
    seconds: float,
) -> None:
    await connection.execute(
        "UPDATE runs SET stage_timings = stage_timings || %s WHERE id = %s",
        (
            Jsonb(
                {
                    key: {
                        STAGE_KEY: stage,
                        SECONDS_KEY: round(seconds, SECONDS_PLACES),
                    }
                }
            ),
            run_id,
        ),
    )


async def start_review_timing(connection: AsyncConnection, run_id: UUID) -> None:
    """Mark when Review began, on the database's clock rather than a process's.

    Review is interrupted and replayed, possibly by a second process after a
    crash, so no in-process clock spans it. Two durable timestamps do.
    """
    await connection.execute(
        "UPDATE runs SET stage_timings = stage_timings || "
        "jsonb_build_object(%s::text, %s::jsonb || "
        "jsonb_build_object(%s::text, to_jsonb(CURRENT_TIMESTAMP))) "
        "WHERE id = %s",
        (
            REVIEW_STAGE,
            Jsonb({STAGE_KEY: REVIEW_STAGE}),
            STARTED_AT_KEY,
            run_id,
        ),
    )


async def record_review_duration(connection: AsyncConnection, run_id: UUID) -> None:
    """How long Review waited, from the two timestamps the run already stores.

    Computed from review_finished_at rather than from the current moment, so a
    replayed Review node writes the same number it wrote the first time.
    """
    await connection.execute(
        "UPDATE runs SET stage_timings = stage_timings || jsonb_build_object("
        "  %s::text, (stage_timings -> %s::text) || jsonb_build_object("
        "    %s::text, round(extract(epoch from (review_finished_at - "
        "      ((stage_timings -> %s::text ->> %s::text)::timestamptz"
        "      )))::numeric, %s::int))"
        ") WHERE id = %s AND review_finished_at IS NOT NULL "
        "AND stage_timings -> %s::text ->> %s::text IS NOT NULL",
        (
            REVIEW_STAGE,
            REVIEW_STAGE,
            SECONDS_KEY,
            REVIEW_STAGE,
            STARTED_AT_KEY,
            SECONDS_PLACES,
            run_id,
            REVIEW_STAGE,
            STARTED_AT_KEY,
        ),
    )


async def record_model_usage(
    connection: AsyncConnection,
    run_id: UUID,
    key: str,
    stage: str,
    usage: ReportedUsage,
    rates: CostRates,
) -> None:
    """Store what one call reported, then re-estimate the run's cost from all of it."""
    await connection.execute(
        "UPDATE runs SET token_usage = token_usage || %s WHERE id = %s",
        (
            Jsonb(
                {
                    key: {
                        STAGE_KEY: stage,
                        PROMPT_TOKENS_KEY: usage.prompt_tokens,
                        COMPLETION_TOKENS_KEY: usage.completion_tokens,
                    }
                }
            ),
            run_id,
        ),
    )
    recorded = await connection.execute(
        "SELECT token_usage FROM runs WHERE id = %s", (run_id,)
    )
    estimate, unknown_reason = estimate_cost_usd(
        token_totals((await recorded.fetchone())["token_usage"]), rates
    )
    await connection.execute(
        "UPDATE runs SET estimated_cost_usd = %s, cost_unknown_reason = %s "
        "WHERE id = %s",
        (estimate, unknown_reason, run_id),
    )


def estimate_cost_usd(
    totals: TokenTotals,
    rates: CostRates,
) -> tuple[Decimal | None, str | None]:
    """The estimate those tokens and those rates give, or why there is none."""
    if totals.calls_reporting_usage == 0:
        return None, (
            f"the model reported no token count for this run's "
            f"{totals.calls_without_usage} call(s), so no cost can be "
            "estimated from them."
        )
    if rates.missing_reason is not None:
        return None, rates.missing_reason
    estimate = (
        Decimal(totals.prompt_tokens) * rates.prompt_usd_per_token
        + Decimal(totals.completion_tokens) * rates.completion_usd_per_token
    )
    return estimate.quantize(COST_PLACES, rounding=ROUND_HALF_UP), None


def token_totals(token_usage: dict[str, Any]) -> TokenTotals:
    """What every recorded call adds up to, counting the silent ones separately."""
    reported = [
        recorded
        for recorded in token_usage.values()
        if recorded[PROMPT_TOKENS_KEY] is not None
        and recorded[COMPLETION_TOKENS_KEY] is not None
    ]
    if not reported:
        return TokenTotals(None, None, 0, len(token_usage))
    return TokenTotals(
        sum(recorded[PROMPT_TOKENS_KEY] for recorded in reported),
        sum(recorded[COMPLETION_TOKENS_KEY] for recorded in reported),
        len(reported),
        len(token_usage) - len(reported),
    )


def cost_and_timing_of_run(run: dict[str, Any]) -> dict[str, Any]:
    """What one run reports about how long it took and what it is estimated to cost."""
    stages = stage_breakdown(run["stage_timings"])
    totals = token_totals(run["token_usage"])
    estimate = run["estimated_cost_usd"]
    return {
        "stages": stages,
        "total_seconds": round(
            sum(stage[SECONDS_KEY] for stage in stages), SECONDS_PLACES
        ),
        "tokens": {
            "prompt": totals.prompt_tokens,
            "completion": totals.completion_tokens,
            "calls_reporting_usage": totals.calls_reporting_usage,
            "calls_without_usage": totals.calls_without_usage,
        },
        "estimated_cost_usd": None if estimate is None else str(estimate),
        "estimate_note": ESTIMATE_NOTE,
        "cost_unknown_reason": (
            None
            if estimate is not None
            else (run["cost_unknown_reason"] or NO_MODEL_CALL_REASON)
        ),
    }


def stage_breakdown(stage_timings: dict[str, Any]) -> list[dict[str, Any]]:
    """One entry per stage that finished, in pipeline order, and none for the rest."""
    seconds_by_stage: dict[str, float] = {}
    for recorded in stage_timings.values():
        if SECONDS_KEY not in recorded:
            continue
        stage = recorded[STAGE_KEY]
        seconds_by_stage[stage] = seconds_by_stage.get(stage, 0.0) + float(
            recorded[SECONDS_KEY]
        )
    return [
        {STAGE_KEY: stage, SECONDS_KEY: round(seconds_by_stage[stage], SECONDS_PLACES)}
        for stage in STAGE_ORDER
        if stage in seconds_by_stage
    ]
