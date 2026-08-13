from __future__ import annotations


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
