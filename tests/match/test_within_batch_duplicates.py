from __future__ import annotations

from pathlib import Path
from typing import Any, NamedTuple

import pytest

from app.extract.answer import CLIENT_REQUIREMENTS_DOCUMENT, MEETING_NOTES
from app.match.match_requirements import EXISTING_ROW, NEW_ROW, POSSIBLE_MATCH
from app.register.cells import (
    CELL_NAMES,
    IN_WRITING,
    IN_WRITING_NOT_KNOWN_YET,
    IN_WRITING_YES,
    NOT_MENTIONED,
    WHAT_WAS_ASKED,
)
from tests.documents.register_documents import (
    several_requirements_answer,
    examine_marker,
    extract_marker,
    match_answer_within_batch,
    match_marker,
    match_marker_for_batch_with,
    no_findings_answer,
    write_document_stating,
)
from tests.register.stored_register import StoredRow, stored_rows
from tests.runs.application import (
    ApplicationProcess,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)


# The requirements document sorts first by file name, so file-name order and
# workflow order disagree — which is the point the batch ordering has to get
# right.
REQUIREMENTS_FILE = "client-requirements-v1.md"
MEETING_FILE = "meeting-notes-10-mar.md"
# The same two documents with their file-name order reversed, so a rule that
# reads the alphabet gives the two batches different answers.
RENAMED_REQUIREMENTS = "zz-client-requirements-v1.md"
RENAMED_MEETING = "aa-meeting-notes-10-mar.md"
REQUIREMENTS_DATE = "12 March 2026"
MEETING_DATE = "10 March 2026"

WRITTEN_ASK = "an email notification to the operations team on submit"
WRITTEN_QUOTE = (
    "An email notification to the operations team whenever a visitor submits "
    "the intake form."
)
SPOKEN_ASK = "the operations team notified when a visitor submits the form"
SPOKEN_QUOTE = (
    "The client asked for the operations team to be told whenever a visitor "
    "submits the intake form."
)
SEARCH_ASK = "a search over old intake records"
SEARCH_QUOTE = "The client also asked to search old intake records."
RESTATED_ASK = "operations told about every new intake form"
RESTATED_QUOTE = "Operations must hear about every new intake form."

POSSIBLE_MATCH_DECISION = "possible match"

# The sentences Match itself writes. Both name the kind of document each
# statement came from and ask the one thing that matters, and both reach the
# card character for character — nothing here is composed by the code.
UNSURE_BATCH_QUESTION = (
    "This ask appears twice in this batch: raised in meeting notes as "
    f"{SPOKEN_ASK}, and written in the client requirements document as "
    f"{WRITTEN_ASK}. Is this the same ask?"
)
COMMITTED_ROW_QUESTION = (
    f"This ask was raised in meeting notes ({MEETING_FILE}) — row 1, "
    f"{SPOKEN_ASK}. It is now written in the client requirements document "
    f"({REQUIREMENTS_FILE}) as {WRITTEN_ASK}. Is this the same ask?"
)


class Document(NamedTuple):
    source_file: str
    document_type: str
    date: str
    requirements: list[tuple[str, str]]


class RunOutcome(NamedTuple):
    decisions: list[dict[str, Any]]
    rows: dict[int, StoredRow]
    export: dict[str, Any]


def _requirements_document(
    requirements: list[tuple[str, str]] | None = None,
) -> Document:
    return Document(
        REQUIREMENTS_FILE,
        CLIENT_REQUIREMENTS_DOCUMENT,
        REQUIREMENTS_DATE,
        requirements if requirements is not None else [(WRITTEN_ASK, WRITTEN_QUOTE)],
    )


def _meeting_note(requirements: list[tuple[str, str]] | None = None) -> Document:
    return Document(
        MEETING_FILE,
        MEETING_NOTES,
        MEETING_DATE,
        requirements if requirements is not None else [(SPOKEN_ASK, SPOKEN_QUOTE)],
    )


