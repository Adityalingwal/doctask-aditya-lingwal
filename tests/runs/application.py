from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import time
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, IO
from uuid import uuid4

import httpx
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from app.model.scripted_client import (
    ANSWER_KEY,
    ERROR_KEY,
    ERROR_MESSAGE_KEY,
    ERROR_STATUS_CODE_KEY,
    PROMPT_MARKER_KEY,
)
from app.run_logging import RUN_LOGGER_NAME


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_URL_ENVIRONMENT_VARIABLE = "DATABASE_URL"
RULES_CONFIG_PATH_ENVIRONMENT_VARIABLE = "RULES_CONFIG_PATH"
WATCHER_CONFIG_PATH_ENVIRONMENT_VARIABLE = "WATCHER_CONFIG_PATH"
DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres@db:5432/register"
POSTGRES_MAINTENANCE_DATABASE = "postgres"
TEST_DATABASE_PREFIX = "register_test_"
HEALTH_TIMEOUT_SECONDS = 60.0
POLL_SECONDS = 0.2
LOG_CONFIG_FILE_SUFFIX = ".log-config.json"


@contextmanager
def temporary_database() -> Iterator[str]:
    """A real PostgreSQL database of its own, migrated and then dropped."""
    application_url = make_url(
        os.environ.get(DATABASE_URL_ENVIRONMENT_VARIABLE, DEFAULT_DATABASE_URL)
    )
    database_name = f"{TEST_DATABASE_PREFIX}{uuid4().hex}"
    test_url = application_url.set(database=database_name)
    maintenance_engine = create_engine(
        application_url.set(database=POSTGRES_MAINTENANCE_DATABASE),
        isolation_level="AUTOCOMMIT",
    )
    try:
        with maintenance_engine.connect() as connection:
            connection.exec_driver_sql(f'CREATE DATABASE "{database_name}"')
        alembic_config = Config(PROJECT_ROOT / "alembic.ini")
        alembic_config.set_main_option(
            "sqlalchemy.url", test_url.render_as_string(hide_password=False)
        )
        command.upgrade(alembic_config, "head")
        yield test_url.render_as_string(hide_password=False)
    finally:
        with maintenance_engine.connect() as connection:
            connection.exec_driver_sql(
                f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)'
            )
        maintenance_engine.dispose()


@dataclass
class ApplicationProcess:
    """One real application process, started and killed the way a crash does."""

    database_url: str
    script_path: Path
    call_log_path: Path
    delay_seconds: float = 0.0
    rules_config_path: Path | None = None
    watcher_config_path: Path | None = None
    log_path: Path | None = None
    port: int = field(default_factory=lambda: _free_port())
    _process: subprocess.Popen | None = None
    _log_file: IO[str] | None = None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> None:
        environment = {
            **os.environ,
            DATABASE_URL_ENVIRONMENT_VARIABLE: self.database_url,
            "MODEL_CLIENT": "scripted",
            "SCRIPTED_MODEL_SCRIPT": str(self.script_path),
            "SCRIPTED_MODEL_CALL_LOG": str(self.call_log_path),
            "SCRIPTED_MODEL_DELAY_SECONDS": str(self.delay_seconds),
        }
        if self.rules_config_path is not None:
            environment[RULES_CONFIG_PATH_ENVIRONMENT_VARIABLE] = str(
                self.rules_config_path
            )
        if self.watcher_config_path is not None:
            environment[WATCHER_CONFIG_PATH_ENVIRONMENT_VARIABLE] = str(
                self.watcher_config_path
            )
        command = [
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(self.port),
        ]
        if self.log_path is not None:
            command += ["--log-config", str(_run_event_log_config(self.log_path))]
            self._log_file = self.log_path.open("a", encoding="utf-8")
        self._process = subprocess.Popen(
            command,
            cwd=str(PROJECT_ROOT),
            env=environment,
            stdout=self._log_file,
            stderr=subprocess.STDOUT if self._log_file is not None else None,
        )
        self._wait_until_healthy()

    def kill(self) -> None:
        """SIGKILL: no cleanup, no shutdown hook, nothing given a chance to run."""
        os.kill(self._process.pid, signal.SIGKILL)
        self._process.wait(timeout=30)
        self._process = None
        self._close_log_file()

    def stop(self) -> None:
        if self._process is None:
            return
        self._process.terminate()
        self._process.wait(timeout=30)
        self._process = None
        self._close_log_file()

    def _close_log_file(self) -> None:
        if self._log_file is not None:
            self._log_file.close()
            self._log_file = None

    def client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, timeout=30)

    def _wait_until_healthy(self) -> None:
        deadline = time.monotonic() + HEALTH_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            try:
                if httpx.get(f"{self.base_url}/health", timeout=2).status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(POLL_SECONDS)
        raise TimeoutError(
            f"the application did not answer /health on port {self.port} within "
            f"{HEALTH_TIMEOUT_SECONDS} seconds — read its output above for the "
            "startup failure it reported."
        )


