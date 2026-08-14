from __future__ import annotations


WAITING = "waiting"
RUNNING = "running"
WAITING_FOR_REVIEW = "waiting for review"
DONE = "done"
CLOSED_WITHOUT_EXPORT = "closed without export"
FAILED = "failed"
ENDED_WITHOUT_CHANGES = "ended without changes"

TERMINAL_STATUSES = (DONE, CLOSED_WITHOUT_EXPORT, FAILED, ENDED_WITHOUT_CHANGES)
# The project's durable lock is exactly these two: a run in any other status
# holds nothing, which is why every terminal status frees the project.
ACTIVE_STATUSES = (RUNNING, WAITING_FOR_REVIEW)

INGEST_STAGE = "ingest"
EXTRACT_STAGE = "extract"
MATCH_STAGE = "match"
EXAMINE_STAGE = "examine"
REVIEW_STAGE = "review"
COMMIT_STAGE = "commit"

# The one ordering every reader of `finished_stages` uses — kept here, beside
# the stage names themselves, so nothing else in the codebase can drift into a
# second copy of the pipeline's order.
STAGE_ORDER = (
    INGEST_STAGE,
    EXTRACT_STAGE,
    MATCH_STAGE,
    EXAMINE_STAGE,
    REVIEW_STAGE,
    COMMIT_STAGE,
)
