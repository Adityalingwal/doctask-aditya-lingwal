from __future__ import annotations

from pathlib import Path
from typing import Any

from app.match.match_requirements import MATCH_PROMPT_MARKER


EXTRACT_MARKER = "File name: {source_file}"
# Only Match is sent the requirements as JSON, so this marker picks out the
# Match call of the run whose batch holds one named document.
MATCH_BATCH_MARKER = '"source_file": "{source_file}"'


def write_meeting_note(folder: Path, source_file: str, requirement: str) -> str:
    """One fabricated meeting note, and the words a citation must be traced to."""
    quote = f"The client asked for {requirement}."
    (folder / source_file).write_text(
        f"# Intake portal — {source_file}\n\n"
        "**Date:** 10 March 2026\n\n"
        "## Discussion\n\n"
        f"{quote}\n",
        encoding="utf-8",
    )
    return quote


def extraction_answer(summary: str, quote: str) -> dict[str, Any]:
    return {
        "document_type": "meeting notes",
        "document_date": {
            "value": "10 March 2026",
            "quote": "**Date:** 10 March 2026",
        },
        "requirements": [{"summary": summary, "quote": quote}],
        "testing_observations": [],
        "blockers": [],
        "embedded_instructions": [],
    }


def match_answer(requirement_count: int) -> dict[str, Any]:
    return {
        "outcomes": [
            {"requirement_index": index, "outcome": "new row", "row_number": None}
            for index in range(requirement_count)
        ]
    }


def match_answer_existing_row(row_number: int) -> dict[str, Any]:
    """Match reporting that the one requirement in this batch is already a row."""
    return {
        "outcomes": [
            {
                "requirement_index": 0,
                "outcome": "existing row",
                "row_number": row_number,
            }
        ]
    }


def extract_marker(source_file: str) -> str:
    return EXTRACT_MARKER.format(source_file=source_file)


def match_marker() -> str:
    return MATCH_PROMPT_MARKER


def match_marker_for_batch_with(source_file: str) -> str:
    return MATCH_BATCH_MARKER.format(source_file=source_file)
