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
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_URL_ENVIRONMENT_VARIABLE = "DATABASE_URL"
DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres@db:5432/register"
POSTGRES_MAINTENANCE_DATABASE = "postgres"
TEST_DATABASE_PREFIX = "register_test_"
HEALTH_TIMEOUT_SECONDS = 60.0
POLL_SECONDS = 0.2


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
    port: int = field(default_factory=lambda: _free_port())
    _process: subprocess.Popen | None = None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> None:
        self._process = subprocess.Popen(
            [
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
            ],
            cwd=str(PROJECT_ROOT),
            env={
                **os.environ,
                DATABASE_URL_ENVIRONMENT_VARIABLE: self.database_url,
                "MODEL_CLIENT": "scripted",
                "SCRIPTED_MODEL_SCRIPT": str(self.script_path),
                "SCRIPTED_MODEL_CALL_LOG": str(self.call_log_path),
                "SCRIPTED_MODEL_DELAY_SECONDS": str(self.delay_seconds),
            },
        )
        self._wait_until_healthy()

    def kill(self) -> None:
        """SIGKILL: no cleanup, no shutdown hook, nothing given a chance to run."""
        os.kill(self._process.pid, signal.SIGKILL)
        self._process.wait(timeout=30)
        self._process = None

    def stop(self) -> None:
        if self._process is None:
            return
        self._process.terminate()
        self._process.wait(timeout=30)
        self._process = None

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
    script_path.write_text(
        json.dumps(
            [
                {"when_prompt_contains": marker, "answer": json.dumps(answer)}
                for marker, answer in answers.items()
            ]
        ),
        encoding="utf-8",
    )


def recorded_markers(call_log_path: Path) -> list[str]:
    if not call_log_path.exists():
        return []
    markers = []
    for line in call_log_path.read_text(encoding="utf-8").splitlines():
        try:
            markers.append(json.loads(line)["marker"])
        except json.JSONDecodeError:
            continue
    return markers


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


def _free_port() -> int:
    with closing(socket.socket()) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]
