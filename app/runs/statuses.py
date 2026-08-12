from __future__ import annotations


WAITING = "waiting"
RUNNING = "running"
WAITING_FOR_REVIEW = "waiting for review"
DONE = "done"
CLOSED_WITHOUT_EXPORT = "closed without export"

TERMINAL_STATUSES = (DONE, CLOSED_WITHOUT_EXPORT)

INGEST_STAGE = "ingest"
EXTRACT_STAGE = "extract"
MATCH_STAGE = "match"
REVIEW_STAGE = "review"
COMMIT_STAGE = "commit"
