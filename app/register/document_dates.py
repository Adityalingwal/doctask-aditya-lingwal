from __future__ import annotations

from datetime import date, datetime
from typing import Any


# How a document writes the date it states about itself, in the wordings this
# system can place against one another. Extract copies the date as the document
# wrote it, so a date written any other way still reaches the cell unchanged —
# it simply cannot be ordered, and the row keeps read order rather than
# claiming an order nobody could check.
DATE_WORDINGS = ("%d %B %Y", "%d %b %Y", "%Y-%m-%d")


def earliest_dated(requirements: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The requirement whose document states the earliest date, or None.

    One ask can be stated in two documents a week apart, and the batch is read
    in file-name order, so the document read first is not the document that
    raised the ask first.
    """
    dated = [one for one in requirements if one.get("document_date") is not None]
    if not dated:
        return None
    return min(
        enumerate(dated),
        key=lambda pair: _when(pair[1]["document_date"]["summary"], pair[0]),
    )[1]


def _when(written: str, read_order: int) -> tuple[bool, date, int]:
    placed = _placed(written)
    return (placed is None, placed or date.min, read_order)


def _placed(written: str) -> date | None:
    for wording in DATE_WORDINGS:
        try:
            return datetime.strptime(written.strip(), wording).date()
        except ValueError:
            continue
    return None
