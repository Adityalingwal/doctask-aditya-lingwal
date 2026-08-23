from __future__ import annotations

from pathlib import Path
from typing import Any, NamedTuple

from app.register.cells import (
    CELL_NAMES,
    IN_WRITING,
    IN_WRITING_YES,
    NOT_MENTIONED,
    WHAT_TESTING_FOUND,
    absence_statement_for,
)
from app.extract.answer import (
    CLIENT_REQUIREMENTS_DOCUMENT,
    MEETING_NOTES,
)
from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    feedback_extraction_answer,
    match_answer,
    match_answer_existing_row,
    match_marker_for_batch_with,
    no_findings_answer,
    observation_answer_of,
    observation_marker,
    several_requirements_answer,
    write_document_stating,
)
from tests.examine.answers import examine_answer, one_finding
from tests.register.stored_register import StoredRow, audit_of_row, stored_rows
from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)


MEETING_NOTE = "meeting-notes-02-jul.md"
REQUIREMENTS_V1 = "client-requirements-v1.md"
REQUIREMENTS_V2 = "client-requirements-v2.md"
TESTING_FEEDBACK = "testing-feedback-12-aug.md"
TESTING_FEEDBACK_2 = "testing-feedback-19-aug.md"
DOCUMENT_DATE = "2 July 2026"

SPOKEN_ASK = "a voice agent that answers support-line calls"
SPOKEN_QUOTE = "The client asked for a voice agent on the support line."
SECOND_ASK = "a weekly analytics report of every call"
SECOND_QUOTE = "The client asked for a weekly analytics report."
THIRD_ASK = "support in Hindi as well as English"
THIRD_QUOTE = "The client asked for support in Hindi as well as English."
OBSERVATION_ABOUT_NO_ROW = "the marketing site loads slowly on mobile"
OBSERVATION_QUOTE = "The marketing site loads slowly on a phone."
VERDICT_ON_THE_SPOKEN_ASK = "the voice agent answers every test call"
VERDICT_QUOTE = "The voice agent answered every call we placed."

CELL_INDEX = {name: index for index, name in enumerate(CELL_NAMES)}
# Matches the Examine prompt only when the silent row is shown as Commit
# will leave it; an Examine that still shows `Not known yet` never hits it.
EXAMINE_SEES_NOT_MENTIONED_MARKER = f'"{WHAT_TESTING_FOUND}": "{NOT_MENTIONED}"'


class Driven(NamedTuple):
    """One project's committed register after each batch, and its audit trail."""

    after_each_batch: list[dict[int, StoredRow]]
    audit_of_first_row: list[tuple[Any, ...]]
    register: dict[str, Any]
    markdown: str


def test_absence_writes_not_mentioned_with_evidence_and_history_and_fingerprint(
    tmp_path: Path,
) -> None:
    """A requirements document that was read and is silent is an answer, not a gap.

    The cell says what is known, the citation names the file that was read and
    says plainly that it does not mention the ask, the history records the
    move, and the fingerprint moves with the cell — a changed cell that left
    the fingerprint standing would be the register lying about itself.
    """
    driven = _drive(
        tmp_path,
        "absence-evidence",
        [[MEETING_NOTE], [REQUIREMENTS_V1]],
        {REQUIREMENTS_V1: SECOND_ASK},
    )
    before, after = driven.after_each_batch

    assert _cell(after[1], IN_WRITING) == NOT_MENTIONED
    assert (IN_WRITING, REQUIREMENTS_V1, None, None, absence_statement_for(
        REQUIREMENTS_V1
    )) in after[1].citations
    assert after[1].fingerprint != before[1].fingerprint
    assert (
        IN_WRITING,
        "cell change",
        driven.after_each_batch[0][1].cells[CELL_INDEX[IN_WRITING]],
        NOT_MENTIONED,
    ) in driven.audit_of_first_row


