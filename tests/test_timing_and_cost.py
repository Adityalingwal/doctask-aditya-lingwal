from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import yaml
from sqlalchemy import create_engine, text

from conftest import (
    PROJECT_ROOT,
    ApplicationProcess,
    logged_run_events,
    recorded_markers,
    temporary_database,
    wait_for_run_status,
    wait_until,
)
from app.model.scripted_client import ANSWER_KEY, PROMPT_MARKER_KEY
from mcp_client import call_tool
from register_documents import (
    examine_marker,
    extract_marker,
    extraction_answer,
    match_answer,
    match_marker,
    no_findings_answer,
    write_meeting_note,
)


SOURCE_FILE = "meeting-note.md"
REQUIREMENT = "an email to the operations team on intake form submit"
# The key a scripted answer carries its reported usage under. It is written
# here as the script file's own format so this test says what a provider
# reports, not what one module happens to call it.
SCRIPT_USAGE_KEY = "usage"
EXTRACT_USAGE = {"prompt_tokens": 100, "completion_tokens": 10}
MATCH_USAGE = {"prompt_tokens": 200, "completion_tokens": 20}
EXAMINE_USAGE = {"prompt_tokens": 50, "completion_tokens": 5}
WAITING_FOR_REVIEW = "waiting for review"
ENDED_WITHOUT_CHANGES = "ended without changes"
KILLED_RUN_DOCUMENTS = {
    "doc-1.md": "an email to the operations team on intake form submit",
    "doc-2.md": "the same notification sent over WhatsApp",
    "doc-3.md": "search over old intake records",
}
MODEL_DELAY_SECONDS = 2.0
FAKE_KEY = "sk-or-v1-not-a-real-key-0123456789"


def test_the_reported_cost_is_labelled_an_estimate_and_never_a_bill(
    tmp_path: Path,
) -> None:
    with _one_document_run(tmp_path, usage=True) as (application, run_id, database_url):
        with application.client() as client:
            status = client.get(f"/runs/{run_id}").json()
        stored = _stored_cost(database_url, run_id)

    reported = status["cost_and_timing"]
    prompt_rate, completion_rate = _configured_rates()
    expected = (
        Decimal(350) * prompt_rate + Decimal(35) * completion_rate
    ).quantize(Decimal("0.000001"))

    assert reported["estimated_cost_usd"] == str(expected)
    assert stored == expected
    assert "estimate" in reported["estimate_note"].lower()
    assert "not a bill" in reported["estimate_note"].lower()
    assert reported["tokens"] == {
        "prompt": 350,
        "completion": 35,
        "calls_reporting_usage": 3,
        "calls_without_usage": 0,
    }
    assert [stage["stage"] for stage in reported["stages"]] == [
        "ingest",
        "extract",
        "match",
        "examine",
    ]
    assert all(stage["seconds"] > 0 for stage in reported["stages"])
    assert reported["total_seconds"] == pytest.approx(
        sum(stage["seconds"] for stage in reported["stages"])
    )


def test_the_status_tool_reports_the_same_cost_and_timing_as_the_endpoint(
    tmp_path: Path,
) -> None:
    with _one_document_run(tmp_path, usage=True) as (application, run_id, _):
        with application.client() as client:
            over_http = client.get(f"/runs/{run_id}").json()
        over_mcp = call_tool(
            application.base_url, "get_run_status", {"run_id": run_id}
        )

    assert over_mcp.refused is False
    assert over_mcp.payload["cost_and_timing"] == over_http["cost_and_timing"]


def test_a_run_whose_model_reported_no_tokens_reports_an_unknown_cost_not_a_zero(
    tmp_path: Path,
) -> None:
    with _one_document_run(tmp_path, usage=False) as (
        application,
        run_id,
        database_url,
    ):
        with application.client() as client:
            status = client.get(f"/runs/{run_id}").json()
        stored = _stored_cost(database_url, run_id)

    reported = status["cost_and_timing"]

    # Neither the cost nor either token count may come back as a zero: a zero
    # reads as a figure someone measured, and nobody measured this one.
    assert stored is None
    assert reported["estimated_cost_usd"] is None
    assert reported["tokens"]["prompt"] is None
    assert reported["tokens"]["completion"] is None
    assert "token count" in reported["cost_unknown_reason"].lower()
    assert reported["tokens"]["calls_without_usage"] == 3
    assert reported["tokens"]["calls_reporting_usage"] == 0


def test_a_stage_that_did_not_run_has_no_duration(tmp_path: Path) -> None:
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    script_path = tmp_path / "script.json"
    _write_script(script_path, {}, {})

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
                        "name": "Nothing to read",
                        "source_folder_path": str(source_folder),
                    },
                ).json()["project_id"]
                run_id = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                status = wait_for_run_status(client, run_id, ENDED_WITHOUT_CHANGES)
        finally:
            application.stop()

    reported = status["cost_and_timing"]

    assert [stage["stage"] for stage in reported["stages"]] == ["ingest"]
    assert all(stage["seconds"] > 0 for stage in reported["stages"])
    assert reported["estimated_cost_usd"] is None
    assert "no model call" in reported["cost_unknown_reason"].lower()