def _runs_over(
    tmp_path: Path,
    name_hint: str,
    batches: list[list[Document]],
    answers: dict[str, Any],
    reject_matches: bool = False,
) -> list[RunOutcome]:
    """Run one project once per batch, and report what each run left behind."""
    outcomes: list[RunOutcome] = []
    with temporary_project_folder(name_hint) as (source_folder, source_folder_path):
        script: dict[str, Any] = {**answers, examine_marker(): no_findings_answer()}
        for batch in batches:
            for document in batch:
                script[extract_marker(document.source_file)] = (
                    several_requirements_answer(
                        document.requirements, document.document_type
                    )
                )
        script_path = tmp_path / "script.json"
        write_script(script_path, script)

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
                        "/projects",
                        json={"source_folder_path": source_folder_path},
                    ).json()["project_id"]
                    for batch in batches:
                        for document in batch:
                            write_document_stating(
                                source_folder,
                                document.source_file,
                                document.date,
                                [quote for _, quote in document.requirements],
                            )
                        outcomes.append(
                            _one_reviewed_run(
                                client, project_id, database_url, reject_matches
                            )
                        )
            finally:
                application.stop()
    return outcomes


def _one_reviewed_run(
    client: Any,
    project_id: str,
    database_url: str,
    reject_matches: bool,
) -> RunOutcome:
    run_id = client.post("/runs", json={"project_id": project_id}).json()["run_id"]
    at_review = wait_for_run_status(client, run_id, "needs review")
    for decision in at_review["decisions"]:
        rejected = reject_matches and decision["kind"] == POSSIBLE_MATCH_DECISION
        client.post(
            f"/runs/{run_id}/decisions",
            json={
                "decision_id": decision["decision_id"],
                "outcome": "rejected" if rejected else "approved",
            },
        ).raise_for_status()
    client.post(
        f"/runs/{run_id}/finish-review",
        json={"add_to_register": True},
    ).raise_for_status()
    wait_for_run_status(client, run_id, "done")
    return RunOutcome(
        decisions=at_review["decisions"],
        rows=stored_rows(database_url, project_id),
        export=client.get(f"/projects/{project_id}/register").json(),
    )


def _cell(row: StoredRow, cell_name: str) -> str:
    return row.cells[CELL_NAMES.index(cell_name)]


def _cited_files(row: StoredRow, cell_name: str) -> list[str]:
    return sorted(
        {citation[1] for citation in row.citations if citation[0] == cell_name}
    )


def _match_questions(outcome: RunOutcome) -> list[str]:
    return [
        decision["question"]
        for decision in outcome.decisions
        if decision["kind"] == POSSIBLE_MATCH_DECISION
    ]


@pytest.fixture(scope="module")
def one_ask_in_two_documents(tmp_path_factory: pytest.TempPathFactory) -> RunOutcome:
    """One batch: the client's written requirement and the note that raised it.

    Match is certain the two are one ask, so the second one creates no row of
    its own — the case the register used to answer with two rows, one of them
    claiming the ask was never written down.
    """
    return _runs_over(
        tmp_path_factory.mktemp("one-ask"),
        "one-ask",
        [[_requirements_document(), _meeting_note()]],
        {
            match_marker(): match_answer_within_batch(
                [(NEW_ROW, None, None), (EXISTING_ROW, None, 0)]
            )
        },
    )[0]


def test_one_ask_stated_in_two_documents_of_one_batch_becomes_one_row(
    one_ask_in_two_documents: RunOutcome,
) -> None:
    assert sorted(one_ask_in_two_documents.rows) == [1]


def test_the_batch_is_ordered_by_document_type_not_by_file_name(
    one_ask_in_two_documents: RunOutcome,
) -> None:
    """The ask is stated first in the meeting note, so it supplies the wording.

    `client-requirements-v1.md` sorts before `meeting-notes-10-mar.md`, so
    file-name order would hand the row the requirements document's words and
    make the requirements document's statement the one that creates the row.
    """
    row = one_ask_in_two_documents.rows[1]
    assert _cell(row, WHAT_WAS_ASKED) == SPOKEN_ASK
    assert sorted(_cited_files(row, WHAT_WAS_ASKED)) == sorted(
        [MEETING_FILE, REQUIREMENTS_FILE]
    )


