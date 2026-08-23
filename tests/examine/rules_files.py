from __future__ import annotations

from pathlib import Path


# The shipped `config/rules.yaml` gives every rule an `applies_when`, so a rule
# runs only once the kind of document it names has been read. A test about
# findings drives a batch of meeting notes, where none of those kinds is read
# and no rule would run at all — so it drives its own rules file instead. A
# rule with no `applies_when` always applies, which is exactly what these tests
# need; the ids and texts are the shipped ones, so what a run reports is still
# the wording a reader would meet.
RULES_THAT_ALWAYS_APPLY = """\
rules:
  - id: R1
    text: "Anything built must have a written requirement; a verbal mention is not enough."

  - id: R2
    text: "Testing feedback asking for new behaviour is a change request, not a bug."

  - id: R4
    text: "Every written requirement must have a testing outcome."

  - id: R5
    text: "No register row is 'Done' without a testing outcome."
"""

RULE_IDS_THAT_ALWAYS_APPLY = ("R1", "R2", "R4", "R5")
# The same four rules by the words a person actually meets — on a finding
# card, in the history and in the export, none of which ever shows an id.
RULE_TEXTS_THAT_ALWAYS_APPLY = {
    "R1": (
        "Anything built must have a written requirement; a verbal mention is "
        "not enough."
    ),
    "R2": (
        "Testing feedback asking for new behaviour is a change request, not a "
        "bug."
    ),
    "R4": "Every written requirement must have a testing outcome.",
    "R5": "No register row is 'Done' without a testing outcome.",
}


def rules_that_always_apply(folder: Path) -> Path:
    """Write the always-applying rules file into a test's own folder."""
    written = folder / "rules-that-always-apply.yaml"
    written.write_text(RULES_THAT_ALWAYS_APPLY, encoding="utf-8")
    return written