def test_a_row_created_after_the_requirements_document_gets_not_mentioned_at_commit(
    tmp_path: Path,
) -> None:
    """A row born after the document was read still records that document's silence.

    Nothing re-reads the requirements document — it is read once for a
    project's whole life — so a row proposed later would otherwise keep saying
    no requirements document had been read at all.
    """
    driven = _drive(
        tmp_path,
        "born-later",
        [[REQUIREMENTS_V1], [MEETING_NOTE]],
        {REQUIREMENTS_V1: SECOND_ASK},
    )
    latest = driven.after_each_batch[-1]

    # Row 1 is the requirements document's own ask; row 2 is the meeting note's,
    # proposed a run after the only requirements document was read.
    assert _cell(latest[2], IN_WRITING) == NOT_MENTIONED
    assert absence_statement_for(REQUIREMENTS_V1) in driven.markdown
    assert "Not found in" not in driven.markdown
    assert "Not found in" not in str(driven.register)


def test_absence_never_overwrites_yes_or_a_testing_verdict(tmp_path: Path) -> None:
    """A document's silence answers an open cell and never argues with an answer.

    Two requirements documents, and the row is only ever moved by the one that
    mentions it. A second silent document adds its own evidence behind a cell
    that already says `Not mentioned`, which changes nothing the cell claims —
    so it writes no history entry and moves no fingerprint.
    """
    mentioned_first = _drive(
        tmp_path,
        "mentioned-first",
        [[MEETING_NOTE], [REQUIREMENTS_V1], [REQUIREMENTS_V2]],
        {REQUIREMENTS_V1: SPOKEN_ASK, REQUIREMENTS_V2: THIRD_ASK},
    )
    silent_twice = _drive(
        tmp_path,
        "silent-twice",
        [[MEETING_NOTE], [REQUIREMENTS_V1], [REQUIREMENTS_V2]],
        {REQUIREMENTS_V1: SECOND_ASK, REQUIREMENTS_V2: THIRD_ASK},
    )

    _asked, written, still_written = mentioned_first.after_each_batch
    assert _cell(written[1], IN_WRITING) == IN_WRITING_YES
    assert _cell(still_written[1], IN_WRITING) == IN_WRITING_YES
    # The silent second document supports nothing the cell says, so it is not
    # cited behind it at all.
    assert _files_cited(still_written[1], IN_WRITING) == {REQUIREMENTS_V1}

    # The testing half of the promise: a verdict already on the row, then a
    # testing report silent about it — the verdict stands and the silent
    # report is not cited behind it.
    tested_then_silent = _drive(
        tmp_path,
        "tested-then-silent",
        [[MEETING_NOTE], [TESTING_FEEDBACK_2], [TESTING_FEEDBACK]],
        {TESTING_FEEDBACK_2: SPOKEN_ASK},
    )
    _asked, tested, still_tested = tested_then_silent.after_each_batch
    assert _cell(tested[1], WHAT_TESTING_FOUND) == VERDICT_ON_THE_SPOKEN_ASK
    assert _cell(still_tested[1], WHAT_TESTING_FOUND) == VERDICT_ON_THE_SPOKEN_ASK
    assert _files_cited(still_tested[1], WHAT_TESTING_FOUND) == {TESTING_FEEDBACK_2}

    _before, silent_once, silent_again = silent_twice.after_each_batch
    assert _cell(silent_again[1], IN_WRITING) == NOT_MENTIONED
    assert _files_cited(silent_again[1], IN_WRITING) == {
        REQUIREMENTS_V1,
        REQUIREMENTS_V2,
    }
    assert silent_again[1].fingerprint == silent_once[1].fingerprint
    assert [
        entry
        for entry in silent_twice.audit_of_first_row
        if entry[0] == IN_WRITING and entry[3] == NOT_MENTIONED
    ] == [(IN_WRITING, "cell change", "Not known yet", NOT_MENTIONED)]


