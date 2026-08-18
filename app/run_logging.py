from __future__ import annotations

import json
import logging
import sys
from typing import Any


RUN_LOGGER_NAME = "register.run"


def configure_run_logging() -> None:
    """Give run events their own stdout handler, once, at application startup.

    Python prints nothing below WARNING while no handler is set, so without
    this the INFO run events D16 promises never reach `docker compose logs` —
    they were only ever visible where a test harness captured them.
    """
    logger = logging.getLogger(RUN_LOGGER_NAME)
    if any(
        getattr(handler, "writes_run_events_to_stdout", False)
        for handler in logger.handlers
    ):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.writes_run_events_to_stdout = True  # type: ignore[attr-defined]
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    # The lines must appear exactly once: without this, a root handler set by
    # any host process would print every event a second time.
    logger.propagate = False


def log_json_line(
    logger_name: str,
    level: int,
    event: str,
    message: str,
    run_id: str | None,
    **fields: Any,
) -> None:
    payload: dict[str, Any] = {
        "event": event,
        "message": message,
        "run_id": run_id,
        **fields,
    }
    logging.getLogger(logger_name).log(level, json.dumps(payload))


def log_run_event(
    level: int,
    event: str,
    message: str,
    run_id: str | None,
    **fields: Any,
) -> None:
    """Every line the application writes during a run carries its run_id."""
    log_json_line(RUN_LOGGER_NAME, level, event, message, run_id, **fields)
