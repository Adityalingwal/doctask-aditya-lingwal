from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine, text

from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)
from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    extraction_answer,
    handover_answer,
    match_answer,
    match_marker,
    no_findings_answer,
    feedback_extraction_answer,
    unrelated_extraction_answer,
    write_meeting_note,
)


ORDINARY_FILE = "meeting-note.md"
INVENTED_TYPE_FILE = "sprint-retro.md"
HANDOVER_FILE = "handover-summary.md"
TESTING_FILE = "testing-feedback.md"
UNRELATED_FILE = "clinic-leave-policy.md"
ORDINARY_REQUIREMENT = "an email to the operations team on intake form submit"
RETRO_REQUIREMENT = "a longer stand-up on Mondays"
HANDOVER_REQUIREMENT = "the records list page handed to the client's own team"
INVENTED_TYPE = "sprint retrospective"
HANDOVER_SUMMARY = "handover summary"


def test_a_document_type_outside_the_declared_set_is_not_read_and_the_run_continues(
    tmp_path: Path,
) -> None:
    with temporary_project_folder("invented-type") as (source_folder, source_folder_path):
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
                        json={"source_folder_path": source_folder_path},
                    ).json()["project_id"]
                    run_id = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    wait_for_run_status(client, run_id, "needs review")
                    approve_every_decision_and_finish_review(client, run_id)
                    finished = wait_for_run_status(client, run_id, "done")
                    export = client.get(f"/projects/{project_id}/register").json()
            finally:
                application.stop()

    not_used = [
        entry
        for entry in finished["not_used"]
        if entry.get("file") == INVENTED_TYPE_FILE
    ]
    assert len(not_used) == 1
    assert not_used[0]["reason"] == "The model gave an unknown document type."
    # The invented type never became a row, and the run it shared a batch with
    # still exported the register.
    assert [row["cells"]["what_was_asked"] for row in export["rows"]] == [
        ORDINARY_REQUIREMENT
    ]


def test_a_document_type_named_handover_summary_may_fill_delivery_evidence(
    tmp_path: Path,
) -> None:
    with temporary_project_folder("handover-summary") as (source_folder, source_folder_path):
        quote = write_meeting_note(source_folder, HANDOVER_FILE, HANDOVER_REQUIREMENT)
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                extract_marker(HANDOVER_FILE): handover_answer(
                    [(HANDOVER_REQUIREMENT, quote)]
                ),
            },
        )
        ended, stored = _one_run_over(
            tmp_path, source_folder_path, script_path, HANDOVER_FILE
        )

    # Processed and labelled, and its delivery evidence kept for the step that
    # moves rows; what it must not do is put a row in the register by itself.
    # It is the only type allowed to fill delivery_evidence, which is why the
    # type is named after what it is rather than after what it is not.
    assert stored["document_type"] == HANDOVER_SUMMARY
    assert stored["requirements"] == []
    assert len(stored["delivery_evidence"]) == 1
    assert ended["exported"] is False


def test_an_unrelated_document_returns_no_requirements(tmp_path: Path) -> None:
    with temporary_project_folder("unrelated") as (source_folder, source_folder_path):
        write_meeting_note(source_folder, UNRELATED_FILE, ORDINARY_REQUIREMENT)
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {extract_marker(UNRELATED_FILE): unrelated_extraction_answer()},
        )
        ended, stored = _one_run_over(
            tmp_path, source_folder_path, script_path, UNRELATED_FILE
        )

    assert stored["document_type"] == "unrelated"
    assert stored["requirements"] == []
    assert ended["exported"] is False


def test_a_testing_feedback_document_never_creates_a_register_row(
    tmp_path: Path,
) -> None:
    with temporary_project_folder("testing-only") as (source_folder, source_folder_path):
        quote = write_meeting_note(source_folder, TESTING_FILE, ORDINARY_REQUIREMENT)
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                extract_marker(TESTING_FILE): feedback_extraction_answer(
                    [("The email notification reaches the team.", "Passed", quote)]
                ),
                examine_marker(): no_findings_answer(),
            },
        )
        stored, committed_rows = _one_run_added_to_the_register(
            tmp_path, source_folder_path, script_path, TESTING_FILE
        )

    # Testing feedback says what testing found; it never states a new ask, so
    # there is nothing here for the register to take as a row. The run still
    # goes to a person, because reading it is what lets every row say whether
    # testing has spoken about it.
    assert stored["requirements"] == []
    assert len(stored["testing_observations"]) == 1
    assert committed_rows == 0


