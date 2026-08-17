from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    match_answer,
    match_answer_of,
    match_answer_within_batch,
    match_marker,
    match_marker_against_an_empty_register,
    no_findings_answer,
    observation_answer_of,
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

NOTHING_SAID_YET = "Nothing said yet"

# One sentence per observation, written by Match itself. Two observations
# landing on one row raise one decision, so both sentences have to survive it.
VAGUE_OBSERVATION_QUESTION = (
    f"Testing feedback ({TESTING_FILE}) says: 'something the tester was vague "
    f"about'. Is this about row #1 — {ASKED}?"
)
FIRST_OBSERVATION_QUESTION = (
    f"Testing feedback ({TESTING_FILE}) says: 'the notification reaches the "
    f"team'. Is this about row #1 — {ASKED}?"
)
SECOND_OBSERVATION_QUESTION = (
    f"Testing feedback ({TESTING_FILE}) says: 'the notification names the "
    f"visitor'. Is this about row #1 — {ASKED}?"
)


def _write_document(folder: Path, name: str, date: str, line: str) -> None:
    (folder / name).write_text(
        f"# Intake portal — {name}\n\n"
        f"**Date:** {date}\n\n"
        "## Notes\n\n"
        f"{line}\n",
        encoding="utf-8",
    )


def _asks(requirements: list[tuple[str, str]], document_type: str) -> dict:
    return {
        "document_type": document_type,
        "requirements": [
            {"summary": summary, "quote": quote} for summary, quote in requirements
        ],
        "testing_observations": [],
        "delivery_evidence": [],
        "embedded_instructions": [],
    }


def _testing(observations: list[tuple[str, str, str]]) -> dict:
    return {
        "document_type": "testing feedback",
        "requirements": [],
        "testing_observations": [
            {"summary": summary, "label": label, "quote": quote}
            for summary, label, quote in observations
        ],
        "delivery_evidence": [],
        "embedded_instructions": [],
    }


def _handover(delivered: list[tuple[str, str]]) -> dict:
    return {
        "document_type": "handover summary",
        "requirements": [],
        "testing_observations": [],
        "delivery_evidence": [
            {"summary": summary, "quote": quote} for summary, quote in delivered
        ],
        "embedded_instructions": [],
    }


class Finished:
    """One finished run: the register it left, its payload, and its export."""

    def __init__(
        self,
        rows: dict[int, dict[str, str]],
        run: dict,
        export: dict,
        audit: dict[int, dict[str, tuple[str | None, str]]] | None = None,
    ):
        self.rows = rows
        self.run = run
        self.export = export
        # Read while the temporary database still exists — it is dropped when
        # the run's context closes.
        self.audit = audit or {}


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
                    client.post(
                        f"/runs/{run_id}/finish-review",
                        json={"add_to_register": True},
                    ).raise_for_status()
                    wait_for_run_status(client, run_id, "done")
                    export = client.get(f"/runs/{run_id}/export").json()
            finally:
                application.stop()
            rows = _stored_cells(database_url, project_id)
            audit = _audit_cell_changes(database_url, project_id)
    return Finished(rows, at_review, export, audit)


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


def _findings_on(export: dict, row_number: int) -> list[dict]:
    for row in export["rows"]:
        if row["row_number"] == row_number:
            return row["findings"]
    return []


def _audit_cell_changes(
    database_url: str, project_id: str
) -> dict[int, dict[str, tuple[str | None, str]]]:
    """Every cell change recorded against each row, oldest first."""
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            entries = (
                connection.execute(
                    text(
                        "SELECT register_rows.row_number, audit.cell_name, "
                        "audit.old_value, audit.new_value "
                        "FROM audit JOIN register_rows "
                        "ON register_rows.id = audit.register_row_id "
                        "WHERE register_rows.project_id = :project_id "
                        "AND audit.cell_name IS NOT NULL "
                        "ORDER BY audit.created_at"
                    ),
                    {"project_id": project_id},
                )
                .mappings()
                .all()
            )
    finally:
        engine.dispose()
    changed: dict[int, dict[str, tuple[str | None, str]]] = {}
    for entry in entries:
        changed.setdefault(entry["row_number"], {})[entry["cell_name"]] = (
            entry["old_value"],
            entry["new_value"],
        )
    return changed


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
            extract_marker(MEETING_NOTES_FILE): _asks([(ASKED, ASKED_QUOTE)], "meeting notes"),
            extract_marker(TESTING_FILE): _testing(
                [("the notification reaches the team", "Passed", TESTING_QUOTE)]
            ),
            match_marker(): match_answer(1),
            observation_marker(): observation_answer_of([1]),
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
            extract_marker(MEETING_NOTES_FILE): _asks([(ASKED, ASKED_QUOTE)], "meeting notes"),
            extract_marker(TESTING_FILE): _testing(
                [("the team wants a daily digest too", "Change request", TESTING_QUOTE)]
            ),
            match_marker(): match_answer(1),
            observation_marker(): observation_answer_of([1]),
            examine_marker(): no_findings_answer(),
        },
    )

    # A new ask arriving during testing is not a verdict on the work. Moving
    # the status here would make the register claim the client asked earlier.
    assert finished.rows[1]["status"] == NOTHING_SAID_YET
    assert finished.rows[1]["what_testing_found"] == "the team wants a daily digest too"


