from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx

from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    temporary_database,
    wait_for_run_status,
    write_script,
)
from tests.interfaces.mcp_client import call_tool, tool_names
from tests.documents.register_documents import (
    dated_extraction_answer,
    examine_marker,
    extract_marker,
    extraction_answer,
    match_answer,
    match_answer_of,
    match_marker,
    match_marker_against_an_empty_register,
    no_findings_answer,
    write_client_requirements,
    write_meeting_note,
)
from tests.register.stored_register import audit_of_row, stored_rows

from app.extract.answer import (
    CLIENT_REQUIREMENTS_DOCUMENT,
    MEETING_NOTES,
    RELATED_ADDITIONAL_DOCUMENT,
)

REQUIREMENTS_FILE = "client-requirements.md"
MEETING_FILE = "meeting-notes.md"
KEPT = "an email notification to the operations team on intake form submit"
DROPPED = "a records list page showing every intake record"
DISCUSSED = "a search over old intake records"
FIRST_VERSION_DATE = "12 March 2026"
SECOND_VERSION_DATE = "26 March 2026"
# Not 10 March: the Extract instructions carry that date in their example, so
# it is in every extraction prompt and cannot tell one document from another.
FIRST_MEETING_DATE = "11 March 2026"
SECOND_MEETING_DATE = "24 March 2026"
THIRD_MEETING_DATE = "30 March 2026"
KEPT_ROW = 1
DROPPED_ROW = 2
DISCUSSED_ROW = 3
STATUS_CELL = 3
DATE_MARKER = "**Date:** {date}"
WITHDRAWN = "Withdrawn"


def _meeting_note_asking_for(
    folder: Path,
    date: str,
    requirements: list[str],
) -> list[str]:
    """The meeting note re-issued: its own date, and what it still asks for."""
    quotes = [f"The client asked for {requirement}." for requirement in requirements]
    (folder / MEETING_FILE).write_text(
        "# Intake portal meeting notes\n\n"
        f"{DATE_MARKER.format(date=date)}\n\n"
        "## Discussion\n\n" + "\n\n".join(quotes) + "\n",
        encoding="utf-8",
    )
    return quotes


def _write_second_meeting_note(folder: Path) -> str:
    """The same meeting note, written again, still asking for the same thing."""
    quote = f"The client asked once more for {DISCUSSED}."
    (folder / MEETING_FILE).write_text(
        "# Intake portal meeting notes\n\n"
        f"{DATE_MARKER.format(date=SECOND_MEETING_DATE)}\n\n"
        "## Discussion\n\n"
        f"{quote}\n",
        encoding="utf-8",
    )
    return quote


def _requirements_document_without_the_dropped_row(source_folder: Path) -> None:
    """The same requirements document, re-issued with one requirement removed."""
    write_client_requirements(
        source_folder,
        REQUIREMENTS_FILE,
        [KEPT],
        SECOND_VERSION_DATE,
    )


@contextmanager
def _register_of_three_rows(
    tmp_path: Path,
    project_name: str,
    second_run_answers: dict[str, dict],
) -> Iterator[tuple[ApplicationProcess, str, str, Path]]:
    """Three committed rows: two from the requirements document, one from a meeting.

    The requirements document's re-issued version is always scripted, because
    every test below re-reads it; what else the second run is told is passed in.
    """
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    kept_quote, dropped_quote = write_client_requirements(
        source_folder,
        REQUIREMENTS_FILE,
        [KEPT, DROPPED],
        FIRST_VERSION_DATE,
    )
    discussed_quote = write_meeting_note(source_folder, MEETING_FILE, DISCUSSED)

    script_path = tmp_path / "script.json"
    write_script(
        script_path,
        {
            # Ordered narrowest first: the scripted model answers with the
            # first marker its prompt contains, and a second run's prompts
            # still carry the broader markers the first run matched on.
            match_marker_against_an_empty_register(): match_answer(3),
            DATE_MARKER.format(date=SECOND_VERSION_DATE): dated_extraction_answer(
                [(KEPT, kept_quote)],
                CLIENT_REQUIREMENTS_DOCUMENT,
                SECOND_VERSION_DATE,
            ),
            **second_run_answers,
            extract_marker(REQUIREMENTS_FILE): dated_extraction_answer(
                [(KEPT, kept_quote), (DROPPED, dropped_quote)],
                CLIENT_REQUIREMENTS_DOCUMENT,
                FIRST_VERSION_DATE,
            ),
            extract_marker(MEETING_FILE): extraction_answer(
                DISCUSSED, discussed_quote
            ),
            examine_marker(): no_findings_answer(),
        },
    )

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
                    json={
                        "name": project_name,
                        "source_folder_path": str(source_folder),
                    },
                ).json()["project_id"]
                first_run = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                wait_for_run_status(client, first_run, "waiting for review")
                approve_every_decision_and_finish_review(client, first_run)
                wait_for_run_status(client, first_run, "done")
            yield application, database_url, project_id, source_folder
        finally:
            application.stop()


