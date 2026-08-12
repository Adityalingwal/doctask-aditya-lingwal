from __future__ import annotations

import json
import logging
from typing import Any


RUN_LOGGER_NAME = "register.run"


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