def test_a_row_nobody_has_looked_at_stays_no_evidence_yet_with_no_citation(
    tmp_path: Path,
) -> None:
    finished = _run_once(
        tmp_path,
        [
            (MEETING_NOTES_FILE, MEETING_DATE, ASKED_QUOTE),
            (WRITTEN_SCOPE_FILE, WRITTEN_DATE, SECOND_QUOTE),
            (TESTING_FILE, TESTING_DATE, TESTING_QUOTE),
        ],
        {
            extract_marker(MEETING_NOTES_FILE): _asks([(ASKED, ASKED_QUOTE)], "meeting notes"),
            extract_marker(WRITTEN_SCOPE_FILE): _asks([(SECOND_ASKED, SECOND_QUOTE)], "meeting notes"),
            extract_marker(TESTING_FILE): _testing(
                [("the notification reaches the team", "Passed", TESTING_QUOTE)]
            ),
            match_marker(): match_answer(2),
            observation_marker(): observation_answer_of([1]),
            examine_marker(): no_findings_answer(),
        },
    )

    assert finished.rows[1]["status"] == "Done"
    # Nothing read said anything about the search row, so it claims nothing.
    assert finished.rows[2]["status"] == NOTHING_SAID_YET
    assert finished.rows[2]["what_testing_found"].startswith("Not known yet")
    # `Nothing said yet` names no document, so nothing is cited behind it.
    # `Not delivered` is the opposite claim and always carries a citation.
    assert _citations_on(finished.export, 2, "status") == []


def test_a_handover_with_no_testing_behind_it_moves_the_row_to_handed_over(
    tmp_path: Path,
) -> None:
    finished = _run_once(
        tmp_path,
        [
            (MEETING_NOTES_FILE, MEETING_DATE, ASKED_QUOTE),
            (HANDOVER_FILE, HANDOVER_DATE, HANDOVER_QUOTE),
        ],
        {
            extract_marker(MEETING_NOTES_FILE): _asks([(ASKED, ASKED_QUOTE)], "meeting notes"),
            extract_marker(HANDOVER_FILE): _handover(
                [("the intake portal was handed over", HANDOVER_QUOTE)]
            ),
            match_marker(): match_answer(1),
            observation_marker(): observation_answer_of([1]),
            examine_marker(): no_findings_answer(),
        },
    )

    # One row, from the meeting note alone. The handover made none.
    assert sorted(finished.rows) == [1]
    # A handover says the work exists, never that it behaves as asked, so it
    # is not on its own a reason to call the row Done — but it is a claim, and
    # a run that read it must leave a mark.
    assert finished.rows[1]["status"] == "Handed over"
    assert finished.rows[1]["what_testing_found"].startswith("Not known yet")
    assert [
        citation["source_file"]
        for citation in _citations_on(finished.export, 1, "status")
    ] == [HANDOVER_FILE]


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
            extract_marker(MEETING_NOTES_FILE): _asks([(ASKED, ASKED_QUOTE)], "meeting notes"),
            extract_marker(WRITTEN_SCOPE_FILE): _asks(
                [(ASKED, WRITTEN_QUOTE)], "client requirements document"
            ),
            extract_marker(TESTING_FILE): _testing(
                [("the notification reaches the team", "Passed", TESTING_QUOTE)]
            ),
            extract_marker(HANDOVER_FILE): _handover(
                [("the intake portal was handed over", HANDOVER_QUOTE)]
            ),
            # The batch is read in workflow order, so the meeting note states
            # the ask first and the written scope matches backwards onto it.
            match_marker(): match_answer_within_batch(
                [("new row", None, None), ("existing row", None, 0)]
            ),
            observation_marker(): observation_answer_of([1, 1]),
            examine_marker(): no_findings_answer(),
        },
    )

    # All four kinds of document in one run: row 1 is created by the meeting
    # note, said again by the written scope, and moved by the testing feedback
    # and the handover, without a second run.
    assert finished.rows[1]["what_was_asked"] == ASKED
    assert finished.rows[1]["in_writing"].startswith("Yes")
    assert finished.rows[1]["status"] == "Done"
    assert finished.rows[1]["what_testing_found"] == "the notification reaches the team"