def _run_to_review(client: httpx.Client, project_id: str) -> tuple[str, dict]:
    run_id = client.post("/runs", json={"project_id": project_id}).json()["run_id"]
    return run_id, wait_for_run_status(client, run_id, "waiting for review")


def _withdrawals(at_review: dict) -> list[dict]:
    return [
        decision
        for decision in at_review["decisions"]
        if decision["kind"] == "withdrawal"
    ]


def test_only_the_document_that_supplied_a_row_can_withdraw_it(
    tmp_path: Path,
) -> None:
    with _register_of_three_rows(
        tmp_path,
        "Silent second document",
        {
            DATE_MARKER.format(date=SECOND_MEETING_DATE): dated_extraction_answer(
                [(DISCUSSED, f"The client asked once more for {DISCUSSED}.")],
                MEETING_NOTES,
                SECOND_MEETING_DATE,
            ),
            match_marker(): match_answer_of([KEPT_ROW, DISCUSSED_ROW]),
        },
    ) as (application, _, project_id, source_folder):
        _requirements_document_without_the_dropped_row(source_folder)
        _write_second_meeting_note(source_folder)
        with application.client() as client:
            _, at_review = _run_to_review(client, project_id)

    raised = _withdrawals(at_review)
    # The meeting note changed too and never mentions the dropped row. Its
    # silence proposes nothing, and it withdraws nothing of its own either,
    # because it still asks for the row it supplied.
    assert len(raised) == 1
    assert f"#{DROPPED_ROW}" in raised[0]["question"]
    assert REQUIREMENTS_FILE in raised[0]["question"]
    assert MEETING_FILE not in raised[0]["question"]


def test_an_approved_withdrawal_marks_the_row_withdrawn_and_keeps_its_history(
    tmp_path: Path,
) -> None:
    with _register_of_three_rows(
        tmp_path,
        "Approved withdrawal",
        {match_marker(): match_answer_of([KEPT_ROW])},
    ) as (application, database_url, project_id, source_folder):
        _requirements_document_without_the_dropped_row(source_folder)
        with application.client() as client:
            before = stored_rows(database_url, project_id)
            second_run, at_review = _run_to_review(client, project_id)
            assert len(_withdrawals(at_review)) == 1
            approve_every_decision_and_finish_review(client, second_run)
            wait_for_run_status(client, second_run, "done")
            after = stored_rows(database_url, project_id)
            export = client.get(f"/runs/{second_run}/export").json()
            markdown = client.get(
                f"/runs/{second_run}/export", params={"format": "markdown"}
            ).text
            audit = audit_of_row(database_url, project_id, DROPPED_ROW)

    withdrawn = after[DROPPED_ROW]
    asked_before, _, _, status_before, _, first_seen_before, _ = before[
        DROPPED_ROW
    ].cells
    asked_after, _, _, status_after, _, first_seen_after, moved_after = withdrawn.cells
    assert status_before != WITHDRAWN
    assert status_after == WITHDRAWN
    assert asked_after == asked_before
    assert first_seen_after == first_seen_before
    assert moved_after == SECOND_VERSION_DATE
    assert withdrawn.fingerprint != before[DROPPED_ROW].fingerprint
    # Nothing the row already carried was taken away.
    assert set(before[DROPPED_ROW].citations) <= set(withdrawn.citations)
    absence = [citation for citation in withdrawn.citations if citation[4] is not None]
    assert len(absence) == 1
    assert absence[0][0] == "status"
    assert absence[0][1] == REQUIREMENTS_FILE
    assert absence[0][2] is None and absence[0][3] is None
    assert REQUIREMENTS_FILE in absence[0][4]
    assert after[DISCUSSED_ROW] == before[DISCUSSED_ROW]
    assert ("status", "cell change", status_before, WITHDRAWN) in audit

    exported = {row["row_number"]: row for row in export["rows"]}
    assert exported[DROPPED_ROW]["cells"]["status"] == WITHDRAWN
    assert WITHDRAWN in markdown


