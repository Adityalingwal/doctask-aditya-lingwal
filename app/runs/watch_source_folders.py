from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Any
from uuid import UUID

import yaml
from psycopg import AsyncConnection

from app.refusal import UnusableRequest
from app.ingest.collect_batch import top_level_files
from app.ingest.read_once import READ_BY_THE_PROJECT, read_by_the_project_parameters
from app.run_logging import log_run_event
from app.runs.run_lifecycle import RunEngine, start_or_queue_run
from app.runs.statuses import (
    ACTIVE_STATUSES,
    DONE,
    ENDED_WITHOUT_CHANGES,
    WAITING,
)


POLL_SECONDS_KEY = "poll_seconds"
QUIET_SECONDS_KEY = "quiet_seconds"
NO_FOLDER = ""


@dataclass(frozen=True)
class WatcherSettings:
    """How often to look, and how long a folder must be still before a run starts."""

    poll_seconds: float
    quiet_seconds: float


@dataclass
class WatchedFolder:
    """What one project's folder looked like last time, and what started a run.

    Held per project and passed in rather than kept at module level, because two
    projects are watched at once and one shared dictionary of state is how one
    project's files end up starting another project's run.
    """

    signature: str
    unchanged_since: float
    started_for: str


def load_watcher_settings(config_path: Path) -> WatcherSettings:
    try:
        parsed = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RuntimeError(
            f"{config_path} is missing — restore config/watcher.yaml, which "
            f"holds {POLL_SECONDS_KEY} and {QUIET_SECONDS_KEY}, before "
            "starting the application."
        ) from error
    except yaml.YAMLError as error:
        raise RuntimeError(
            f"{config_path} is not valid YAML ({error}) — fix its syntax "
            "before starting the application."
        ) from error

    if not isinstance(parsed, dict):
        raise RuntimeError(
            f"{config_path} must hold a YAML mapping with {POLL_SECONDS_KEY} "
            f"and {QUIET_SECONDS_KEY} in it — restore those two keys before "
            "starting the application."
        )
    return WatcherSettings(
        poll_seconds=_positive_seconds(config_path, parsed, POLL_SECONDS_KEY),
        quiet_seconds=_positive_seconds(config_path, parsed, QUIET_SECONDS_KEY),
    )


async def watch_source_folders(
    engine: RunEngine,
    project_root: Path,
    settings: WatcherSettings,
) -> None:
    """Look at every project's folder for ever, starting the runs it earns.

    One failed poll never ends the watching: the folder may be on a mount that
    came back a moment later, and a watcher that stopped would leave the
    Delivery Owner with no auto-start and no sign of why.
    """
    watched: dict[UUID, WatchedFolder] = {}
    while True:
        await asyncio.sleep(settings.poll_seconds)
        try:
            await start_runs_for_settled_folders(
                engine, project_root, settings, watched
            )
        except asyncio.CancelledError:
            raise
        except Exception as error:
            log_run_event(
                logging.ERROR,
                "watcher_poll_failed",
                f"Looking at the watched folders failed ({error}) — the "
                "watcher keeps looking, and POST /runs still starts a run by "
                "hand. Check the folders on the projects are readable.",
                None,
            )


async def start_runs_for_settled_folders(
    engine: RunEngine,
    project_root: Path,
    settings: WatcherSettings,
    watched: dict[UUID, WatchedFolder],
) -> list[UUID]:
    """Start one run per project whose folder changed and has since gone quiet."""
    started: list[UUID] = []
    async with engine.pool.connection() as connection:
        projects = await _projects_to_watch(connection)

    for project in projects:
        folder = _resolve_folder(project_root, project)
        signature = await asyncio.to_thread(folder_signature, folder)
        if not _folder_has_settled(watched, project["id"], signature, settings):
            continue

        async with engine.pool.connection() as connection:
            if await _project_has_a_run_in_flight(connection, project["id"]):
                # A run already holds this project. Its signature is left
                # alone, so the files that arrived reach the run after it.
                continue
            if await _folder_signature_was_served(
                connection, project["id"], folder
            ):
                # A manual run, or the one already waiting behind another run,
                # may have collected this arrival while the watcher was
                # waiting for the folder to settle. Remember that exact
                # signature without writing a second `no changes` run.
                watched[project["id"]].started_for = signature
                log_run_event(
                    logging.INFO,
                    "watcher_arrival_already_served",
                    f"The settled folder change for '{project['name']}' was "
                    "already handled by another run, so the watcher did not "
                    "start a duplicate.",
                    None,
                    project_id=str(project["id"]),
                )
                continue

        watched[project["id"]].started_for = signature
        try:
            run = await start_or_queue_run(engine, project["id"])
        except UnusableRequest as refused:
            # No run exists to name in the log, so the project is named
            # instead. Nothing is started: the folder has nothing to read.
            log_run_event(
                logging.INFO,
                "watcher_refused_to_start_a_run",
                f"The folder watched for '{project['name']}' settled, and no "
                f"run started: {refused}",
                None,
                project_id=str(project["id"]),
            )
            continue
        started.append(run["run_id"])
        log_run_event(
            logging.INFO,
            "watcher_started_run",
            f"The folder watched for '{project['name']}' changed and has been "
            f"still for {settings.quiet_seconds} second(s), so this run "
            "started by itself.",
            str(run["run_id"]),
            project_id=str(project["id"]),
        )
    return started


