from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import OperationalError

from app.run_logging import log_json_line


STARTUP_LOGGER_NAME = "register.startup"
DATABASE_CONNECTION_FAILURE_MESSAGE = (
    "Could not connect to PostgreSQL while running startup migrations — confirm "
    "the database service is running and the database environment settings are "
    "correct, then restart the application."
)


def migrate_database(project_root: Path, database_url: str) -> None:
    alembic_config = Config(project_root / "alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    try:
        command.upgrade(alembic_config, "head")
    except OperationalError:
        log_startup_event(
            logging.ERROR,
            "database_connection_failed",
            DATABASE_CONNECTION_FAILURE_MESSAGE,
        )
        raise RuntimeError(DATABASE_CONNECTION_FAILURE_MESSAGE) from None
    log_startup_event(
        logging.INFO,
        "database_migrated",
        "PostgreSQL migrations reached the latest revision.",
    )


def load_accepted_extensions(config_path: Path) -> tuple[str, ...]:
    try:
        raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RuntimeError(
            f"{config_path} is missing — restore config/formats.yaml before "
            "starting the application."
        ) from error
    except yaml.YAMLError as error:
        raise RuntimeError(
            f"{config_path} is not valid YAML — fix its YAML syntax before "
            "starting the application."
        ) from error

    if not isinstance(raw_config, dict):
        raise RuntimeError(
            f"{config_path} must contain a YAML mapping — restore the "
            "accepted_extensions and document_page_limit keys."
        )

    accepted_extensions = raw_config.get("accepted_extensions")
    if not isinstance(accepted_extensions, list) or not all(
        isinstance(extension, str) for extension in accepted_extensions
    ):
        raise RuntimeError(
            f"{config_path} accepted_extensions must be a list of strings — "
            "fix that key before starting the application."
        )
    return tuple(accepted_extensions)


def report_formats_without_readers(
    config_path: Path,
    available_reader_extensions: frozenset[str],
) -> None:
    configured_extensions = load_accepted_extensions(config_path)
    for extension in configured_extensions:
        if extension in available_reader_extensions:
            continue
        relative_path = Path("config") / config_path.name
        log_startup_event(
            logging.WARNING,
            "format_reader_missing",
            f"{relative_path} lists {extension} but no reader exists for it — "
            "remove the line or add a reader.",
            extension=extension,
        )


def log_startup_event(
    level: int,
    event: str,
    message: str,
    **fields: Any,
) -> None:
    # Startup happens before any run exists, so these lines carry no run_id.
    log_json_line(STARTUP_LOGGER_NAME, level, event, message, None, **fields)
