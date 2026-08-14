from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy.exc import OperationalError

from app import startup


def test_unavailable_database_reports_cause_and_fix_without_exposing_secret(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    secret_value = "must-not-appear"
    connection_error = OperationalError(
        "connect",
        {},
        RuntimeError(f"database password was {secret_value}"),
    )

    def fail_upgrade(_: Config, __: str) -> None:
        raise connection_error

    monkeypatch.setattr(startup.command, "upgrade", fail_upgrade)

    with caplog.at_level(logging.ERROR, logger=startup.STARTUP_LOGGER_NAME):
        with pytest.raises(RuntimeError) as raised_error:
            startup.migrate_database(
                tmp_path,
                f"postgresql+psycopg://postgres:{secret_value}@db:5432/register",
            )

    assert str(raised_error.value) == startup.DATABASE_CONNECTION_FAILURE_MESSAGE
    payload = json.loads(caplog.records[-1].message)
    assert payload == {
        "event": "database_connection_failed",
        "message": startup.DATABASE_CONNECTION_FAILURE_MESSAGE,
        "run_id": None,
    }
    assert secret_value not in caplog.text
    assert secret_value not in str(raised_error.value)
