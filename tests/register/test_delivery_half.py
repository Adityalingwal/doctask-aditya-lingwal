from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    match_answer,
    match_answer_of,
    match_marker,
    no_findings_answer,
    observation_marker,
)
from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)

from app.register.cells import CELL_NAMES


MEETING_NOTES_FILE = "meeting-notes-10-mar.md"
TESTING_FILE = "testing-feedback-25-mar.md"
HANDOVER_FILE = "handover-summary-30-mar.md"
WRITTEN_SCOPE_FILE = "client-requirements-12-mar.md"

ASKED = "an email notification to the operations team on submit"
SECOND_ASKED = "a search over old intake records"
ASKED_QUOTE = "The client asked for an email notification to the operations team."
SECOND_QUOTE = "The client also asked to search old intake records."
TESTING_QUOTE = "The email notification reaches the operations team every time."
HANDOVER_QUOTE = "The intake portal was handed over to the client's team."
WRITTEN_QUOTE = "An email notification to the operations team on every submit."

MEETING_DATE = "10 March 2026"
WRITTEN_DATE = "12 March 2026"
TESTING_DATE = "25 March 2026"
HANDOVER_DATE = "30 March 2026"

NO_EVIDENCE_YET = "No evidence yet"


def _write_document(folder: Path, name: str, date: str, line: str) -> None:
    (folder / name).write_text(
        f"# Intake portal — {name}\n\n"
        f"**Date:** {date}\n\n"
        "## Notes\n\n"
        f"{line}\n",
        encoding="utf-8",
    )


def _dated(date: str) -> dict[str, str]:
    return {"value": date, "quote": f"**Date:** {date}"}


def _asks(requirements: list[tuple[str, str]], date: str, document_type: str) -> dict:
    return {
        "document_type": document_type,
        "document_date": _dated(date),
        "requirements": [
            {"summary": summary, "quote": quote} for summary, quote in requirements
        ],
        "testing_observations": [],
        "delivery_evidence": [],
        "blockers": [],
        "embedded_instructions": [],
    }


def _testing(observations: list[tuple[str, str, str]], date: str = TESTING_DATE) -> dict:
    return {
        "document_type": "testing feedback",
        "document_date": _dated(date),
        "requirements": [],
        "testing_observations": [
            {"summary": summary, "label": label, "quote": quote}
            for summary, label, quote in observations
        ],
        "delivery_evidence": [],
        "blockers": [],
        "embedded_instructions": [],
    }


def _handover(delivered: list[tuple[str, str]], date: str = HANDOVER_DATE) -> dict:
    return {
        "document_type": "related additional document",
        "document_date": _dated(date),
        "requirements": [],
        "testing_observations": [],
        "delivery_evidence": [
            {"summary": summary, "quote": quote} for summary, quote in delivered
        ],
        "blockers": [],
        "embedded_instructions": [],
    }


class Finished:
    """One finished run: the register it left, its payload, and its export."""

    def __init__(self, rows: dict[int, dict[str, str]], run: dict, export: dict):
        self.rows = rows
        self.run = run
        self.export = export


def _run_once(
    tmp_path: Path,
    documents: list[tuple[str, str, str]],
    answers: dict[str, dict],
    reject_observation_matches: bool = False,
) -> Finished:
    """One project, one run over the documents given, taken through review."""
    with temporary_project_folder("delivery-half") as (folder, source_folder_path):
        for name, date, line in documents:
            _write_document(folder, name, date, line)
        script_path = tmp_path / "script.json"
        write_script(script_path, answers)

        with temporary_database() as database_url:
            application = ApplicationProcess(
                database_url=database_url,
                script_path=script_path,
                call_log_path=tmp_path / "model-calls.jsonl",
            )
            application.start()
            try:
                with application.client() as client:
                    project_id = client.post(
                        "/projects", json={"source_folder_path": source_folder_path}
                    ).json()["project_id"]
                    run_id = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    at_review = wait_for_run_status(client, run_id, "needs review")
                    if reject_observation_matches:
                        _reject_every_observation_match(client, run_id)
                    approve_every_decision(client, run_id)
                    client.post(f"/runs/{run_id}/finish-review").raise_for_status()
                    wait_for_run_status(client, run_id, "done")
                    export = client.get(f"/runs/{run_id}/export").json()
            finally:
                application.stop()
            rows = _stored_cells(database_url, project_id)
    return Finished(rows, at_review, export)


def _reject_every_observation_match(client: Any, run_id: str) -> None:
    for decision in client.get(f"/runs/{run_id}").json()["decisions"]:
        if decision["kind"] != "observation match":
            continue
        client.post(
            f"/runs/{run_id}/decisions",
            json={"decision_id": decision["decision_id"], "outcome": "rejected"},
        ).raise_for_status()


def _stored_cells(database_url: str, project_id: str) -> dict[int, dict[str, str]]:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            rows = (
                connection.execute(
                    text(
                        "SELECT row_number, " + ", ".join(CELL_NAMES) + " "
                        "FROM register_rows WHERE project_id = :project_id "
                        "AND is_committed ORDER BY row_number"
                    ),
                    {"project_id": project_id},
                )
                .mappings()
                .all()
            )
    finally:
        engine.dispose()
    return {
        row["row_number"]: {name: row[name] for name in CELL_NAMES} for row in rows
    }


