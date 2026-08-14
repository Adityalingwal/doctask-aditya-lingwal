from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine, text

from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    temporary_database,
    wait_for_run_status,
    write_script,
)
from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    extraction_answer,
    match_answer,
    match_marker,
    no_findings_answer,
    write_meeting_note,
)


ORDINARY_FILE = "meeting-note.md"
INVENTED_TYPE_FILE = "sprint-retro.md"
HANDOVER_FILE = "handover-summary.md"
ORDINARY_REQUIREMENT = "an email to the operations team on intake form submit"
RETRO_REQUIREMENT = "a longer stand-up on Mondays"
HANDOVER_REQUIREMENT = "the records list page handed to the client's own team"
INVENTED_TYPE = "sprint retrospective"
RELATED_ADDITIONAL = "related additional document"


def test_a_document_type_outside_the_declared_set_is_skipped_and_the_run_continues(
    tmp_path: Path,
) -> None:
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    ordinary_quote = write_meeting_note(
        source_folder, ORDINARY_FILE, ORDINARY_REQUIREMENT
    )
    retro_quote = write_meeting_note(
        source_folder, INVENTED_TYPE_FILE, RETRO_REQUIREMENT
    )
    script_path = tmp_path / "script.json"
    write_script(
        script_path,
        {
            extract_marker(ORDINARY_FILE): extraction_answer(
                ORDINARY_REQUIREMENT, ordinary_quote
            ),
            extract_marker(INVENTED_TYPE_FILE): extraction_answer(
                RETRO_REQUIREMENT, retro_quote
            )
            | {"document_type": INVENTED_TYPE},
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
                    "/projects",
                    json={
                        "name": "Intake portal with an invented type",
                        "source_folder_path": str(source_folder),
                    },
                ).json()["project_id"]
                run_id = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                wait_for_run_status(client, run_id, "waiting for review")
                approve_every_decision_and_finish_review(client, run_id)
                finished = wait_for_run_status(client, run_id, "done")
                export = client.get(f"/runs/{run_id}/export").json()
        finally:
            application.stop()

    skipped = [
        entry
        for entry in finished["skipped"]
        if entry.get("file") == INVENTED_TYPE_FILE
    ]
    assert len(skipped) == 1
    assert "document type not recognised" in skipped[0]["reason"]
    assert INVENTED_TYPE in skipped[0]["reason"]
    # The invented type never became a row, and the run it shared a batch with
    # still exported the register.
    assert [row["cells"]["what_was_asked"] for row in export["rows"]] == [
        ORDINARY_REQUIREMENT
    ]


def test_a_related_additional_document_is_labelled_but_never_creates_a_row_alone(
    tmp_path: Path,
) -> None:
    source_folder = tmp_path / "intake-portal"
    source_folder.mkdir()
    quote = write_meeting_note(source_folder, HANDOVER_FILE, HANDOVER_REQUIREMENT)
    script_path = tmp_path / "script.json"
    write_script(
        script_path,
        {
            extract_marker(HANDOVER_FILE): extraction_answer(
                HANDOVER_REQUIREMENT, quote
            )
            | {"document_type": RELATED_ADDITIONAL},
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
                    "/projects",
                    json={
                        "name": "Intake portal with a handover summary",
                        "source_folder_path": str(source_folder),
                    },
                ).json()["project_id"]
                run_id = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                ended = wait_for_run_status(client, run_id, "ended without changes")
        finally:
            application.stop()

        engine = create_engine(database_url)
        with engine.connect() as connection:
            stored = connection.execute(
                text("SELECT extraction FROM documents WHERE source_path = :path"),
                {"path": HANDOVER_FILE},
            ).scalar_one()
        engine.dispose()

    extraction = stored if isinstance(stored, dict) else json.loads(stored)
    # Processed and labelled, and its evidence kept for the slices that read it;
    # what it must not do is put a row in the register by itself.
    assert extraction["document_type"] == RELATED_ADDITIONAL
    assert len(extraction["requirements"]) == 1
    assert "no document in this batch reported a requirement" in (
        ended["ended_early_reason"]
    )
    assert ended["exported"] is False