def test_renaming_a_source_file_does_not_change_which_wording_the_row_keeps(
    tmp_path: Path,
    one_ask_in_two_documents: RunOutcome,
) -> None:
    """Nothing about a file's name is a fact about the evidence inside it."""
    renamed = _runs_over(
        tmp_path,
        "renamed",
        [
            [
                _requirements_document()._replace(source_file=RENAMED_REQUIREMENTS),
                _meeting_note()._replace(source_file=RENAMED_MEETING),
            ]
        ],
        {
            match_marker(): match_answer_within_batch(
                [(NEW_ROW, None, None), (EXISTING_ROW, None, 0)]
            )
        },
    )[0]

    assert _cell(renamed.rows[1], WHAT_WAS_ASKED) == _cell(
        one_ask_in_two_documents.rows[1], WHAT_WAS_ASKED
    )
    assert sorted(_cited_files(renamed.rows[1], WHAT_WAS_ASKED)) == sorted(
        [RENAMED_MEETING, RENAMED_REQUIREMENTS]
    )


def test_that_row_says_it_is_in_writing_and_cites_both_documents(
    one_ask_in_two_documents: RunOutcome,
) -> None:
    row = one_ask_in_two_documents.rows[1]
    assert _cell(row, IN_WRITING) == IN_WRITING_YES
    assert _cited_files(row, IN_WRITING) == [REQUIREMENTS_FILE]


def test_a_confident_batch_match_raises_no_decision(
    one_ask_in_two_documents: RunOutcome,
) -> None:
    """Nothing in the batch is committed, and the export gate covers the run.

    Asking separately about every obvious pair trains a reviewer to approve
    without reading, which costs more than it saves.
    """
    assert _match_questions(one_ask_in_two_documents) == []


def test_an_uncertain_batch_match_raises_a_decision_and_never_settles_itself(
    tmp_path: Path,
) -> None:
    outcome = _runs_over(
        tmp_path,
        "unsure-batch",
        [[_requirements_document(), _meeting_note()]],
        {
            match_marker(): match_answer_within_batch(
                [(NEW_ROW, None, None), (POSSIBLE_MATCH, None, 0)],
                questions=[None, UNSURE_BATCH_QUESTION],
            )
        },
    )[0]

    questions = _match_questions(outcome)
    assert len(questions) == 1
    assert questions[0] == UNSURE_BATCH_QUESTION
    assert SPOKEN_ASK in questions[0]
    assert WRITTEN_ASK in questions[0]
    # The person approved it, so the two became one row carrying both sources.
    assert sorted(outcome.rows) == [1]
    assert _cited_files(outcome.rows[1], WHAT_WAS_ASKED) == [
        REQUIREMENTS_FILE,
        MEETING_FILE,
    ]


def test_a_rejected_batch_merge_leaves_two_rows_each_with_its_own_evidence(
    tmp_path: Path,
) -> None:
    outcome = _runs_over(
        tmp_path,
        "rejected-batch",
        [[_requirements_document(), _meeting_note()]],
        {
            match_marker(): match_answer_within_batch(
                [(NEW_ROW, None, None), (POSSIBLE_MATCH, None, 0)]
            )
        },
        reject_matches=True,
    )[0]

    # The meeting note is read first, so it holds row 1 and the requirements
    # document — the later statement of the same ask — holds row 2.
    assert sorted(outcome.rows) == [1, 2]
    assert _cited_files(outcome.rows[1], WHAT_WAS_ASKED) == [MEETING_FILE]
    assert _cited_files(outcome.rows[2], WHAT_WAS_ASKED) == [REQUIREMENTS_FILE]
    assert _cell(outcome.rows[1], WHAT_WAS_ASKED) == SPOKEN_ASK