def _citations_on(export: dict, row_number: int, cell: str) -> list[dict]:
    for row in export["rows"]:
        if row["row_number"] == row_number:
            return [one for one in row["citations"] if one["cell"] == cell]
    return []


def test_a_passed_observation_moves_the_status_to_done_with_its_citation(
    tmp_path: Path,
) -> None:
    finished = _run_once(
        tmp_path,
        [
            (MEETING_NOTES_FILE, MEETING_DATE, ASKED_QUOTE),
            (TESTING_FILE, TESTING_DATE, TESTING_QUOTE),
        ],
        {
            extract_marker(MEETING_NOTES_FILE): _asks(
                [(ASKED, ASKED_QUOTE)], MEETING_DATE, "meeting notes"
            ),
            extract_marker(TESTING_FILE): _testing(
                [("the notification reaches the team", "Passed", TESTING_QUOTE)]
            ),
            match_marker(): match_answer(1),
            observation_marker(): match_answer_of([1]),
            examine_marker(): no_findings_answer(),
        },
    )

    assert finished.rows[1]["status"] == "Done"
    assert finished.rows[1]["what_testing_found"] == "the notification reaches the team"
    # The status is a claim, so it carries the words that support it.
    cited = _citations_on(finished.export, 1, "status")
    assert [one["source_file"] for one in cited] == [TESTING_FILE]
    assert cited[0]["source_words"] == TESTING_QUOTE


def test_a_change_request_never_moves_the_status(tmp_path: Path) -> None:
    finished = _run_once(
        tmp_path,
        [
            (MEETING_NOTES_FILE, MEETING_DATE, ASKED_QUOTE),
            (TESTING_FILE, TESTING_DATE, TESTING_QUOTE),
        ],
        {
            extract_marker(MEETING_NOTES_FILE): _asks(
                [(ASKED, ASKED_QUOTE)], MEETING_DATE, "meeting notes"
            ),
            extract_marker(TESTING_FILE): _testing(
                [("the team wants a daily digest too", "Change request", TESTING_QUOTE)]
            ),
            match_marker(): match_answer(1),
            observation_marker(): match_answer_of([1]),
            examine_marker(): no_findings_answer(),
        },
    )

    # A new ask arriving during testing is not a verdict on the work. Moving
    # the status here would make the register claim the client asked earlier.
    assert finished.rows[1]["status"] == NO_EVIDENCE_YET
    assert finished.rows[1]["what_testing_found"] == "the team wants a daily digest too"


def test_a_row_no_document_mentions_keeps_no_evidence_yet(tmp_path: Path) -> None:
    finished = _run_once(
        tmp_path,
        [
            (MEETING_NOTES_FILE, MEETING_DATE, ASKED_QUOTE),
            (WRITTEN_SCOPE_FILE, WRITTEN_DATE, SECOND_QUOTE),
            (TESTING_FILE, TESTING_DATE, TESTING_QUOTE),
        ],
        {
            extract_marker(MEETING_NOTES_FILE): _asks(
                [(ASKED, ASKED_QUOTE)], MEETING_DATE, "meeting notes"
            ),
            extract_marker(WRITTEN_SCOPE_FILE): _asks(
                [(SECOND_ASKED, SECOND_QUOTE)], WRITTEN_DATE, "meeting notes"
            ),
            extract_marker(TESTING_FILE): _testing(
                [("the notification reaches the team", "Passed", TESTING_QUOTE)]
            ),
            match_marker(): match_answer(2),
            observation_marker(): match_answer_of([1]),
            examine_marker(): no_findings_answer(),
        },
    )

    assert finished.rows[1]["status"] == "Done"
    # Nothing read said anything about the search row, so it claims nothing.
    assert finished.rows[2]["status"] == NO_EVIDENCE_YET
    assert finished.rows[2]["what_testing_found"].startswith("Not known yet")
    assert finished.rows[2]["first_seen"] == finished.rows[2]["last_moved"]


def test_last_moved_carries_the_date_of_the_document_that_moved_the_row(
    tmp_path: Path,
) -> None:
    finished = _run_once(
        tmp_path,
        [
            (MEETING_NOTES_FILE, MEETING_DATE, ASKED_QUOTE),
            (TESTING_FILE, TESTING_DATE, TESTING_QUOTE),
        ],
        {
            extract_marker(MEETING_NOTES_FILE): _asks(
                [(ASKED, ASKED_QUOTE)], MEETING_DATE, "meeting notes"
            ),
            extract_marker(TESTING_FILE): _testing(
                [("the notification reaches the team", "Passed", TESTING_QUOTE)]
            ),
            match_marker(): match_answer(1),
            observation_marker(): match_answer_of([1]),
            examine_marker(): no_findings_answer(),
        },
    )

    # Both dates come from documents, and they finally differ: one names when
    # the ask was first seen, the other when the row last changed.
    assert finished.rows[1]["first_seen"] == MEETING_DATE
    assert finished.rows[1]["last_moved"] == TESTING_DATE


