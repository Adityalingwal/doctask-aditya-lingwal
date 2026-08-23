from __future__ import annotations

import asyncio
import hashlib
import shutil
from pathlib import Path
from typing import Any, NamedTuple
from uuid import UUID, uuid4

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from app.database import build_connection_pool
from app.extract.answer import (
    CLIENT_REQUIREMENTS_DOCUMENT,
    MEETING_NOTES,
    UNRELATED_DOCUMENT,
)
from app.ingest.collect_batch import _already_read_by_name_or_content
from app.ingest.read_once import documents_read_by_project
from app.register.cells import IN_WRITING, IN_WRITING_NOT_KNOWN_YET
from app.runs.statuses import (
    CLOSED_WITHOUT_EXPORT,
    DONE,
    ENDED_WITHOUT_CHANGES,
)
from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    extraction_answer,
    match_answer,
    match_marker,
    no_findings_answer,
    requirement_extraction_answer,
    write_meeting_note,
)
from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)


class SeededDocument(NamedTuple):
    """One document, the state it was left in, and whether it counts as read."""

    source_path: str
    kind: str
    run_status: str
    requirement_count: int
    has_extraction: bool
    counts_as_read: bool


# Every shape the read-once rule distinguishes, each in the run ending that
# decides it. A discarded run settles nothing it carried, except an unrelated
# document, which is unrelated whatever its run did.
SEEDED = (
    SeededDocument(
        "requirements-added.md", CLIENT_REQUIREMENTS_DOCUMENT, DONE, 1, True, True
    ),
    SeededDocument(
        "requirements-discarded.md",
        CLIENT_REQUIREMENTS_DOCUMENT,
        CLOSED_WITHOUT_EXPORT,
        1,
        True,
        False,
    ),
    SeededDocument(
        "asks-for-nothing.md", MEETING_NOTES, ENDED_WITHOUT_CHANGES, 0, True, True
    ),
    SeededDocument(
        "asks-for-nothing-discarded.md",
        MEETING_NOTES,
        CLOSED_WITHOUT_EXPORT,
        0,
        True,
        False,
    ),
    SeededDocument(
        "staff-leave-policy.md", UNRELATED_DOCUMENT, CLOSED_WITHOUT_EXPORT, 0, True, True
    ),
    SeededDocument(
        "requirements-never-extracted.md",
        CLIENT_REQUIREMENTS_DOCUMENT,
        DONE,
        0,
        False,
        False,
    ),
)


def test_ingest_and_match_share_one_definition_of_read() -> None:
    """One document state answers the same question to Ingest and to the register.

    Ingest asks it to decide whether to pay to read a file again; the absence
    move and the rule gate ask it to decide what the register may claim a
    document was silent about. Two definitions would let a discarded run's
    requirements document be invisible to one and settled to the other.
    """
    answers = asyncio.run(_ask_both_of_every_seeded_document())

    for seeded in SEEDED:
        ingest_says, register_says = answers[seeded.source_path]
        assert ingest_says == seeded.counts_as_read, seeded.source_path
        assert register_says == seeded.counts_as_read, seeded.source_path


async def _ask_both_of_every_seeded_document() -> dict[str, tuple[bool, bool]]:
    with temporary_database() as database_url:
        pool = build_connection_pool(database_url)
        await pool.open(wait=True)
        try:
            async with pool.connection() as connection:
                project_id = await _seed(connection)
                return {
                    seeded.source_path: (
                        await _ingest_counts_it_read(connection, project_id, seeded),
                        await _register_counts_it_read(connection, project_id, seeded),
                    )
                    for seeded in SEEDED
                }
        finally:
            await pool.close()


async def _ingest_counts_it_read(
    connection: AsyncConnection,
    project_id: UUID,
    seeded: SeededDocument,
) -> bool:
    matched = await _already_read_by_name_or_content(
        connection, project_id, seeded.source_path, _content_hash(seeded.source_path)
    )
    return matched is not None


async def _register_counts_it_read(
    connection: AsyncConnection,
    project_id: UUID,
    seeded: SeededDocument,
) -> bool:
    read = await documents_read_by_project(connection, project_id, seeded.kind)
    return seeded.source_path in {document["source_path"] for document in read}