def test_a_later_mention_drops_the_absence_citation(tmp_path: Path) -> None:
    """A document that does mention the ask replaces the silence and its evidence.

    The cell holds one claim, so the file that was read and said nothing no
    longer supports what the cell now says, and goes with the old value.
    """
    driven = _drive(
        tmp_path,
        "silent-then-written",
        [[MEETING_NOTE], [REQUIREMENTS_V1], [REQUIREMENTS_V2]],
        {REQUIREMENTS_V1: SECOND_ASK, REQUIREMENTS_V2: SPOKEN_ASK},
    )
    _asked, silent, written = driven.after_each_batch

    assert _cell(silent[1], IN_WRITING) == NOT_MENTIONED
    assert _files_cited(silent[1], IN_WRITING) == {REQUIREMENTS_V1}
    assert _cell(written[1], IN_WRITING) == IN_WRITING_YES
    assert _files_cited(written[1], IN_WRITING) == {REQUIREMENTS_V2}


def test_a_silent_testing_feedback_document_still_reaches_review_and_commit(
    tmp_path: Path,
) -> None:
    """Silence about a row is a change, and a person approves it like any other.

    The one thing this testing report says is about no row the register
    traces. Ending the run there would leave every row saying no testing
    outcome had been read, when one had.
    """
    driven = _drive(
        tmp_path,
        "silent-testing",
        [[MEETING_NOTE], [TESTING_FEEDBACK]],
        {},
        decisions_at_review=[],
    )
    _asked, tested = driven.after_each_batch

    assert _cell(tested[1], WHAT_TESTING_FOUND) == NOT_MENTIONED
    assert (
        WHAT_TESTING_FOUND,
        TESTING_FEEDBACK,
        None,
        None,
        absence_statement_for(TESTING_FEEDBACK),
    ) in tested[1].citations


def test_examine_sees_a_silent_documents_not_mentioned_before_commit(
    tmp_path: Path,
) -> None:
    """A rule about silence must see the silence before the person is asked.

    `Not mentioned` is written at Commit, after Review — but the rule runs
    before it. Examine therefore has to be shown what Commit will write, the
    way it is shown pending moves, or the testing-outcome rule never sees a
    silent testing report and the finding it exists for is never raised.
    """
    driven = _drive(
        tmp_path,
        "silent-seen-by-examine",
        [[MEETING_NOTE], [TESTING_FEEDBACK]],
        {},
        decisions_per_batch=[[], ["finding"]],
        answers_tried_first={
            EXAMINE_SEES_NOT_MENTIONED_MARKER: examine_answer(
                [one_finding(rule_id="R4", row_number=1)]
            )
        },
    )
    _asked, tested = driven.after_each_batch
    assert _cell(tested[1], WHAT_TESTING_FOUND) == NOT_MENTIONED
    assert [finding["rule_id"] for finding in driven.register["rows"][0]["findings"]] == ["R4"]


def _cell(row: StoredRow, cell_name: str) -> str:
    return row.cells[CELL_INDEX[cell_name]]


def _files_cited(row: StoredRow, cell_name: str) -> set[str]:
    return {
        citation[1] for citation in row.citations if citation[0] == cell_name
    }