def test_a_requirement_matched_against_one_that_created_no_row_reaches_the_row_at_the_end_of_the_chain(
    tmp_path: Path,
) -> None:
    """Requirement 2 names requirement 1, which itself named requirement 0.

    Requirement 1 created no row, so naming it must reach the row at the end
    of the chain rather than fail the run over an answer that was correct.
    """
    outcome = _runs_over(
        tmp_path,
        "chained-batch",
        [
            [
                _requirements_document(),
                _meeting_note(
                    [(SPOKEN_ASK, SPOKEN_QUOTE), (RESTATED_ASK, RESTATED_QUOTE)]
                ),
            ]
        ],
        {
            match_marker(): match_answer_within_batch(
                [
                    (NEW_ROW, None, None),
                    (EXISTING_ROW, None, 0),
                    (EXISTING_ROW, None, 1),
                ]
            )
        },
    )[0]

    assert sorted(outcome.rows) == [1]
    assert len(
        [
            citation
            for citation in outcome.rows[1].citations
            if citation[0] == WHAT_WAS_ASKED
        ]
    ) == 3


def test_in_writing_says_the_requirements_document_does_not_mention_it(
    tmp_path: Path,
) -> None:
    outcome = _runs_over(
        tmp_path,
        "not-mentioned",
        [
            [
                _requirements_document(),
                _meeting_note([(SEARCH_ASK, SEARCH_QUOTE)]),
            ]
        ],
        {
            match_marker(): match_answer_within_batch(
                [(NEW_ROW, None, None), (NEW_ROW, None, None)]
            )
        },
    )[0]

    # The meeting note is read first, so its ask — the one the requirements
    # document never mentions — is row 1.
    assert _cell(outcome.rows[1], IN_WRITING) == NOT_MENTIONED
    # The absence carries its own evidence: the file that was read and is
    # silent, never a bare claim the row cannot support.
    assert _cited_files(outcome.rows[1], IN_WRITING) == [REQUIREMENTS_FILE]
    assert _cell(outcome.rows[2], IN_WRITING) == IN_WRITING_YES


def test_a_requirements_document_read_by_an_earlier_run_still_answers_written_down(
    tmp_path: Path,
) -> None:
    """A document is read once for a project's whole life, never again.

    A row born after that document was read must still record its silence, or
    every later row would keep saying no requirements document has been read.
    """
    first, second = _runs_over(
        tmp_path,
        "earlier-run",
        [[_requirements_document()], [_meeting_note([(SEARCH_ASK, SEARCH_QUOTE)])]],
        {match_marker(): match_answer_within_batch([(NEW_ROW, None, None)])},
    )

    assert _cell(first.rows[1], IN_WRITING) == IN_WRITING_YES
    assert _cell(second.rows[2], IN_WRITING) == NOT_MENTIONED
    assert _cited_files(second.rows[2], IN_WRITING) == [REQUIREMENTS_FILE]


def test_two_documents_in_separate_runs_still_reach_the_committed_row_gate(
    tmp_path: Path,
) -> None:
    """The path that already worked must not regress as the batch path arrives.

    A committed row is approved and in the register, so this batch's evidence
    reaching it is still the Delivery Owner's to decide.
    """
    first, second = _runs_over(
        tmp_path,
        "separate-runs",
        [[_meeting_note()], [_requirements_document()]],
        {
            # The batch-specific marker comes first: the second run's Match
            # call is the only prompt naming the requirements document.
            match_marker_for_batch_with(REQUIREMENTS_FILE): match_answer_within_batch(
                [(EXISTING_ROW, 1, None)],
                questions=[COMMITTED_ROW_QUESTION],
            ),
            match_marker(): match_answer_within_batch([(NEW_ROW, None, None)]),
        },
    )

    assert _cell(first.rows[1], IN_WRITING) == IN_WRITING_NOT_KNOWN_YET
    questions = _match_questions(second)
    assert len(questions) == 1
    assert questions[0] == COMMITTED_ROW_QUESTION
    assert SPOKEN_ASK in questions[0]
    # The person approved it, so one row carries both documents.
    assert sorted(second.rows) == [1]
    assert _cited_files(second.rows[1], WHAT_WAS_ASKED) == [
        REQUIREMENTS_FILE,
        MEETING_FILE,
    ]
