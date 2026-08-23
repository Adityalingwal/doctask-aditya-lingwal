from __future__ import annotations

from typing import Any, NamedTuple

from app.ingest.source_line import SAYS, source_line
from app.register.cells import CELL_NAMES, COLUMN_HEADINGS


REGISTER_ROW_LABEL = "Register row {row_number}"
PROPOSED_ROW_LABEL = "Row {row_number} (proposed by this run)"

# A person reads the whole decision as one text; the screen and the MCP caller
# read the same parts it was built from. Blocks are separated by a blank line
# and the lines inside one block by a single break, which is what the review
# screen already splits on.
BLOCKS_JOINED_BY = "\n\n"
LINES_JOINED_BY = "\n"
# Two cells that change on one row are read across one line, so they are
# spaced apart rather than run together.
CHANGES_JOINED_BY = "  "

SAME_ASK_QUESTION = "Is this the same ask as row {row_number}?"
ABOUT_THIS_ROW_QUESTION = "Is this about row {row_number}?"
BREAKS_THIS_RULE_QUESTION = "Does row {row_number} break this rule?"

APPROVE_LINE = "Approve → {sentence}"
REJECT_LINE = "Reject → {sentence}"
ROW_CHANGES = "Row {row_number} changes: {changes}"
ROW_UNCHANGED = "Row {row_number} stays as it is."
# A merge that writes no cell still moves the ask's evidence onto the row, so
# the sentence says what does happen rather than only what does not.
NOTHING_CHANGES_ON_A_MERGE = (
    "Row {row_number} stays as it is; this ask's evidence is added to it."
)
NEW_ROW_ON_REJECT = (
    "A new row is created for this ask, with Written down: {in_writing}."
)
FINDING_ADDED = "The finding is added to row {row_number}."
FINDING_NOT_ADDED = "The finding is not added."
RULE_LINE = "Rule: {rule_text}"


class DecisionText(NamedTuple):
    question: str
    parts: dict[str, Any]


def register_row_label(row_number: int) -> str:
    return REGISTER_ROW_LABEL.format(row_number=row_number)


def proposed_row_label(row_number: int) -> str:
    """A candidate this same run proposed is not on the register yet (S24)."""
    return PROPOSED_ROW_LABEL.format(row_number=row_number)


def quote_block(source_file: str, source_place: str, quote: str) -> dict[str, str]:
    return {
        "source_line": source_line(source_file, source_place),
        # A quote spanning two paragraphs keeps its words and loses its blank
        # lines: a blank line is the text's own block boundary, and one inside
        # a quote would shift every block the screen counts after it. The
        # committed citation keeps the document's exact words; this is the
        # decision card's copy only.
        "quote": _without_blank_lines(quote),
    }


def _without_blank_lines(quote: str) -> str:
    return LINES_JOINED_BY.join(
        line for line in (line.strip() for line in quote.splitlines()) if line
    )


def possible_match_text(
    row_number: int,
    row_label: str,
    cells: dict[str, str],
    quote: dict[str, str],
    if_approved: list[dict[str, str]],
    proposed_in_writing: str,
) -> DecisionText:
    """The whole text asked before two statements are treated as one ask."""
    approve = (
        ROW_CHANGES.format(row_number=row_number, changes=_changes(if_approved))
        if if_approved
        else NOTHING_CHANGES_ON_A_MERGE.format(row_number=row_number)
    )
    reject = NEW_ROW_ON_REJECT.format(in_writing=proposed_in_writing)
    return _built(
        row_number=row_number,
        row_label=row_label,
        cells=cells,
        quotes=[quote],
        rule_text=None,
        issue=None,
        question=SAME_ASK_QUESTION.format(row_number=row_number),
        if_approved=if_approved,
        approve=approve,
        if_rejected=reject,
    )


def observation_match_text(
    row_number: int,
    row_label: str,
    cells: dict[str, str],
    quotes: list[dict[str, str]],
    if_approved: list[dict[str, str]],
) -> DecisionText:
    """The whole text asked before a report's words change what a row says.

    One row's observations are one decision with one question, and each of
    them keeps its own quote block — nothing is stitched into a paragraph
    nobody wrote.
    """
    return _built(
        row_number=row_number,
        row_label=row_label,
        cells=cells,
        quotes=quotes,
        rule_text=None,
        issue=None,
        question=ABOUT_THIS_ROW_QUESTION.format(row_number=row_number),
        if_approved=if_approved,
        approve=ROW_CHANGES.format(
            row_number=row_number, changes=_changes(if_approved)
        ),
        if_rejected=ROW_UNCHANGED.format(row_number=row_number),
    )


def finding_text(
    row_number: int,
    cells: dict[str, str],
    rule_text: str,
    issue: str,
) -> DecisionText:
    """The whole text asked before a rule finding is attached to a row.

    Every line but one is built here. The issue line is the model's own
    sentence about the rule it was given (S27), and it is the only sentence a
    template cannot write, because only the rule says what breaking it means.
    """
    return _built(
        row_number=row_number,
        row_label=register_row_label(row_number),
        cells=cells,
        quotes=[],
        rule_text=rule_text,
        issue=issue,
        question=BREAKS_THIS_RULE_QUESTION.format(row_number=row_number),
        if_approved=[],
        approve=FINDING_ADDED.format(row_number=row_number),
        if_rejected=FINDING_NOT_ADDED,
    )


def _built(
    row_number: int,
    row_label: str,
    cells: dict[str, str],
    quotes: list[dict[str, str]],
    rule_text: str | None,
    issue: str | None,
    question: str,
    if_approved: list[dict[str, str]],
    approve: str,
    if_rejected: str,
) -> DecisionText:
    parts = {
        "row": {
            "row_number": row_number,
            "label": row_label,
            "cells": cells,
        },
        "quotes": quotes,
        "rule_text": rule_text,
        "issue": issue,
        "question": question,
        "if_approved": if_approved,
        "if_rejected": if_rejected,
    }
    blocks = [_row_block(row_label, cells)]
    if rule_text is not None:
        blocks.append(RULE_LINE.format(rule_text=rule_text))
    if issue is not None:
        blocks.append(issue)
    blocks += [_quote_block_text(one) for one in quotes]
    blocks.append(question)
    blocks.append(
        LINES_JOINED_BY.join(
            [
                APPROVE_LINE.format(sentence=approve),
                REJECT_LINE.format(sentence=if_rejected),
            ]
        )
    )
    return DecisionText(question=BLOCKS_JOINED_BY.join(blocks), parts=parts)


def _row_block(row_label: str, cells: dict[str, str]) -> str:
    return LINES_JOINED_BY.join(
        [row_label] + [f"{heading}: {value}" for heading, value in cells.items()]
    )


def _quote_block_text(quote: dict[str, str]) -> str:
    return LINES_JOINED_BY.join(
        [f"{quote['source_line']}{SAYS}", f"\"{quote['quote']}\""]
    )


def _changes(if_approved: list[dict[str, str]]) -> str:
    return CHANGES_JOINED_BY.join(
        f"{change['cell']}: {change['value']}" for change in if_approved
    )


def cells_as_a_person_reads_them(row: dict[str, Any]) -> dict[str, str]:
    """The four cells under the headings the register's table shows."""
    return {COLUMN_HEADINGS[name]: row[name] for name in CELL_NAMES}
