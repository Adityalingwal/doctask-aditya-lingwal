from __future__ import annotations

import asyncio
import logging
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from app.examine.frozen_rules import RulesFileUnusable
from app.run_logging import RUN_LOGGER_NAME
from app.extract.answer import (
    CLIENT_REQUIREMENTS_DOCUMENT,
    DOCUMENT_WORKFLOW_ORDER,
    MEETING_NOTES,
)
from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    feedback_extraction_answer,
    handover_answer,
    match_answer,
    match_marker,
    no_findings_answer,
    observation_answer_of,
    observation_marker,
    requirement_extraction_answer,
    write_meeting_note,
)
from tests.register.stored_register import rules_applied_of_run
from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    recorded_markers,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)


MEETING_FILE = "meeting-notes-02-jul.md"
REQUIREMENTS_FILE = "client-requirements-v1.md"
HANDOVER_FILE = "handover-summary.md"
TESTING_FILE = "testing-feedback-12-aug.md"

SPOKEN_ASK = "a voice agent that answers support-line calls"
WRITTEN_ASK = "one dashboard containing all call and chat transcripts"
DELIVERED = "the voice agent is live and answering calls"
TESTED = "the voice agent answered every question correctly"

# The rule text reaches the model as JSON, so a marker naming one rule's id
# matches only a prompt that actually carried that rule.
R4_IN_THE_PROMPT = '"id": "R4"'

UNKNOWN_DOCUMENT_KIND = "invoice"
RULES_NAMING_AN_UNKNOWN_KIND = f"""\
rules:
  - id: R1
    text: "Anything built must have a written requirement."
    applies_when:
      - {UNKNOWN_DOCUMENT_KIND}
"""


def test_a_rule_runs_only_after_every_document_kind_it_names_was_read(
    tmp_path: Path,
) -> None:
    """A rule waits for the documents it is about, and every one of them.

    Six findings in one demo came from a rule about testing outcomes judged
    before any testing feedback had been read: with nothing to judge, silence
    reads as a fault. R5 names two kinds, so a project that has read only the
    handover still leaves it waiting.
    """
    after_the_handover, after_the_testing, markers = _two_runs(tmp_path)

    assert after_the_handover == ["R1"]
    assert after_the_testing == ["R1", "R2", "R4", "R5"]
    # What the model was actually sent, not only what the run recorded: the
    # marker matches a prompt holding R4 and nothing else does.
    assert markers["before_testing"].count(R4_IN_THE_PROMPT) == 0
    assert markers["after_testing"].count(R4_IN_THE_PROMPT) == 1


@pytest.fixture()
def run_logger_left_as_found() -> Iterator[None]:
    """Starting the application configures the run logger; put it back after.

    The handler it adds holds the `sys.stdout` of the moment, and it is added
    once and never replaced — so a test that starts the application and walks
    away leaves every later test's run events going to a stream pytest has
    already swapped out.
    """
    logger = logging.getLogger(RUN_LOGGER_NAME)
    handlers_before = list(logger.handlers)
    propagate_before = logger.propagate
    level_before = logger.level
    yield
    logger.handlers = handlers_before
    logger.propagate = propagate_before
    logger.setLevel(level_before)


def test_an_unknown_applies_when_value_stops_startup_naming_the_four_kinds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    run_logger_left_as_found: None,
) -> None:
    """A broken rules file stops the application, not the first run someone starts.

    Waiting for the first run would mean a person presses start, pays for
    nothing, and only then learns the file is wrong.
    """
    broken = tmp_path / "rules.yaml"
    broken.write_text(RULES_NAMING_AN_UNKNOWN_KIND, encoding="utf-8")

    with temporary_database() as database_url:
        monkeypatch.setenv("DATABASE_URL", database_url)
        monkeypatch.setenv("RULES_CONFIG_PATH", str(broken))
        with pytest.raises(RulesFileUnusable) as refused:
            asyncio.run(_start_the_application())

    message = str(refused.value)
    assert UNKNOWN_DOCUMENT_KIND in message
    for kind in DOCUMENT_WORKFLOW_ORDER:
        assert kind in message


async def _start_the_application() -> None:
    from app.main import app, lifespan

    async with lifespan(app):
        pass


def _two_runs(tmp_path: Path) -> tuple[list[str], list[str], dict[str, list[str]]]:
    """One run reading three kinds, then a second reading the testing feedback."""
    script_path = tmp_path / "script.json"
    call_log_path = tmp_path / "model-calls.jsonl"
    waiting = tmp_path / "not-yet-delivered"
    waiting.mkdir()

    with temporary_project_folder("applies-when") as (folder, folder_path):
        spoken_quote = write_meeting_note(folder, MEETING_FILE, SPOKEN_ASK)
        written_quote = write_meeting_note(folder, REQUIREMENTS_FILE, WRITTEN_ASK)
        handover_quote = write_meeting_note(folder, HANDOVER_FILE, DELIVERED)
        testing_quote = write_meeting_note(waiting, TESTING_FILE, TESTED)
        write_script(
            script_path,
            {
                extract_marker(MEETING_FILE): requirement_extraction_answer(
                    SPOKEN_ASK, spoken_quote, MEETING_NOTES
                ),
                extract_marker(REQUIREMENTS_FILE): requirement_extraction_answer(
                    WRITTEN_ASK, written_quote, CLIENT_REQUIREMENTS_DOCUMENT
                ),
                extract_marker(HANDOVER_FILE): handover_answer(
                    [(DELIVERED, handover_quote)]
                ),
                extract_marker(TESTING_FILE): feedback_extraction_answer(
                    [(TESTED, "Passed", testing_quote)]
                ),
                match_marker(): match_answer(2),
                observation_marker(): observation_answer_of([1]),
                R4_IN_THE_PROMPT: no_findings_answer(),
                examine_marker(): no_findings_answer(),
            },
        )
        with temporary_database() as database_url:
            application = ApplicationProcess(
                database_url=database_url,
                script_path=script_path,
                call_log_path=call_log_path,
            )
            application.start()
            try:
                with application.client() as client:
                    project_id = client.post(
                        "/projects", json={"source_folder_path": folder_path}
                    ).json()["project_id"]
                    first = _run_to_done(client, project_id)
                    before_testing = recorded_markers(call_log_path)

                    shutil.copy(waiting / TESTING_FILE, folder / TESTING_FILE)
                    second = _run_to_done(client, project_id)
                    after_testing = recorded_markers(call_log_path)[
                        len(before_testing) :
                    ]

                    return (
                        rules_applied_of_run(database_url, first),
                        rules_applied_of_run(database_url, second),
                        {
                            "before_testing": before_testing,
                            "after_testing": after_testing,
                        },
                    )
            finally:
                application.stop()


def _run_to_done(client: Any, project_id: str) -> str:
    run_id = client.post("/runs", json={"project_id": project_id}).json()["run_id"]
    wait_for_run_status(client, run_id, "needs review")
    approve_every_decision_and_finish_review(client, run_id)
    wait_for_run_status(client, run_id, "done")
    return run_id
