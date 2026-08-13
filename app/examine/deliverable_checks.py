from __future__ import annotations

from typing import Any

from app.examine.found_issue import finding_on_row
from app.register.cells import WHAT_TESTING_FOUND


D1 = "D1"
D2 = "D2"
DONE_STATUS = "Done"

# The two checks the deliverable itself owes, whatever the user's rules say.
# They are code, not configuration: both are mechanical facts about the stored
# register, so a query answers them faster and more reliably than a model.
DELIVERABLE_CHECKS = (
    {"id": D1, "text": "Every register row cites a source."},
    {
        "id": D2,
        "text": f"No register row is '{DONE_STATUS}' without a testing outcome.",
    },
)
DELIVERABLE_CHECK_IDS = tuple(check["id"] for check in DELIVERABLE_CHECKS)
_TEXT_BY_ID = {check["id"]: check["text"] for check in DELIVERABLE_CHECKS}


def deliverable_findings(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run both deliverable checks over the stored register, in code.

    Each is a mechanical fact about what is stored — a citation is there or it
    is not — so they are answered by looking, not by asking a model.
    """
    found: list[dict[str, Any]] = []
    for row in rows:
        if not row["cited_cells"]:
            found.append(
                finding_on_row(
                    D1,
                    _TEXT_BY_ID[D1],
                    row,
                    "This row cites no source at all.",
                    f"Row #{row['row_number']} has no citation on any of its "
                    "seven cells.",
                )
            )
        if (
            row["cells"]["status"] == DONE_STATUS
            and WHAT_TESTING_FOUND not in row["cited_cells"]
        ):
            found.append(
                finding_on_row(
                    D2,
                    _TEXT_BY_ID[D2],
                    row,
                    f"This row is '{DONE_STATUS}' and no testing outcome was "
                    "read for it.",
                    f"Row #{row['row_number']} reads "
                    f"'{row['cells'][WHAT_TESTING_FOUND]}' and no citation "
                    "supports that cell.",
                )
            )
    return found