def write_script(script_path: Path, answers: dict[str, dict]) -> None:
    entries = []
    for marker, answer in answers.items():
        scripted = (
            answer
            if ERROR_KEY in answer
            else {ANSWER_KEY: json.dumps(answer)}
        )
        entries.append({PROMPT_MARKER_KEY: marker, **scripted})
    script_path.write_text(json.dumps(entries), encoding="utf-8")


def model_call_failure(message: str, status_code: int | None = None) -> dict[str, Any]:
    """A scripted call that fails the way the provider's SDK fails."""
    return {ERROR_KEY: {ERROR_MESSAGE_KEY: message, ERROR_STATUS_CODE_KEY: status_code}}


def recorded_markers(call_log_path: Path) -> list[str]:
    return [call["marker"] for call in recorded_calls(call_log_path)]


def recorded_calls(call_log_path: Path) -> list[dict[str, Any]]:
    """Every scripted model call, with the moment the call started.

    The moment matters to a concurrency test: a call occupies the scripted
    client for its configured delay, so two calls whose windows overlap were
    genuinely in flight together rather than one after the other.
    """
    if not call_log_path.exists():
        return []
    calls = []
    for line in call_log_path.read_text(encoding="utf-8").splitlines():
        try:
            recorded = json.loads(line)
        except json.JSONDecodeError:
            continue
        calls.append(
            {
                "marker": recorded["marker"],
                "asked_at": datetime.fromisoformat(recorded["asked_at"]),
            }
        )
    return calls


def logged_run_events(log_path: Path) -> list[dict[str, Any]]:
    """Every structured run event the application process wrote to stdout."""
    if not log_path.exists():
        return []
    events = []
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and "event" in payload:
            events.append(payload)
    return events


def _run_event_log_config(log_path: Path) -> Path:
    """Write the logging configuration that puts run events on stdout.

    uvicorn's shipped configuration leaves the run logger without a handler, so
    an INFO run event reaches nothing at all and a test cannot read one back.
    The application is started with this file instead, which changes where the
    records go and nothing about the records themselves.
    """
    config_path = log_path.with_suffix(LOG_CONFIG_FILE_SUFFIX)
    config_path.write_text(
        json.dumps(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {"one_line": {"format": "%(message)s"}},
                "handlers": {
                    "stdout": {
                        "class": "logging.StreamHandler",
                        "formatter": "one_line",
                        "stream": "ext://sys.stdout",
                    }
                },
                "loggers": {
                    RUN_LOGGER_NAME: {
                        "handlers": ["stdout"],
                        "level": "INFO",
                        "propagate": False,
                    }
                },
                "root": {"handlers": ["stdout"], "level": "WARNING"},
            }
        ),
        encoding="utf-8",
    )
    return config_path


def wait_for_run_status(
    client: httpx.Client,
    run_id: str,
    status: str,
) -> dict[str, Any]:
    return wait_until(
        lambda: _run_in_status(client, run_id, status),
        f"run {run_id} reports '{status}'",
    )


def approve_every_decision(client: httpx.Client, run_id: str) -> None:
    for decision in client.get(f"/runs/{run_id}").json()["decisions"]:
        if decision["outcome"] is not None:
            continue
        client.post(
            f"/runs/{run_id}/decisions",
            json={"decision_id": decision["decision_id"], "outcome": "approved"},
        ).raise_for_status()


def approve_every_decision_and_finish_review(
    client: httpx.Client,
    run_id: str,
) -> None:
    approve_every_decision(client, run_id)
    client.post(f"/runs/{run_id}/finish-review").raise_for_status()


def wait_until(
    condition: Callable[[], Any],
    description: str,
    timeout_seconds: float = 60.0,
) -> Any:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        answer = condition()
        if answer:
            return answer
        time.sleep(POLL_SECONDS)
    raise TimeoutError(f"timed out waiting until {description}")


def _run_in_status(
    client: httpx.Client,
    run_id: str,
    status: str,
) -> dict[str, Any] | None:
    run = client.get(f"/runs/{run_id}").json()
    return run if run["status"] == status else None


def _free_port() -> int:
    with closing(socket.socket()) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]
