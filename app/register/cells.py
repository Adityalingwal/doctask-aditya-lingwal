from __future__ import annotations

import hashlib


WHAT_WAS_ASKED = "what_was_asked"
IN_WRITING = "in_writing"
WHAT_TESTING_FOUND = "what_testing_found"
STATUS = "status"

CELL_NAMES = (
    WHAT_WAS_ASKED,
    IN_WRITING,
    WHAT_TESTING_FOUND,
    STATUS,
)

# The stored column stays `in_writing`; only the heading a reader sees asks
# the question in words a first-time reader does not have to decode. Both the
# export and the review screen print cells, so the headings live with the
# cells rather than with either surface.
COLUMN_HEADINGS = {
    WHAT_WAS_ASKED: "What was asked",
    IN_WRITING: "Written down",
    WHAT_TESTING_FOUND: "What testing found",
    STATUS: "Status",
}

STATUS_REQUESTED = "Requested"
STATUS_HANDED_OVER = "Handed over"
STATUS_DONE = "Done"
STATUS_PARTIAL = "Partial"
STATUS_NOT_DELIVERED = "Not delivered"
STATUS_DISPUTED = "Disputed"
MAXIMUM_QUOTE_CHARACTERS = 300
TRUNCATED_QUOTE_SUFFIX = "\u2026"

# A cell answers in as few words as a reader can scan down a column; the file
# behind the answer lives in the row's evidence and is never repeated here. A
# blank cell would mean both "not known" and "nothing to report", and a reader
# cannot tell which, so a cell with no answer yet still carries words.
IN_WRITING_NOT_KNOWN_YET = "Not known yet"
IN_WRITING_YES = "Yes"
TESTING_NOT_KNOWN_YET = "Not known yet"
# Said once a document of the kind that speaks to this cell has been read and
# does not mention this ask. "No" would claim more than a document saying
# nothing about an ask can support.
NOT_MENTIONED = "Not mentioned"

ABSENCE_STATEMENT = "{source_file} was read, and it does not mention this ask."


def absence_statement_for(source_file: str) -> str:
    """The one sentence standing behind every `Not mentioned` cell.

    Written in one place because both cells and both document kinds use it: a
    second writer would let `Written down` and `What testing found` describe
    the same silence in two different sentences.
    """
    return ABSENCE_STATEMENT.format(source_file=source_file)


def in_writing_says_yes(cell: str) -> bool:
    """Whether this cell reports the ask written down."""
    return cell == IN_WRITING_YES


def cells_a_merge_would_write(
    proposal_in_writing: str,
    candidate_in_writing: str,
) -> dict[str, str]:
    """Which of the surviving row's cells an approved merge moves, and to what.

    Only the cell the arriving requirement can speak to moves, and only
    towards `Yes`: the requirement can say the ask is written down and cannot
    say it is not. Written once because two readers need the same answer — the
    decision that promises the change, and Commit that makes it. A promise
    worked out separately from the write is a promise that can be broken.
    """
    if in_writing_says_yes(proposal_in_writing) and not in_writing_says_yes(
        candidate_in_writing
    ):
        return {IN_WRITING: proposal_in_writing}
    return {}


def fingerprint_of_cells(cells: dict[str, str]) -> str:
    """Hash the four cells only — attachments never move a row's fingerprint."""
    joined = "\n".join(f"{name}={cells[name]}" for name in CELL_NAMES)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def shorten_quote(source_words: str) -> str:
    if len(source_words) <= MAXIMUM_QUOTE_CHARACTERS:
        return source_words
    return source_words[:MAXIMUM_QUOTE_CHARACTERS] + TRUNCATED_QUOTE_SUFFIX
