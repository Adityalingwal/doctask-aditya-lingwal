from __future__ import annotations

import hashlib


WHAT_WAS_ASKED = "what_was_asked"
IN_WRITING = "in_writing"
WHAT_TESTING_FOUND = "what_testing_found"
STATUS = "status"
BLOCKED_ON = "blocked_on"
FIRST_SEEN = "first_seen"
LAST_MOVED = "last_moved"

CELL_NAMES = (
    WHAT_WAS_ASKED,
    IN_WRITING,
    WHAT_TESTING_FOUND,
    STATUS,
    BLOCKED_ON,
    FIRST_SEEN,
    LAST_MOVED,
)

STATUS_NO_EVIDENCE_YET = "No evidence yet"
STATUS_WITHDRAWN = "Withdrawn"
DATE_UNKNOWN = "date unknown"
MAXIMUM_QUOTE_CHARACTERS = 300
TRUNCATED_QUOTE_SUFFIX = "…"

# A cell whose answer is not known says so in words. A blank cell would mean
# both "not known" and "nothing to report", and a reader cannot tell which.
IN_WRITING_NOT_KNOWN_YET = (
    "Not known yet — no client requirements document has been read for this "
    "project."
)
TESTING_NOT_KNOWN_YET = (
    "Not known yet — no testing outcome has been read for this requirement."
)
BLOCKED_ON_NOT_KNOWN_YET = (
    "Not known yet — no source read so far reports work stopped on this "
    "requirement."
)


def fingerprint_of_cells(cells: dict[str, str]) -> str:
    """Hash the seven cells only — attachments never move a row's fingerprint."""
    joined = "\n".join(f"{name}={cells[name]}" for name in CELL_NAMES)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def shorten_quote(source_words: str) -> str:
    if len(source_words) <= MAXIMUM_QUOTE_CHARACTERS:
        return source_words
    return source_words[:MAXIMUM_QUOTE_CHARACTERS] + TRUNCATED_QUOTE_SUFFIX