def test_a_rejected_withdrawal_leaves_the_row_byte_identical(
    tmp_path: Path,
) -> None:
    with _register_of_three_rows(
        tmp_path,
        "Rejected withdrawal",
        {match_marker(): match_answer_of([KEPT_ROW])},
    ) as (application, database_url, project_id, source_folder):
        _requirements_document_without_the_dropped_row(source_folder)
        with application.client() as client:
            before = stored_rows(database_url, project_id)
            second_run, at_review = _run_to_review(client, project_id)
            for decision in at_review["decisions"]:
                client.post(
                    f"/runs/{second_run}/decisions",
                    json={
                        "decision_id": decision["decision_id"],
                        "outcome": (
                            "rejected"
                            if decision["kind"] == "withdrawal"
                            else "approved"
                        ),
                    },
                ).raise_for_status()
            client.post(f"/runs/{second_run}/finish-review").raise_for_status()
            wait_for_run_status(client, second_run, "done")
            after = stored_rows(database_url, project_id)
            answered = client.get(f"/runs/{second_run}").json()["decisions"]

    assert after[DROPPED_ROW] == before[DROPPED_ROW]
    assert [
        decision["outcome"] for decision in _withdrawals({"decisions": answered})
    ] == ["rejected"]


def test_a_withdrawal_is_answered_through_the_same_seven_mcp_tools(
    tmp_path: Path,
) -> None:
    with _register_of_three_rows(
        tmp_path,
        "Withdrawal driven by a machine",
        {match_marker(): match_answer_of([KEPT_ROW])},
    ) as (application, database_url, project_id, source_folder):
        _requirements_document_without_the_dropped_row(source_folder)
        base_url = application.base_url
        with application.client() as client:
            second_run, at_review = _run_to_review(client, project_id)
        tools = tool_names(base_url)
        for decision in at_review["decisions"]:
            call_tool(
                base_url,
                "submit_decision",
                {
                    "run_id": second_run,
                    "decision_id": decision["decision_id"],
                    "outcome": "approved",
                },
            )
        call_tool(base_url, "finish_review", {"run_id": second_run})
        with application.client() as client:
            wait_for_run_status(client, second_run, "done")
        exported = call_tool(base_url, "get_export", {"run_id": second_run})
        after = stored_rows(database_url, project_id)

    # The tool list is unaffected by withdrawal: a withdrawal is another
    # decision the existing tools carry, not a tool of its own. `list_runs`
    # (D15) brings the count to seven for a different reason entirely.
    assert len(tools) == 7
    assert after[DROPPED_ROW].cells[STATUS_CELL] == WITHDRAWN
    assert any(
        row["cells"]["status"] == WITHDRAWN for row in exported.payload["rows"]
    )