async def _seed(connection: AsyncConnection) -> UUID:
    project_id = uuid4()
    await connection.execute(
        "INSERT INTO projects (id, name, source_folder_path) VALUES (%s, %s, %s)",
        (project_id, f"One definition {project_id}", f"sample-projects/one-{project_id}"),
    )
    for seeded in SEEDED:
        run_id = uuid4()
        await connection.execute(
            "INSERT INTO runs (id, project_id, status) VALUES (%s, %s, %s)",
            (run_id, project_id, seeded.run_status),
        )
        await connection.execute(
            "INSERT INTO documents (id, run_id, source_path, extracted_text, "
            "content_hash, extraction) VALUES (%s, %s, %s, %s, %s, %s)",
            (
                uuid4(),
                run_id,
                seeded.source_path,
                f"The text of {seeded.source_path}.",
                _content_hash(seeded.source_path),
                Jsonb(_extraction(seeded)) if seeded.has_extraction else None,
            ),
        )
    return project_id


def _extraction(seeded: SeededDocument) -> dict[str, Any]:
    return {
        "document_type": seeded.kind,
        "requirements": [
            {
                "summary": f"Ask {index} of {seeded.source_path}.",
                "source_file": seeded.source_path,
                "place": "Discussion",
                "source_words": f"The text of {seeded.source_path}.",
            }
            for index in range(seeded.requirement_count)
        ],
        "testing_observations": [],
        "delivery_evidence": [],
        "embedded_instructions": [],
    }


def _content_hash(source_path: str) -> str:
    return hashlib.sha256(source_path.encode("utf-8")).hexdigest()


REQUIREMENTS_FILE = "client-requirements-v1.md"
MEETING_FILE = "meeting-notes-10-mar.md"
WRITTEN_ASK = "an email to the operations team on intake form submit"
SPOKEN_ASK = "a search over old records"


def test_a_requirements_document_read_by_a_discarded_run_does_not_count_as_read(
    tmp_path: Path,
) -> None:
    """A discarded run's requirements document never reached the register.

    Claiming it was read would let a later row say that document is silent
    about the ask — an absence backed by evidence nobody ever added.
    """
    written_down = _the_cell_a_later_run_writes(tmp_path)

    assert written_down == IN_WRITING_NOT_KNOWN_YET


def _the_cell_a_later_run_writes(tmp_path: Path) -> str:
    script_path = tmp_path / "script.json"
    with temporary_project_folder("discarded-requirements") as (folder, folder_path):
        written_quote = write_meeting_note(folder, REQUIREMENTS_FILE, WRITTEN_ASK)
        waiting = tmp_path / "not-yet-read"
        waiting.mkdir()
        spoken_quote = write_meeting_note(waiting, MEETING_FILE, SPOKEN_ASK)
        write_script(
            script_path,
            {
                extract_marker(REQUIREMENTS_FILE): requirement_extraction_answer(
                    WRITTEN_ASK, written_quote, CLIENT_REQUIREMENTS_DOCUMENT
                ),
                extract_marker(MEETING_FILE): extraction_answer(
                    SPOKEN_ASK, spoken_quote
                ),
                match_marker(): match_answer(1),
                examine_marker(): no_findings_answer(),
            },
        )
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
                        "/projects", json={"source_folder_path": folder_path}
                    ).json()["project_id"]
                    discarded = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    wait_for_run_status(client, discarded, "needs review")
                    client.post(
                        f"/runs/{discarded}/finish-review",
                        json={"add_to_register": False},
                    ).raise_for_status()
                    wait_for_run_status(client, discarded, "discarded")

                    # Out of the folder, so the next run reads the meeting note
                    # alone: what is under test is whether the discarded read
                    # still counts, not what a second read of it would do.
                    (folder / REQUIREMENTS_FILE).unlink()
                    shutil.copy(waiting / MEETING_FILE, folder / MEETING_FILE)

                    added = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    wait_for_run_status(client, added, "needs review")
                    approve_every_decision_and_finish_review(client, added)
                    wait_for_run_status(client, added, "done")
                    register = client.get(
                        f"/projects/{project_id}/register"
                    ).json()
            finally:
                application.stop()

    return register["rows"][0]["cells"][IN_WRITING]
