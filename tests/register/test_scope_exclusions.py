from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    match_answer,
    match_marker_against_an_empty_register,
    no_findings_answer,
    observation_answer_of,
    observation_marker,
    write_document_stating,
)
from tests.runs.application import (
    ApplicationProcess,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)


MEETING_FILE = "meeting-notes.md"
SCOPE_FILE = "client-requirements.md"
ASK = "mobile barcode scanning"
ASK_QUOTE = "The warehouse team asked for mobile barcode scanning."
EXCLUSION = "mobile barcode scanning is outside the approved scope"
EXCLUSION_QUOTE = (
    "Mobile barcode scanning is not included in the approved scope for this delivery."
)


def _extraction_answers(exclusion_summary: str = EXCLUSION) -> dict:
    return {
        extract_marker(MEETING_FILE): {
            "document_type": "meeting notes",
            "requirements": [{"summary": ASK, "quote": ASK_QUOTE}],
            "scope_exclusions": [],
            "testing_observations": [],
            "delivery_evidence": [],
            "embedded_instructions": [],
        },
        extract_marker(SCOPE_FILE): {
            "document_type": "client requirements document",
            "requirements": [],
            "scope_exclusions": [
                {"summary": exclusion_summary, "quote": EXCLUSION_QUOTE}
            ],
            "testing_observations": [],
            "delivery_evidence": [],
            "embedded_instructions": [],
        },
    }


@contextmanager
def _one_batch(
    tmp_path: Path,
    script: dict,
) -> Iterator[tuple[Any, str, str]]:
    with temporary_project_folder("scope-exclusions") as (
        folder,
        source_folder_path,
    ):
        write_document_stating(
            folder, MEETING_FILE, "10 March 2026", [ASK_QUOTE]
        )
        write_document_stating(
            folder, SCOPE_FILE, "12 March 2026", [EXCLUSION_QUOTE]
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
                    run_id = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    yield client, project_id, run_id
            finally:
                application.stop()


def _settle(client: object, run_id: str, reject_exclusion: bool = False) -> dict:
    at_review = wait_for_run_status(client, run_id, "needs review")
    for decision in at_review["decisions"]:
        outcome = (
            "rejected"
            if reject_exclusion and decision["kind"] == "observation match"
            else "approved"
        )
        response = client.post(
            f"/runs/{run_id}/decisions",
            json={"decision_id": decision["decision_id"], "outcome": outcome},
        )
        response.raise_for_status()
    client.post(
        f"/runs/{run_id}/finish-review", json={"add_to_register": True}
    ).raise_for_status()
    wait_for_run_status(client, run_id, "done")
    return at_review


def test_a_scope_exclusion_is_never_a_second_positive_requirement(
    tmp_path: Path,
) -> None:
    """Never-do: a negative scope sentence must not become work to deliver."""
    script = _extraction_answers() | {
        match_marker_against_an_empty_register(): match_answer(1),
        observation_marker(): observation_answer_of([1]),
        examine_marker(): no_findings_answer(),
    }
    with _one_batch(tmp_path, script) as (client, project_id, run_id):
        at_review = _settle(client, run_id)
        register = client.get(f"/projects/{project_id}/register").json()

    assert [decision["kind"] for decision in at_review["decisions"]] == [
        "observation match"
    ]
    assert "Status: Excluded" in at_review["decisions"][0]["question"]
    assert len(register["rows"]) == 1
    assert register["rows"][0]["cells"]["what_was_asked"] == ASK
    assert register["rows"][0]["cells"]["in_writing"] == "Excluded"
    assert register["rows"][0]["cells"]["status"] == "Excluded"


def test_rejecting_the_scope_link_leaves_the_requirement_unchanged(
    tmp_path: Path,
) -> None:
    """A model-proposed conflict changes no row without a person's approval."""
    script = _extraction_answers() | {
        match_marker_against_an_empty_register(): match_answer(1),
        observation_marker(): observation_answer_of([1]),
        examine_marker(): no_findings_answer(),
    }
    with _one_batch(tmp_path, script) as (client, project_id, run_id):
        _settle(client, run_id, reject_exclusion=True)
        register = client.get(f"/projects/{project_id}/register").json()

    assert len(register["rows"]) == 1
    assert register["rows"][0]["cells"]["status"] == "Requested"


def test_an_unmatched_scope_exclusion_is_reported_not_attached(
    tmp_path: Path,
) -> None:
    """An exclusion about other work is never forced onto the nearest row."""
    script = _extraction_answers("offline stock counting is outside scope") | {
        match_marker_against_an_empty_register(): match_answer(1),
        observation_marker(): observation_answer_of([None]),
        examine_marker(): no_findings_answer(),
    }
    with _one_batch(tmp_path, script) as (client, project_id, run_id):
        at_review = _settle(client, run_id)
        register = client.get(f"/projects/{project_id}/register").json()

    assert len(register["rows"]) == 1
    assert register["rows"][0]["cells"]["status"] == "Requested"
    assert len(at_review["skipped"]) == 1
    assert at_review["skipped"][0]["kind"] == "not attached"
    assert at_review["skipped"][0]["summary"] == (
        "offline stock counting is outside scope"
    )