def test_the_absence_is_cited_to_the_document_that_actually_stopped_asking(
    tmp_path: Path,
) -> None:
    # Row 2 ends up cited to both documents. Only the meeting note drops it, so
    # the absence must be written against the meeting note — not against the
    # requirements document, which is merely the first of the two by name.
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    kept_quote, dropped_quote = write_client_requirements(
        source_folder, REQUIREMENTS_FILE, [KEPT, DROPPED], FIRST_VERSION_DATE
    )
    first_meeting_quotes = _meeting_note_asking_for(
        source_folder, FIRST_MEETING_DATE, [DISCUSSED]
    )
    second_meeting_quotes = [
        f"The client asked for {requirement}." for requirement in (DISCUSSED, DROPPED)
    ]
    third_meeting_quotes = [f"The client asked for {DISCUSSED}."]

    script_path = tmp_path / "script.json"
    write_script(
        script_path,
        {
            match_marker_against_an_empty_register(): match_answer(3),
            DATE_MARKER.format(date=THIRD_MEETING_DATE): dated_extraction_answer(
                [(DISCUSSED, third_meeting_quotes[0])],
                MEETING_NOTES,
                THIRD_MEETING_DATE,
            ),
            DATE_MARKER.format(date=SECOND_MEETING_DATE): dated_extraction_answer(
                [
                    (DISCUSSED, second_meeting_quotes[0]),
                    (DROPPED, second_meeting_quotes[1]),
                ],
                MEETING_NOTES,
                SECOND_MEETING_DATE,
            ),
            DATE_MARKER.format(date=FIRST_MEETING_DATE): dated_extraction_answer(
                [(DISCUSSED, first_meeting_quotes[0])],
                MEETING_NOTES,
                FIRST_MEETING_DATE,
            ),
            # Re-read and judged a different type this time, so it reaches
            # neither Match nor a withdrawal — and still carries row 2's
            # earlier citation.
            DATE_MARKER.format(date=SECOND_VERSION_DATE): dated_extraction_answer(
                [], RELATED_ADDITIONAL_DOCUMENT, SECOND_VERSION_DATE
            ),
            DATE_MARKER.format(date=FIRST_VERSION_DATE): dated_extraction_answer(
                [(KEPT, kept_quote), (DROPPED, dropped_quote)],
                CLIENT_REQUIREMENTS_DOCUMENT,
                FIRST_VERSION_DATE,
            ),
            # Only the second meeting note's Match call carries this quote.
            second_meeting_quotes[1]: match_answer_of([DISCUSSED_ROW, DROPPED_ROW]),
            match_marker(): match_answer_of([DISCUSSED_ROW]),
            examine_marker(): no_findings_answer(),
        },
    )

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
                    json={
                        "name": "Two documents, one dropped it",
                        "source_folder_path": str(source_folder),
                    },
                ).json()["project_id"]
                first_run = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                wait_for_run_status(client, first_run, "waiting for review")
                approve_every_decision_and_finish_review(client, first_run)
                wait_for_run_status(client, first_run, "done")

                # The meeting note asks for the dropped requirement too, and
                # approving that match puts its citation on row 2.
                _meeting_note_asking_for(
                    source_folder, SECOND_MEETING_DATE, [DISCUSSED, DROPPED]
                )
                second_run, _ = _run_to_review(client, project_id)
                approve_every_decision_and_finish_review(client, second_run)
                wait_for_run_status(client, second_run, "done")

                write_client_requirements(
                    source_folder, REQUIREMENTS_FILE, [KEPT, DROPPED], SECOND_VERSION_DATE
                )
                _meeting_note_asking_for(
                    source_folder, THIRD_MEETING_DATE, [DISCUSSED]
                )
                third_run, at_review = _run_to_review(client, project_id)
                raised = _withdrawals(at_review)
                approve_every_decision_and_finish_review(client, third_run)
                wait_for_run_status(client, third_run, "done")
                after = stored_rows(database_url, project_id)
        finally:
            application.stop()

    assert len(raised) == 1
    assert MEETING_FILE in raised[0]["question"]

    withdrawn = after[DROPPED_ROW]
    cited_files = {citation[1] for citation in withdrawn.citations}
    assert {REQUIREMENTS_FILE, MEETING_FILE} <= cited_files
    absence = [citation for citation in withdrawn.citations if citation[4] is not None]
    assert len(absence) == 1
    # The question named the meeting note; the record must name it too.
    assert absence[0][1] == MEETING_FILE
    assert MEETING_FILE in absence[0][4]
    assert withdrawn.cells[STATUS_CELL] == WITHDRAWN
    assert withdrawn.cells[6] == THIRD_MEETING_DATE