def test_a_filled_list_the_type_may_not_use_leaves_that_document_unread(
    tmp_path: Path,
) -> None:
    with temporary_project_folder("wrong-list") as (source_folder, source_folder_path):
        ordinary_quote = write_meeting_note(
            source_folder, ORDINARY_FILE, ORDINARY_REQUIREMENT
        )
        stray_quote = write_meeting_note(
            source_folder, TESTING_FILE, RETRO_REQUIREMENT
        )
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                extract_marker(ORDINARY_FILE): extraction_answer(
                    ORDINARY_REQUIREMENT, ordinary_quote
                ),
                # Testing feedback may not state a new ask. Answering with one
                # is a wrong answer, not something to quietly empty.
                extract_marker(TESTING_FILE): feedback_extraction_answer([])
                | {"requirements": [{"summary": RETRO_REQUIREMENT, "quote": stray_quote}]},
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
                        json={"source_folder_path": source_folder_path},
                    ).json()["project_id"]
                    run_id = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    wait_for_run_status(client, run_id, "needs review")
                    approve_every_decision_and_finish_review(client, run_id)
                    finished = wait_for_run_status(client, run_id, "done")
                    export = client.get(f"/projects/{project_id}/register").json()
            finally:
                application.stop()

    not_used = [
        entry for entry in finished["not_used"] if entry.get("file") == TESTING_FILE
    ]
    assert len(not_used) == 1
    # The reason a person reads names what came back, not merely that
    # something did: without the type and the list there is nothing to act on.
    assert not_used[0]["reason"] == (
        "The model read this as testing feedback and reported requirements, "
        "which that kind of document may not report."
    )
    # The run did not fail, the list was not quietly emptied into the register,
    # and the other document in the batch still became its row.
    assert [row["cells"]["what_was_asked"] for row in export["rows"]] == [
        ORDINARY_REQUIREMENT
    ]


def _one_run_added_to_the_register(
    tmp_path: Path,
    source_folder_path: str,
    script_path: Path,
    source_file: str,
) -> tuple[dict, int]:
    """One run taken through Review to Commit, and what it left behind."""
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
                    "/projects", json={"source_folder_path": source_folder_path}
                ).json()["project_id"]
                run_id = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                wait_for_run_status(client, run_id, "needs review")
                approve_every_decision_and_finish_review(client, run_id)
                wait_for_run_status(client, run_id, "done")
        finally:
            application.stop()

        engine = create_engine(database_url)
        with engine.connect() as connection:
            stored = connection.execute(
                text("SELECT extraction FROM documents WHERE source_path = :path"),
                {"path": source_file},
            ).scalar_one()
            committed_rows = connection.execute(
                text(
                    "SELECT count(*) FROM register_rows WHERE is_committed"
                )
            ).scalar_one()
        engine.dispose()

    return (
        stored if isinstance(stored, dict) else json.loads(stored),
        committed_rows,
    )


def _one_run_over(
    tmp_path: Path,
    source_folder_path: str,
    script_path: Path,
    source_file: str,
) -> tuple[dict, dict]:
    """One run that reaches no review, and the extraction it stored."""
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
                    "/projects", json={"source_folder_path": source_folder_path}
                ).json()["project_id"]
                run_id = client.post(
                    "/runs", json={"project_id": project_id}
                ).json()["run_id"]
                ended = wait_for_run_status(client, run_id, "no changes")
        finally:
            application.stop()

        engine = create_engine(database_url)
        with engine.connect() as connection:
            stored = connection.execute(
                text("SELECT extraction FROM documents WHERE source_path = :path"),
                {"path": source_file},
            ).scalar_one()
        engine.dispose()

    return ended, stored if isinstance(stored, dict) else json.loads(stored)