def test_a_killed_and_resumed_run_reports_each_stage_once_without_doubling_tokens(
    tmp_path: Path,
) -> None:
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    script_path = tmp_path / "script.json"
    call_log_path = tmp_path / "model-calls.jsonl"

    answers: dict[str, Any] = {
        match_marker(): match_answer(len(KILLED_RUN_DOCUMENTS)),
        examine_marker(): no_findings_answer(),
    }
    usage = {match_marker(): MATCH_USAGE, examine_marker(): EXAMINE_USAGE}
    for source_file, requirement in KILLED_RUN_DOCUMENTS.items():
        quote = write_meeting_note(source_folder, source_file, requirement)
        answers[extract_marker(source_file)] = extraction_answer(requirement, quote)
        usage[extract_marker(source_file)] = EXTRACT_USAGE
    _write_script(script_path, answers, usage)

    with temporary_database() as database_url:
        application = ApplicationProcess(
            database_url=database_url,
            script_path=script_path,
            call_log_path=call_log_path,
            delay_seconds=MODEL_DELAY_SECONDS,
        )
        application.start()
        try:
            with application.client() as client:
                project_id = client.post(
                    "/projects",
                    json={
                        "name": "Killed run timing",
                        "source_folder_path": str(source_folder),
                    },
                ).json()["project_id"]
                run_id = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                # The kill lands inside Extract with the third document's call
                # in flight, so the resumed run asks about that document again.
                wait_until(
                    lambda: len(recorded_markers(call_log_path))
                    >= len(KILLED_RUN_DOCUMENTS),
                    "the model has been asked about every document",
                )
            application.kill()

            application.start()
            with application.client() as client:
                status = wait_for_run_status(client, run_id, WAITING_FOR_REVIEW)
        finally:
            application.stop()

    markers = recorded_markers(call_log_path)
    reported = status["cost_and_timing"]
    stage_names = [stage["stage"] for stage in reported["stages"]]
    every_extract = len(KILLED_RUN_DOCUMENTS) * EXTRACT_USAGE["prompt_tokens"]

    # The repeated call really happened; what must not happen is counting the
    # document it read twice.
    assert markers.count(extract_marker("doc-3.md")) == 2
    assert stage_names == sorted(set(stage_names), key=stage_names.index)
    assert stage_names.count("extract") == 1
    assert reported["tokens"]["prompt"] == (
        every_extract
        + MATCH_USAGE["prompt_tokens"]
        + EXAMINE_USAGE["prompt_tokens"]
    )
    assert reported["tokens"]["calls_reporting_usage"] == (
        len(KILLED_RUN_DOCUMENTS) + 2
    )


def test_the_new_timing_and_token_log_fields_carry_no_secret_or_document_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    log_path = tmp_path / "run-events.log"

    with _one_document_run(tmp_path, usage=True, log_path=log_path) as (
        application,
        _,
        _database_url,
    ):
        assert application is not None

    events = {event["event"]: event for event in logged_run_events(log_path)}
    written = log_path.read_text(encoding="utf-8", errors="replace")
    document_text = (tmp_path / "intake-portal" / SOURCE_FILE).read_text(
        encoding="utf-8"
    )

    for stage_event in (
        "ingest_finished",
        "extract_document_finished",
        "match_finished",
        "examine_finished",
    ):
        assert events[stage_event]["seconds"] > 0
    assert events["extract_document_finished"]["prompt_tokens"] == 100
    assert events["extract_document_finished"]["completion_tokens"] == 10
    assert events["match_finished"]["prompt_tokens"] == 200
    assert events["examine_finished"]["prompt_tokens"] == 50
    assert FAKE_KEY not in written
    assert document_text not in written
    assert REQUIREMENT not in written


@contextmanager
def _one_document_run(
    tmp_path: Path,
    usage: bool,
    log_path: Path | None = None,
) -> Iterator[tuple[ApplicationProcess, str, str]]:
    """One run of one document, parked at Review with its numbers recorded."""
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    quote = write_meeting_note(source_folder, SOURCE_FILE, REQUIREMENT)
    script_path = tmp_path / "script.json"
    _write_script(
        script_path,
        {
            match_marker(): match_answer(1),
            examine_marker(): no_findings_answer(),
            extract_marker(SOURCE_FILE): extraction_answer(REQUIREMENT, quote),
        },
        {
            match_marker(): MATCH_USAGE,
            examine_marker(): EXAMINE_USAGE,
            extract_marker(SOURCE_FILE): EXTRACT_USAGE,
        }
        if usage
        else {},
    )

    with temporary_database() as database_url:
        application = ApplicationProcess(
            database_url=database_url,
            script_path=script_path,
            call_log_path=tmp_path / "model-calls.jsonl",
            log_path=log_path,
        )
        application.start()
        try:
            with application.client() as client:
                project_id = client.post(
                    "/projects",
                    json={
                        "name": "Timing and cost intake portal",
                        "source_folder_path": str(source_folder),
                    },
                ).json()["project_id"]
                run_id = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                wait_for_run_status(client, run_id, WAITING_FOR_REVIEW)
            yield application, run_id, database_url
        finally:
            application.stop()


def _write_script(
    script_path: Path,
    answers: dict[str, Any],
    usage_by_marker: dict[str, dict[str, int]],
) -> None:
    """The scripted answers, each with the usage that call reports, or none."""
    entries = []
    for marker, answer in answers.items():
        entry = {PROMPT_MARKER_KEY: marker, ANSWER_KEY: json.dumps(answer)}
        reported = usage_by_marker.get(marker)
        if reported is not None:
            entry[SCRIPT_USAGE_KEY] = reported
        entries.append(entry)
    script_path.write_text(json.dumps(entries), encoding="utf-8")


def _configured_rates() -> tuple[Decimal, Decimal]:
    rates = yaml.safe_load(
        (PROJECT_ROOT / "config" / "model.yaml").read_text(encoding="utf-8")
    )["rates_usd_per_token"]
    return Decimal(str(rates["prompt"])), Decimal(str(rates["completion"]))


def _stored_cost(database_url: str, run_id: str) -> Decimal | None:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return connection.execute(
                text("SELECT estimated_cost_usd FROM runs WHERE id = :id"),
                {"id": run_id},
            ).scalar_one()
    finally:
        engine.dispose()
