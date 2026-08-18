from __future__ import annotations

import json
import logging
from collections.abc import Iterator

import pytest

from app.run_logging import (
    RUN_LOGGER_NAME,
    configure_run_logging,
    log_run_event,
)


@pytest.fixture()
def run_logger_left_as_found() -> Iterator[None]:
    logger = logging.getLogger(RUN_LOGGER_NAME)
    handlers_before = list(logger.handlers)
    propagate_before = logger.propagate
    level_before = logger.level
    yield
    logger.handlers = handlers_before
    logger.propagate = propagate_before
    logger.setLevel(level_before)


def test_a_run_event_reaches_stdout_as_one_json_line_with_its_run_id(
    capsys: pytest.CaptureFixture[str],
    run_logger_left_as_found: None,
) -> None:
    configure_run_logging()
    log_run_event(logging.INFO, "stage_started", "Ingest started.", "run-123")

    printed = capsys.readouterr().out.strip().splitlines()
    assert len(printed) == 1
    line = json.loads(printed[0])
    assert line["event"] == "stage_started"
    assert line["run_id"] == "run-123"


def test_configuring_the_run_logger_twice_does_not_double_its_lines(
    capsys: pytest.CaptureFixture[str],
    run_logger_left_as_found: None,
) -> None:
    configure_run_logging()
    configure_run_logging()
    log_run_event(logging.INFO, "stage_started", "Ingest started.", "run-123")

    printed = capsys.readouterr().out.strip().splitlines()
    assert len(printed) == 1
