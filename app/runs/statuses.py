from __future__ import annotations


WAITING = "waiting"
RUNNING = "running"
WAITING_FOR_REVIEW = "waiting for review"
DONE = "done"
CLOSED_WITHOUT_EXPORT = "closed without export"

# A run holding its project's lock is one in either of these two states.
ACTIVE_STATUSES = (RUNNING, WAITING_FOR_REVIEW)
TERMINAL_STATUSES = (DONE, CLOSED_WITHOUT_EXPORT)

INGEST_STAGE = "ingest"
EXTRACT_STAGE = "extract"
MATCH_STAGE = "match"
REVIEW_STAGE = "review"
COMMIT_STAGE = "commit"
