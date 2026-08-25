from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, NamedTuple

import httpx

from app.extract.answer import CLIENT_REQUIREMENTS_DOCUMENT, MEETING_NOTES
from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    feedback_extraction_answer,
    handover_answer,
    match_answer,
    match_answer_within_batch,
    match_marker,
    match_marker_against_an_empty_register,
    no_findings_answer,
    observation_answer_of,
    observation_marker,
    several_requirements_answer,
    write_document_stating,
)
from tests.interfaces.mcp_client import call_tool
from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)


MEETING_FILE = "meeting-notes-02-jul.md"
REQUIREMENTS_FILE = "client-requirements-v1.md"
HANDOVER_FILE = "handover-summary.md"
TESTING_FILE = "testing-feedback-12-aug.md"

FIRST_QUOTE = "The client asked for a support line that answers calls."
SECOND_QUOTE = "The client also asked for a chat widget on the website."
WRITTEN_QUOTE = "The support line must answer calls, not queue them."
HANDOVER_QUOTE = "The support line was built and handed over."
TESTING_QUOTE = "The support line could not be reached during testing."

FIRST_ASK = "a support line that answers calls rather than queueing them"
SECOND_ASK = "a chat widget on the website"
WRITTEN_ASK = "the support line answers calls rather than queueing them"
HANDED_OVER = "the support line was built"
TESTING_VERDICT = "the support line could not be reached"

SILENT_ABOUT_ROW_2 = (
    f"Row 2 · Written down → Not mentioned — {REQUIREMENTS_FILE} was read and "
    "does not mention this ask."
)


class Helpline(NamedTuple):
    client: httpx.Client
    project_id: str
    folder: Path
    application: ApplicationProcess


def _script() -> dict[str, Any]:
    """One script covering all four documents, whichever run reads them."""
    return {
        extract_marker(MEETING_FILE): several_requirements_answer(
            [(FIRST_ASK, FIRST_QUOTE), (SECOND_ASK, SECOND_QUOTE)], MEETING_NOTES
        ),
        extract_marker(REQUIREMENTS_FILE): several_requirements_answer(
            [(WRITTEN_ASK, WRITTEN_QUOTE)], CLIENT_REQUIREMENTS_DOCUMENT
        ),
        extract_marker(HANDOVER_FILE): handover_answer([(HANDED_OVER, HANDOVER_QUOTE)]),
        extract_marker(TESTING_FILE): feedback_extraction_answer(
            [(TESTING_VERDICT, "Not found", TESTING_QUOTE)]
        ),
        match_marker_against_an_empty_register(): match_answer(2),
        # The written statement may be the first ask, and Match says so rather
        # than deciding for the person: the run stops and asks.
        match_marker(): match_answer_within_batch([("possible match", 1, None)]),
        observation_marker(): observation_answer_of([1]),
        examine_marker(): no_findings_answer(),
    }


@contextmanager
def _helpline(tmp_path: Path) -> Iterator[Helpline]:
    """One project whose folder starts with the meeting note alone."""
    with temporary_project_folder("add-preview") as (folder, source_folder_path):
        write_document_stating(
            folder, MEETING_FILE, "2 July 2026", [FIRST_QUOTE, SECOND_QUOTE]
        )
        script_path = tmp_path / "script.json"
        write_script(script_path, _script())
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
                    yield Helpline(client, project_id, folder, application)
            finally:
                application.stop()


def _start(client: httpx.Client, project_id: str) -> tuple[str, dict[str, Any]]:
    run_id = client.post("/runs", json={"project_id": project_id}).json()["run_id"]
    return run_id, wait_for_run_status(client, run_id, "needs review")


def _add(client: httpx.Client, run_id: str) -> None:
    approve_every_decision(client, run_id)
    client.post(
        f"/runs/{run_id}/finish-review", json={"add_to_register": True}
    ).raise_for_status()
    wait_for_run_status(client, run_id, "done")


def _answer(client: httpx.Client, run_id: str, kind: str, outcome: str) -> None:
    for decision in client.get(f"/runs/{run_id}").json()["decisions"]:
        if decision["kind"] != kind or decision["outcome"] is not None:
            continue
        client.post(
            f"/runs/{run_id}/decisions",
            json={"decision_id": decision["decision_id"], "outcome": outcome},
        ).raise_for_status()


def _lines(payload: dict[str, Any]) -> list[str]:
    return [entry["text"] for entry in payload["add_will_write"]]


def test_a_first_runs_preview_counts_its_new_rows_and_names_their_document(
    tmp_path: Path,
) -> None:
    """A run that only proposes rows says how many, and from where."""
    with _helpline(tmp_path) as helpline:
        run_id, at_review = _start(helpline.client, helpline.project_id)
        _add(helpline.client, run_id)
        ended = helpline.client.get(f"/runs/{run_id}").json()

    assert _lines(at_review) == [f"2 new rows, all from {MEETING_FILE}."]
    assert at_review["open_decisions"] == 0
    # The block previews the press; a run that has ended has nothing to preview.
    assert ended["add_will_write"] is None


