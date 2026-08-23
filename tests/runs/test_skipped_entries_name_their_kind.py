from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    match_answer,
    match_marker,
    no_findings_answer,
    several_requirements_answer,
    unrelated_extraction_answer,
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


SCOPE_FILE = "12-march-scope.md"
UNRELATED_FILE = "clinic-staff-leave-policy.md"
TRACED_REQUIREMENT = "an email to the operations team on intake form submit"
DROPPED_REQUIREMENT = "a weekly AI summary of all open tickets"
INVENTED_QUOTE = "the client wants a weekly AI summary of every open ticket"
UNRELATED_ASK = "a window seat on the Tuesday flight"


def test_a_skipped_entry_names_whether_the_file_was_read_before_not_read_or_not_attached(
    tmp_path: Path,
) -> None:
    """Each of the three weights of entry says which one it is, in `kind`.

    A reader scanning the list cannot otherwise tell a file an earlier run had
    already read from a requirement that fell out of the register, so the kind
    is driven through the three paths that really create one: a quote that is
    not in its file, an unrelated document, and a second run over a folder
    nobody touched. Each sentence is asserted whole, because the screen prints
    it and writes none of it.
    """
    with temporary_project_folder("kind-per-entry") as (source_folder, folder_path):
        traced_quote = write_meeting_note(
            source_folder, SCOPE_FILE, TRACED_REQUIREMENT
        )
        write_meeting_note(source_folder, UNRELATED_FILE, UNRELATED_ASK)
        script_path = tmp_path / "script.json"
        write_script(
            script_path,
            {
                extract_marker(SCOPE_FILE): several_requirements_answer(
                    [
                        (TRACED_REQUIREMENT, traced_quote),
                        (DROPPED_REQUIREMENT, INVENTED_QUOTE),
                    ],
                    "meeting notes",
                ),
                extract_marker(UNRELATED_FILE): unrelated_extraction_answer(),
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

                    first_run = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    wait_for_run_status(client, first_run, "needs review")
                    approve_every_decision_and_finish_review(client, first_run)
                    exported = wait_for_run_status(client, first_run, "done")

                    second_run = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    ended = wait_for_run_status(client, second_run, "no changes")
            finally:
                application.stop()

    not_attached = _entries_of_kind(exported, "not attached")
    assert [entry["file"] for entry in not_attached] == [SCOPE_FILE]
    assert not_attached[0]["summary"] == DROPPED_REQUIREMENT
    # The words were never in the file, so there is no place to name and the
    # reason names the file instead (S12).
    assert not_attached[0]["source_line"] is None
    assert not_attached[0]["reason"] == (
        f"The model said this comes from {SCOPE_FILE}, but those words are "
        "not in the file."
    )

    not_read = _entries_of_kind(exported, "not read")
    assert [entry["file"] for entry in not_read] == [UNRELATED_FILE]
    assert not_read[0]["reason"] == (
        "This document is not related to this client or project."
    )

    read_before = _entries_of_kind(ended, "read before")
    assert sorted(entry["file"] for entry in read_before) == sorted(
        [SCOPE_FILE, UNRELATED_FILE]
    )
    # The screen prints `<file> — <reason>`, so the reason never repeats the
    # file name it sits beside.
    assert read_before[0]["reason"] == "unchanged since it was read."
    # Nothing the second run recorded is anything but a file it had read.
    assert [entry["kind"] for entry in ended["skipped"]] == ["read before"] * 2
    assert ended["ended_early_reason"] == (
        "2 files were skipped. See the Skipped tab for why."
    )


def _entries_of_kind(run: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    return [entry for entry in run["skipped"] if entry["kind"] == kind]