def test_a_handover_summary_moves_an_existing_row_and_creates_none(
    tmp_path: Path,
) -> None:
    finished = _run_once(
        tmp_path,
        [
            (MEETING_NOTES_FILE, MEETING_DATE, ASKED_QUOTE),
            (HANDOVER_FILE, HANDOVER_DATE, HANDOVER_QUOTE),
        ],
        {
            extract_marker(MEETING_NOTES_FILE): _asks(
                [(ASKED, ASKED_QUOTE)], MEETING_DATE, "meeting notes"
            ),
            extract_marker(HANDOVER_FILE): _handover(
                [("the intake portal was handed over", HANDOVER_QUOTE)]
            ),
            match_marker(): match_answer(1),
            observation_marker(): match_answer_of([1]),
            examine_marker(): no_findings_answer(),
        },
    )

    # One row, from the meeting note alone. The handover moved it and made none.
    assert sorted(finished.rows) == [1]
    assert finished.rows[1]["last_moved"] == HANDOVER_DATE
    # A handover says the work exists, never that it behaves as asked, so it
    # is not on its own a reason to call the row Done.
    assert finished.rows[1]["status"] == NO_EVIDENCE_YET


def test_a_row_created_and_moved_in_the_same_batch_ends_with_both_its_evidence(
    tmp_path: Path,
) -> None:
    finished = _run_once(
        tmp_path,
        [
            (MEETING_NOTES_FILE, MEETING_DATE, ASKED_QUOTE),
            (WRITTEN_SCOPE_FILE, WRITTEN_DATE, WRITTEN_QUOTE),
            (TESTING_FILE, TESTING_DATE, TESTING_QUOTE),
            (HANDOVER_FILE, HANDOVER_DATE, HANDOVER_QUOTE),
        ],
        {
            extract_marker(MEETING_NOTES_FILE): _asks(
                [(ASKED, ASKED_QUOTE)], MEETING_DATE, "meeting notes"
            ),
            extract_marker(WRITTEN_SCOPE_FILE): _asks(
                [(ASKED, WRITTEN_QUOTE)],
                WRITTEN_DATE,
                "client requirements document",
            ),
            extract_marker(TESTING_FILE): _testing(
                [("the notification reaches the team", "Passed", TESTING_QUOTE)]
            ),
            extract_marker(HANDOVER_FILE): _handover(
                [("the intake portal was handed over", HANDOVER_QUOTE)]
            ),
            # Both statements of the ask become rows; the review queue is what
            # settles whether they are one, exactly as before this work.
            match_marker(): match_answer(2),
            observation_marker(): match_answer_of([1, 1]),
            examine_marker(): no_findings_answer(),
        },
    )

    # All four kinds of document in one run: row 1 is created by the written
    # scope (documents are read in file-name order, so it is read first) and
    # moved by the testing feedback and the handover, without a second run.
    assert finished.rows[1]["what_was_asked"] == ASKED
    assert finished.rows[1]["in_writing"].startswith("Yes")
    assert finished.rows[1]["status"] == "Done"
    assert finished.rows[1]["what_testing_found"] == "the notification reaches the team"
    assert finished.rows[1]["first_seen"] == WRITTEN_DATE
    # Two documents move this row in one batch. `last_moved` carries the date
    # of the one read last, which is the one whose value the cell ends holding
    # — the documents are read in file-name order, not date order.
    assert finished.rows[1]["last_moved"] == TESTING_DATE


def test_an_uncertain_observation_to_row_link_is_flagged_and_never_settled(
    tmp_path: Path,
) -> None:
    answers = {
        extract_marker(MEETING_NOTES_FILE): _asks(
            [(ASKED, ASKED_QUOTE)], MEETING_DATE, "meeting notes"
        ),
        extract_marker(TESTING_FILE): _testing(
            [("something the tester was vague about", "Passed", TESTING_QUOTE)]
        ),
        match_marker(): match_answer(1),
        observation_marker(): {
            "outcomes": [
                {
                    "requirement_index": 0,
                    "outcome": "possible match",
                    "row_number": 1,
                }
            ]
        },
        examine_marker(): no_findings_answer(),
    }
    documents = [
        (MEETING_NOTES_FILE, MEETING_DATE, ASKED_QUOTE),
        (TESTING_FILE, TESTING_DATE, TESTING_QUOTE),
    ]

    finished = _run_once(tmp_path, documents, answers, reject_observation_matches=True)

    # The uncertain link was put to a person rather than settled by the system,
    # and rejecting it leaves the row claiming nothing.
    asked = [
        decision
        for decision in finished.run["decisions"]
        if decision["kind"] == "observation match"
    ]
    assert len(asked) == 1
    assert "row #1" in asked[0]["question"]
    assert finished.rows[1]["status"] == NO_EVIDENCE_YET
    assert finished.rows[1]["what_testing_found"].startswith("Not known yet")
