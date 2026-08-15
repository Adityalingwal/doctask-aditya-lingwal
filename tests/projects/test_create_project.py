from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text

from tests.interfaces.mcp_client import call_tool
from tests.runs.application import (
    ApplicationProcess,
    temporary_database,
    temporary_project_folder,
    write_script,
)


# Never-do tests for "a folder is a project" (handoff/brief-folder-is-a-project-
# and-register-moves.md, Part 1). Written and run against `main` at `a436393`
# before any implementation, per that brief's protocol.


def _application(database_url: str, tmp_path: Path) -> ApplicationProcess:
    # None of these tests start a run, so the scripted model is never called —
    # but `build_scripted_client` still reads this file at startup, and a
    # missing file crashes the application before `/health` ever answers.
    script_path = tmp_path / "script.json"
    write_script(script_path, {})
    return ApplicationProcess(
        database_url=database_url,
        script_path=script_path,
        call_log_path=tmp_path / "model-calls.jsonl",
    )


def test_two_calls_for_one_folder_return_the_same_project_and_create_nothing(
    tmp_path: Path,
) -> None:
    with temporary_project_folder("same-folder-twice") as (_folder, folder_path):
        with temporary_database() as database_url:
            application = _application(database_url, tmp_path)
            application.start()
            try:
                with application.client() as client:
                    first = client.post(
                        "/projects", json={"source_folder_path": folder_path}
                    )
                    second = client.post(
                        "/projects", json={"source_folder_path": folder_path}
                    )
            finally:
                application.stop()

            assert first.status_code == 201
            assert second.status_code == 201
            assert first.json()["project_id"] == second.json()["project_id"]
            assert first.json()["created"] is True
            assert second.json()["created"] is False

            engine = create_engine(database_url)
            with engine.connect() as connection:
                matching = connection.execute(
                    text(
                        "SELECT count(*) FROM projects WHERE source_folder_path = :path"
                    ),
                    {"path": folder_path},
                ).scalar_one()
            engine.dispose()
            assert matching == 1


def test_a_second_project_over_one_folder_is_refused_by_the_database(
    tmp_path: Path,
) -> None:
    """The real unique constraint, driven directly — not a Python-side check."""
    with temporary_project_folder("constraint-check") as (_folder, folder_path):
        with temporary_database() as database_url:
            engine = create_engine(database_url)
            try:
                with engine.begin() as connection:
                    connection.execute(
                        text(
                            "INSERT INTO projects (id, name, source_folder_path) "
                            "VALUES (:id, :name, :path)"
                        ),
                        {"id": str(uuid4()), "name": "First", "path": folder_path},
                    )
                raised = None
                try:
                    with engine.begin() as connection:
                        connection.execute(
                            text(
                                "INSERT INTO projects (id, name, source_folder_path) "
                                "VALUES (:id, :name, :path)"
                            ),
                            {
                                "id": str(uuid4()),
                                "name": "Second",
                                "path": folder_path,
                            },
                        )
                except Exception as error:  # the database's own IntegrityError
                    raised = error
                assert raised is not None
                assert "unique" in str(raised).lower()

                with engine.connect() as connection:
                    matching = connection.execute(
                        text(
                            "SELECT count(*) FROM projects WHERE source_folder_path = :path"
                        ),
                        {"path": folder_path},
                    ).scalar_one()
                assert matching == 1
            finally:
                engine.dispose()


def test_a_folder_outside_the_projects_root_is_refused(tmp_path: Path) -> None:
    outside = tmp_path / "not-in-the-projects-root"
    outside.mkdir()
    with temporary_project_folder("nested-root") as (folder, folder_path):
        nested = folder / "two-levels-down"
        nested.mkdir()
        with temporary_database() as database_url:
            application = _application(database_url, tmp_path)
            application.start()
            try:
                with application.client() as client:
                    dot_dot = client.post(
                        "/projects",
                        json={"source_folder_path": "sample-projects/../../etc"},
                    )
                    absolute = client.post(
                        "/projects", json={"source_folder_path": str(outside)}
                    )
                    nested_two_deep = client.post(
                        "/projects",
                        json={
                            "source_folder_path": f"{folder_path}/two-levels-down"
                        },
                    )
            finally:
                application.stop()

            for refused, cause in (
                (dot_dot, "'..'"),
                (absolute, "absolute"),
                (nested_two_deep, "directly inside"),
            ):
                assert refused.status_code == 400, refused.text
                detail = refused.json()["detail"]
                assert "sample-projects" in detail
                assert cause in detail or "directly inside" in detail

            engine = create_engine(database_url)
            with engine.connect() as connection:
                stored = connection.execute(
                    text("SELECT source_folder_path FROM projects")
                ).scalars().all()
            engine.dispose()
            assert nested.name not in " ".join(stored)


def test_the_project_name_is_derived_from_the_folder_and_never_supplied(
    tmp_path: Path,
) -> None:
    with temporary_project_folder("northside_dental") as (_folder, folder_path):
        with temporary_database() as database_url:
            application = _application(database_url, tmp_path)
            application.start()
            try:
                with application.client() as client:
                    project_id = client.post(
                        "/projects", json={"source_folder_path": folder_path}
                    ).json()["project_id"]
                    listed = client.get("/projects").json()
            finally:
                application.stop()

            project = next(
                project
                for project in listed["projects"]
                if project["project_id"] == project_id
            )
        # The folder's own name segment ("northside_dental-<suffix>"),
        # dash/underscore split and each word capitalised — never a name a
        # caller supplied, because none was ever sent.
        assert project["name"].startswith("Northside Dental")


def test_the_create_project_tool_and_endpoint_accept_no_name(tmp_path: Path) -> None:
    with temporary_project_folder("no-name-http") as (_folder_a, path_a):
        with temporary_project_folder("no-name-mcp") as (_folder_b, path_b):
            with temporary_database() as database_url:
                application = _application(database_url, tmp_path)
                application.start()
                try:
                    with application.client() as client:
                        over_http = client.post(
                            "/projects", json={"source_folder_path": path_a}
                        )
                    through_mcp = call_tool(
                        application.base_url,
                        "create_project",
                        {"source_folder_path": path_b},
                    )
                finally:
                    application.stop()

                assert over_http.status_code == 201
                assert "project_id" in over_http.json()
                assert through_mcp.refused is False
                assert "project_id" in through_mcp.payload
