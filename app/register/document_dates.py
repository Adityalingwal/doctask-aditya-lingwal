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
    placed = [_placed(one["document_date"]["summary"]) for one in dated]
    # One date nobody can place makes the whole comparison a guess: the
    # unplaceable one may itself be the earliest, and sorting it last would let
    # the row claim a first-seen date its own evidence does not support. Read
    # order claims nothing, so read order is what is kept.
    if any(when is None for when in placed):
        return dated[0]
    return min(zip(placed, dated), key=lambda pair: pair[0])[1]


def earlier_of(held: str, arriving: str) -> str:
    """The earlier of two written dates, keeping the held one where unplaceable.

    A merge brings a second document's date onto a row that already carries
    one. Where either cannot be placed the row keeps what it had, for the same
    reason `earliest_dated` keeps read order: an order nobody can check is not
    an order.
    """
    first, second = _placed(held), _placed(arriving)
    if first is None or second is None:
        return held
    return held if first <= second else arriving


def _placed(written: str) -> date | None:
    for wording in DATE_WORDINGS:
        try:
            return datetime.strptime(written.strip(), wording).date()
        except ValueError:
            continue
    return None
