from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.review_screen.serve_screen import BUILD_COMMAND, serve_review_screen


SCREEN_PATH = "/ui"


def test_built_review_screen_is_served_at_its_path(tmp_path: Path) -> None:
    built = tmp_path / "dist"
    built.mkdir()
    (built / "index.html").write_text(
        "<div id='review-screen'></div>",
        encoding="utf-8",
    )
    application = FastAPI()
    serve_review_screen(application, built, SCREEN_PATH)

    answered = TestClient(application).get(f"{SCREEN_PATH}/")

    assert answered.status_code == 200
    assert "review-screen" in answered.text


def test_unbuilt_review_screen_answers_with_the_command_that_builds_it(
    tmp_path: Path,
) -> None:
    application = FastAPI()
    serve_review_screen(application, tmp_path / "dist", SCREEN_PATH)

    answered = TestClient(application).get(SCREEN_PATH)

    assert answered.status_code == 503
    assert BUILD_COMMAND in answered.text
    # Whether the screen is mounted is decided once, at startup, so a build
    # that happens afterwards cannot appear in the running application. Telling
    # the reader to reload would send them round a loop that cannot end.
    assert "restart" in answered.text
    assert "reload" not in answered.text
