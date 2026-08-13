from __future__ import annotations

from uuid import UUID

from app.refusal import NotPossibleNow
from app.review.review_queue import unanswered_decisions
from app.runs.run_lifecycle import REVIEW_FINISHED, RunEngine, resume_after_review
from app.runs.run_records import claim_review_finished, require_run
from app.runs.statuses import WAITING_FOR_REVIEW


async def finish_review(engine: RunEngine, run_id: UUID) -> dict[str, str]:
    """Take one run out of review once every gate it raised has been answered."""
    async with engine.pool.connection() as connection:
        run = await require_run(connection, run_id)
        if run["status"] != WAITING_FOR_REVIEW:
            raise NotPossibleNow(
                f"this run is '{run['status']}', not at review, so there is no "
                "review to finish."
            )
        outstanding = await unanswered_decisions(connection, run_id)
        if outstanding:
            # Finishing with an unanswered gate would claim the review completed
            # while an approved output may not exist.
            raise NotPossibleNow(
                f"review cannot finish while {len(outstanding)} decision(s) are "
                "unanswered: "
                + "; ".join(
                    f"{decision['id']} — {decision['question']}"
                    for decision in outstanding
                )
                + f". Answer each with POST /runs/{run_id}/decisions, then "
                "finish the review again."
            )
        # The run leaves review here, before anything is launched: an answer
        # that nothing in the database records would be a false success.
        claimed = await claim_review_finished(connection, run_id)

    if claimed is None:
        raise NotPossibleNow(
            "this run's review was finished by another call a moment ago, so "
            f"this one changed nothing — poll GET /runs/{run_id} for what that "
            "run does next."
        )

    resume_after_review(engine, run_id, claimed["project_id"])
    return {"run_id": str(run_id), "status": REVIEW_FINISHED}