def test_an_uncertain_observation_to_row_link_is_flagged_and_never_settled(
    tmp_path: Path,
) -> None:
    answers = {
        extract_marker(MEETING_NOTES_FILE): _asks([(ASKED, ASKED_QUOTE)], "meeting notes"),
        extract_marker(TESTING_FILE): _testing(
            [("something the tester was vague about", "Passed", TESTING_QUOTE)]
        ),
        match_marker(): match_answer(1),
        observation_marker(): {
            "outcomes": [
                {
                    "observation_index": 0,
                    "outcome": "possible match",
                    "row_number": 1,
                    "question": VAGUE_OBSERVATION_QUESTION,
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
    assert asked[0]["question"] == VAGUE_OBSERVATION_QUESTION
    assert "row #1" in asked[0]["question"]
    assert finished.rows[1]["status"] == NOTHING_SAID_YET
    assert finished.rows[1]["what_testing_found"].startswith("Not known yet")


def test_a_row_this_run_moved_to_done_raises_no_finding_about_a_missing_outcome(
    tmp_path: Path,
) -> None:
    finished = _run_once(
        tmp_path,
        [
            (MEETING_NOTES_FILE, MEETING_DATE, ASKED_QUOTE),
            (TESTING_FILE, TESTING_DATE, TESTING_QUOTE),
        ],
        {
            extract_marker(MEETING_NOTES_FILE): _asks([(ASKED, ASKED_QUOTE)], "meeting notes"),
            extract_marker(TESTING_FILE): _testing(
                [("the notification reaches the team", "Passed", TESTING_QUOTE)]
            ),
            match_marker(): match_answer(1),
            observation_marker(): observation_answer_of([1]),
            examine_marker(): no_findings_answer(),
        },
    )

    # Examine judges the register this run leaves, so it must see the citation
    # this run's move supplies as well as the value. Seeing one without the
    # other makes a rule report the row as Done with no testing outcome — a
    # finding raised against the very evidence that moved it.
    assert finished.rows[1]["status"] == "Done"
    assert _findings_on(finished.export, 1) == []
    assert [one["rule_id"] for one in finished.run["examine"]["findings"]] == []


def test_not_delivered_still_needs_a_document_that_looked_and_did_not_find_it(
    tmp_path: Path,
) -> None:
    finished = _run_once(
        tmp_path,
        [
            (MEETING_NOTES_FILE, MEETING_DATE, ASKED_QUOTE),
            (TESTING_FILE, TESTING_DATE, TESTING_QUOTE),
        ],
        {
            extract_marker(MEETING_NOTES_FILE): _asks([(ASKED, ASKED_QUOTE)], "meeting notes"),
            extract_marker(TESTING_FILE): _testing(
                [("there is no notification at all", "Not found", TESTING_QUOTE)]
            ),
            match_marker(): match_answer(1),
            observation_marker(): observation_answer_of([1]),
            examine_marker(): no_findings_answer(),
        },
    )

    # Silence is not a claim: no handover said this was delivered, so testing
    # reporting it absent contradicts nothing. `Not delivered` is a positive
    # claim, so unlike `Nothing said yet` it names the document that made it.
    assert finished.rows[1]["status"] == "Not delivered"
    assert [
        citation["source_file"]
        for citation in _citations_on(finished.export, 1, "status")
    ] == [TESTING_FILE]


def test_a_handover_claiming_delivery_against_testing_reporting_missing_is_disputed(
    tmp_path: Path,
) -> None:
    finished = _run_once(
        tmp_path,
        [
            (MEETING_NOTES_FILE, MEETING_DATE, ASKED_QUOTE),
            (HANDOVER_FILE, HANDOVER_DATE, HANDOVER_QUOTE),
            (TESTING_FILE, TESTING_DATE, TESTING_QUOTE),
        ],
        {
            extract_marker(MEETING_NOTES_FILE): _asks([(ASKED, ASKED_QUOTE)], "meeting notes"),
            extract_marker(HANDOVER_FILE): _handover(
                [("the notification was handed over", HANDOVER_QUOTE)]
            ),
            extract_marker(TESTING_FILE): _testing(
                [("there is no notification at all", "Not found", TESTING_QUOTE)]
            ),
            match_marker(): match_answer(1),
            observation_marker(): observation_answer_of([1, 1]),
            examine_marker(): no_findings_answer(),
        },
    )

    # Two claims that oppose each other: one document says it was handed over,
    # another says it is not there. The system never picks a winner.
    assert finished.rows[1]["status"] == "Disputed"


def test_a_cell_moved_by_an_observation_writes_its_audit_entry_and_moves_the_fingerprint(
    tmp_path: Path,
) -> None:
    # Two runs on purpose: a row created and moved in one run never publicly
    # held "Nothing said yet", so only a second run exercises the move against
    # a row that is already committed — the branch this test exists for.
    fingerprints, audit = _committed_row_then_moved(tmp_path)

    before, after = fingerprints
    assert before != after
    assert audit["status"] == (NOTHING_SAID_YET, "Done")
    assert audit["what_testing_found"][0].startswith("Not known yet")
    assert audit["what_testing_found"][1] == "the notification reaches the team"


def _committed_row_then_moved(
    tmp_path: Path,
) -> tuple[tuple[str, str], dict[str, tuple[str | None, str]]]:
    """One run commits a row; a second run's testing feedback moves it."""
    answers = {
        extract_marker(MEETING_NOTES_FILE): _asks([(ASKED, ASKED_QUOTE)], "meeting notes"),
        extract_marker(TESTING_FILE): _testing(
            [("the notification reaches the team", "Passed", TESTING_QUOTE)]
        ),
        match_marker(): match_answer(1),
        match_marker_against_an_empty_register(): match_answer(1),
        observation_marker(): observation_answer_of([1]),
        examine_marker(): no_findings_answer(),
    }
    with temporary_project_folder("moved-row-audit") as (folder, source_folder_path):
        _write_document(folder, MEETING_NOTES_FILE, MEETING_DATE, ASKED_QUOTE)
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
                    _one_run_through_review(client, project_id)
                    before = _fingerprints(database_url, project_id)[1]

                    _write_document(
                        folder, TESTING_FILE, TESTING_DATE, TESTING_QUOTE
                    )
                    _one_run_through_review(client, project_id)
                    after = _fingerprints(database_url, project_id)[1]
                    audit = _audit_cell_changes(database_url, project_id)[1]
            finally:
                application.stop()
    return (before, after), audit


def _one_run_through_review(client: Any, project_id: str) -> None:
    run_id = client.post("/runs", json={"project_id": project_id}).json()["run_id"]
    wait_for_run_status(client, run_id, "needs review")
    approve_every_decision(client, run_id)
    client.post(
        f"/runs/{run_id}/finish-review",
        json={"add_to_register": True},
    ).raise_for_status()
    wait_for_run_status(client, run_id, "done")


def _fingerprints(database_url: str, project_id: str) -> dict[int, str]:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            rows = (
                connection.execute(
                    text(
                        "SELECT row_number, fingerprint FROM register_rows "
                        "WHERE project_id = :project_id AND is_committed"
                    ),
                    {"project_id": project_id},
                )
                .mappings()
                .all()
            )
    finally:
        engine.dispose()
    return {row["row_number"]: row["fingerprint"] for row in rows}


def test_two_observations_on_one_row_stack_their_questions_verbatim(
    tmp_path: Path,
) -> None:
    """One decision covers both observations, so it shows both sentences.

    Joining them into a new sentence would put words in front of the person
    that Match never wrote, and an audit could no longer show what was read.
    """
    finished = _run_once(
        tmp_path,
        [
            (MEETING_NOTES_FILE, MEETING_DATE, ASKED_QUOTE),
            (TESTING_FILE, TESTING_DATE, TESTING_QUOTE),
        ],
        {
            extract_marker(MEETING_NOTES_FILE): _asks(
                [(ASKED, ASKED_QUOTE)], "meeting notes"
            ),
            extract_marker(TESTING_FILE): _testing(
                [
                    ("the notification reaches the team", "Passed", TESTING_QUOTE),
                    ("the notification names the visitor", "Passed", TESTING_QUOTE),
                ]
            ),
            match_marker(): match_answer(1),
            observation_marker(): {
                "outcomes": [
                    {
                        "observation_index": 0,
                        "outcome": "possible match",
                        "row_number": 1,
                        "question": FIRST_OBSERVATION_QUESTION,
                    },
                    {
                        "observation_index": 1,
                        "outcome": "possible match",
                        "row_number": 1,
                        "question": SECOND_OBSERVATION_QUESTION,
                    },
                ]
            },
            examine_marker(): no_findings_answer(),
        },
    )

    asked = [
        decision
        for decision in finished.run["decisions"]
        if decision["kind"] == "observation match"
    ]
    assert len(asked) == 1
    assert asked[0]["question"] == (
        f"{FIRST_OBSERVATION_QUESTION}\n\n{SECOND_OBSERVATION_QUESTION}"
    )