def folder_signature(folder: Path) -> str:
    """What the folder's top-level files look like right now, as one string.

    Name, size and modification time together, because a file still being
    copied changes size between two polls and that is exactly the arrival the
    quiet period is there to wait out.
    """
    if not folder.is_dir():
        return NO_FOLDER
    listed = sorted(
        f"{path.name}:{path.stat().st_size}:{path.stat().st_mtime_ns}"
        for path in folder.iterdir()
        if path.is_file()
    )
    return "\n".join(listed)


def _folder_has_settled(
    watched: dict[UUID, WatchedFolder],
    project_id: UUID,
    signature: str,
    settings: WatcherSettings,
) -> bool:
    seen = watched.get(project_id)
    if seen is None:
        # First sight of a project: whatever is already in its folder is not an
        # arrival, so it is remembered and starts nothing. A folder full of
        # documents is read by POST /runs, which is unchanged.
        watched[project_id] = WatchedFolder(
            signature=signature,
            unchanged_since=monotonic(),
            started_for=signature,
        )
        return False

    if signature != seen.signature:
        seen.signature = signature
        seen.unchanged_since = monotonic()
        return False
    if signature == seen.started_for:
        return False
    return monotonic() - seen.unchanged_since >= settings.quiet_seconds


async def _projects_to_watch(connection: AsyncConnection) -> list[dict[str, Any]]:
    result = await connection.execute(
        "SELECT id, name, source_folder_path FROM projects ORDER BY created_at"
    )
    return list(await result.fetchall())


async def _project_has_a_run_in_flight(
    connection: AsyncConnection,
    project_id: UUID,
) -> bool:
    """Is a run of this project running, at review, or already queued behind one?"""
    result = await connection.execute(
        "SELECT 1 FROM runs WHERE project_id = %s AND status = ANY(%s) LIMIT 1",
        (project_id, [*ACTIVE_STATUSES, WAITING]),
    )
    return await result.fetchone() is not None


async def _folder_signature_was_served(
    connection: AsyncConnection,
    project_id: UUID,
    folder: Path,
) -> bool:
    """Whether every current file was settled after its last filesystem change.

    A file is served when a settled document read names it, or when a terminal
    run reports it in Skipped (for example an unsupported format or a renamed
    copy already read by content). Comparing the run's finish time with the
    file's modification time matters: an old run naming `notes.md` must not
    suppress the watcher after that same path is edited later.

    An empty folder deliberately returns false. The watcher must still reach
    the shared empty-folder refusal once for a settled deletion, rather than
    silently treating no files as work another run consumed.
    """
    files = await asyncio.to_thread(top_level_files, folder)
    if not files:
        return False

    result = await connection.execute(
        "WITH served AS ("
        "SELECT documents.source_path AS file, runs.finished_at AS served_at "
        "FROM documents JOIN runs ON runs.id = documents.run_id "
        f"WHERE {READ_BY_THE_PROJECT} "
        "UNION ALL "
        "SELECT skipped.entry ->> 'file' AS file, runs.finished_at AS served_at "
        "FROM runs CROSS JOIN LATERAL "
        "jsonb_array_elements(runs.skipped) AS skipped(entry) "
        "WHERE runs.project_id = %s AND runs.status = ANY(%s)"
        ") SELECT file, max(served_at) AS served_at FROM served "
        "WHERE file IS NOT NULL GROUP BY file",
        (
            *read_by_the_project_parameters(project_id),
            project_id,
            [DONE, ENDED_WITHOUT_CHANGES],
        ),
    )
    served_at = {
        row["file"]: row["served_at"] for row in await result.fetchall()
    }
    return all(
        served_at.get(path.name) is not None
        and served_at[path.name].timestamp() >= path.stat().st_mtime
        for path in files
    )


def _resolve_folder(project_root: Path, project: dict[str, Any]) -> Path:
    recorded = Path(project["source_folder_path"])
    return recorded if recorded.is_absolute() else project_root / recorded


def _positive_seconds(config_path: Path, parsed: dict[str, Any], key: str) -> float:
    seconds = parsed.get(key)
    if not isinstance(seconds, (int, float)) or isinstance(seconds, bool):
        raise RuntimeError(
            f"{config_path} {key} must be a number of seconds — fix that key "
            "before starting the application."
        )
    if seconds <= 0:
        raise RuntimeError(
            f"{config_path} {key} is {seconds}, and it must be above zero — a "
            "watcher that waits no time at all starts a run on a folder still "
            "being copied into. Fix that key before starting the application."
        )
    return float(seconds)
