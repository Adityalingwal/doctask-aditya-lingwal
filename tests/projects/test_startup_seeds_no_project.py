from __future__ import annotations

from pathlib import Path

from tests.runs.application import ApplicationProcess, temporary_database, write_script


# Never-do test for handoff/brief-helpline-ai-corpus.md: the application must
# never invent a project the operator did not create. Written and run against
# `main` at `f6ca05d` before the demo seed was deleted, per that brief's
# protocol.


def _application(database_url: str, tmp_path: Path) -> ApplicationProcess:
    # No run starts in this test, but `build_scripted_client` still reads
    # this file at startup, and a missing file crashes the application
    # before `/health` ever answers.
    script_path = tmp_path / "script.json"
    write_script(script_path, {})
    return ApplicationProcess(
        database_url=database_url,
        script_path=script_path,
        call_log_path=tmp_path / "model-calls.jsonl",
    )


def test_startup_creates_no_project_of_its_own(tmp_path: Path) -> None:
    with temporary_database() as database_url:
        application = _application(database_url, tmp_path)
        application.start()
        try:
            with application.client() as client:
                listed = client.get("/projects")
        finally:
            application.stop()

        assert listed.status_code == 200
        assert listed.json()["projects"] == []