def _drive(
    tmp_path: Path,
    name_hint: str,
    batches: list[list[str]],
    requirements_documents_state: dict[str, str],
    decisions_at_review: list[str] | None = None,
    decisions_per_batch: list[list[str]] | None = None,
    answers_tried_first: dict[str, Any] | None = None,
) -> Driven:
    """Run one project batch by batch, approving everything each time.

    `requirements_documents_state` says which ask each requirements document
    states: the spoken ask, which makes it mention row 1, or another ask, which
    makes it silent about row 1 and propose a row of its own.
    """
    script_path = tmp_path / "script.json"
    # A script answers the first marker that matches, so an answer that must
    # win over the general Examine answer is written before it.
    write_script(
        script_path,
        {**(answers_tried_first or {}), **_answers(requirements_documents_state)},
    )
    snapshots: list[dict[int, StoredRow]] = []

    with temporary_project_folder(name_hint) as (folder, folder_path):
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
                        "/projects", json={"source_folder_path": folder_path}
                    ).json()["project_id"]
                    for batch_index, batch in enumerate(batches):
                        for source_file in batch:
                            write_document_stating(
                                folder,
                                source_file,
                                DOCUMENT_DATE,
                                [_quote_in(source_file, requirements_documents_state)],
                            )
                        run_id = client.post(
                            "/runs", json={"project_id": project_id}
                        ).json()["run_id"]
                        waiting = wait_for_run_status(client, run_id, "needs review")
                        expected_decisions = (
                            decisions_per_batch[batch_index]
                            if decisions_per_batch is not None
                            else decisions_at_review
                        )
                        if expected_decisions is not None:
                            assert [
                                decision["kind"] for decision in waiting["decisions"]
                            ] == expected_decisions
                        approve_every_decision_and_finish_review(client, run_id)
                        wait_for_run_status(client, run_id, "done")
                        snapshots.append(stored_rows(database_url, project_id))
                    register = client.get(
                        f"/projects/{project_id}/register"
                    ).json()
                    markdown = client.get(
                        f"/projects/{project_id}/register",
                        params={"format": "markdown"},
                    ).text
                audit = audit_of_row(database_url, project_id, 1)
            finally:
                application.stop()

    return Driven(
        after_each_batch=snapshots,
        audit_of_first_row=audit,
        register=register,
        markdown=markdown,
    )


def _quote_in(source_file: str, states: dict[str, str]) -> str:
    return _QUOTE_OF_ASK[_ask_in(source_file, states)]


def _ask_in(source_file: str, states: dict[str, str]) -> str:
    if source_file == MEETING_NOTE:
        return SPOKEN_ASK
    if source_file == TESTING_FEEDBACK:
        return OBSERVATION_ABOUT_NO_ROW
    if source_file == TESTING_FEEDBACK_2:
        return VERDICT_ON_THE_SPOKEN_ASK
    return states[source_file]


_QUOTE_OF_ASK = {
    SPOKEN_ASK: SPOKEN_QUOTE,
    SECOND_ASK: SECOND_QUOTE,
    THIRD_ASK: THIRD_QUOTE,
    OBSERVATION_ABOUT_NO_ROW: OBSERVATION_QUOTE,
    VERDICT_ON_THE_SPOKEN_ASK: VERDICT_QUOTE,
}


def _answers(states: dict[str, str]) -> dict[str, Any]:
    """One scripted answer per document, plus Match, observations and Examine.

    A requirements document that states the spoken ask is answered against the
    committed row; one that states its own ask proposes a row of its own.
    """
    answers: dict[str, Any] = {
        extract_marker(MEETING_NOTE): several_requirements_answer(
            [(SPOKEN_ASK, SPOKEN_QUOTE)], MEETING_NOTES
        ),
        extract_marker(TESTING_FEEDBACK): feedback_extraction_answer(
            [(OBSERVATION_ABOUT_NO_ROW, "Defect", OBSERVATION_QUOTE)]
        ),
    }
    for source_file, ask in states.items():
        if source_file == TESTING_FEEDBACK_2:
            answers[extract_marker(source_file)] = feedback_extraction_answer(
                [(VERDICT_ON_THE_SPOKEN_ASK, "Passed", VERDICT_QUOTE)]
            )
            # Answered before the general observation answer below, because
            # the scripted model takes the first marker that matches.
            answers[match_marker_for_batch_with(source_file)] = observation_answer_of([1])
            continue
        answers[extract_marker(source_file)] = several_requirements_answer(
            [(ask, _QUOTE_OF_ASK[ask])], CLIENT_REQUIREMENTS_DOCUMENT
        )
        answers[match_marker_for_batch_with(source_file)] = (
            match_answer_existing_row(1) if ask == SPOKEN_ASK else match_answer(1)
        )
    answers[match_marker_for_batch_with(MEETING_NOTE)] = match_answer(1)
    answers[observation_marker()] = observation_answer_of([None])
    answers[examine_marker()] = no_findings_answer()
    return answers