def test_an_unanswered_decision_is_counted_and_never_predicted(
    tmp_path: Path,
) -> None:
    """Neither of an open question's two outcomes may appear as a line.

    A possible match against row 1 either merges the written statement into it
    or leaves the row saying that document does not mention this ask. While it
    stands open the preview shows neither, and the count says one answer is
    still owed.
    """
    with _helpline(tmp_path) as helpline:
        first_run, _ = _start(helpline.client, helpline.project_id)
        _add(helpline.client, first_run)

        write_document_stating(
            helpline.folder, REQUIREMENTS_FILE, "8 July 2026", [WRITTEN_QUOTE]
        )
        second_run, unanswered = _start(helpline.client, helpline.project_id)
        _answer(helpline.client, second_run, "possible match", "approved")
        approved = helpline.client.get(f"/runs/{second_run}").json()
        through_mcp = call_tool(
            helpline.application.base_url,
            "get_run_status",
            {"run_id": second_run},
        ).payload

    assert unanswered["open_decisions"] == 1
    assert _lines(unanswered) == [SILENT_ABOUT_ROW_2]

    assert approved["open_decisions"] == 0
    assert _lines(approved) == [
        f"Row 1 · Written down → Yes — {REQUIREMENTS_FILE}.",
        SILENT_ABOUT_ROW_2,
    ]
    # One field built by one core function, so the machine door reads exactly
    # what the screen reads.
    assert through_mcp["add_will_write"] == approved["add_will_write"]
    assert through_mcp["open_decisions"] == approved["open_decisions"]


def test_a_rejected_match_previews_the_row_it_gives_the_ask_instead(
    tmp_path: Path,
) -> None:
    """Rejecting says these are two asks, and Add writes the second one down."""
    with _helpline(tmp_path) as helpline:
        first_run, _ = _start(helpline.client, helpline.project_id)
        _add(helpline.client, first_run)

        write_document_stating(
            helpline.folder, REQUIREMENTS_FILE, "8 July 2026", [WRITTEN_QUOTE]
        )
        second_run, _ = _start(helpline.client, helpline.project_id)
        _answer(helpline.client, second_run, "possible match", "rejected")
        rejected = helpline.client.get(f"/runs/{second_run}").json()

    assert _lines(rejected) == [
        f'A new row for "{WRITTEN_ASK}" — you rejected the match with row 1, '
        "so this ask gets its own row, with Written down: Yes.",
        f"Row 1 · Written down → Not mentioned — {REQUIREMENTS_FILE} was read "
        "and does not mention this ask.",
        SILENT_ABOUT_ROW_2,
    ]


def test_a_disputed_status_names_the_document_on_each_side(tmp_path: Path) -> None:
    """`Disputed` exists because two documents oppose each other, so both are named.

    The handover was read in an earlier run and still stands behind the row's
    status; this run's testing report says the work is absent. The line says
    which document makes which claim, and never merges them into one source.
    """
    with _helpline(tmp_path) as helpline:
        first_run, _ = _start(helpline.client, helpline.project_id)
        _add(helpline.client, first_run)

        write_document_stating(
            helpline.folder, HANDOVER_FILE, "1 August 2026", [HANDOVER_QUOTE]
        )
        handover_run, _ = _start(helpline.client, helpline.project_id)
        _answer(helpline.client, handover_run, "observation match", "approved")
        handed_over = helpline.client.get(f"/runs/{handover_run}").json()
        _add(helpline.client, handover_run)

        write_document_stating(
            helpline.folder, TESTING_FILE, "12 August 2026", [TESTING_QUOTE]
        )
        testing_run, _ = _start(helpline.client, helpline.project_id)
        _answer(helpline.client, testing_run, "observation match", "approved")
        disputed = helpline.client.get(f"/runs/{testing_run}").json()

    assert _lines(handed_over) == [
        f"Row 1 · Status → Handed over — {HANDOVER_FILE}."
    ]
    assert _lines(disputed) == [
        f"Row 1 · What testing found → {TESTING_VERDICT} · Status → Disputed "
        f"— {HANDOVER_FILE} claims it was built; {TESTING_FILE} reports it absent.",
        f"Row 2 · What testing found → Not mentioned — {TESTING_FILE} was read "
        "and is silent about this row.",
    ]


def test_a_run_whose_every_answer_writes_nothing_says_so(tmp_path: Path) -> None:
    """An empty Add is a choice a person can see, never a silent block."""
    with _helpline(tmp_path) as helpline:
        first_run, _ = _start(helpline.client, helpline.project_id)
        _add(helpline.client, first_run)

        write_document_stating(
            helpline.folder, HANDOVER_FILE, "1 August 2026", [HANDOVER_QUOTE]
        )
        handover_run, _ = _start(helpline.client, helpline.project_id)
        _answer(helpline.client, handover_run, "observation match", "rejected")
        nothing = helpline.client.get(f"/runs/{handover_run}").json()

    assert _lines(nothing) == ["Nothing — the register stays as it is."]
