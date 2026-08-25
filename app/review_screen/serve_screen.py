from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, status
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles


BUILD_COMMAND = "npm --prefix ui ci && npm --prefix ui run build"


def serve_review_screen(application: FastAPI, built_screen: Path, path: str) -> None:
    """Serve the built review screen, or answer with the command that builds it.

    The production image already carries the screen built by its Node stage.
    A direct host checkout may still have no local build, so tell that developer
    what to run rather than answer 404 and leave the route ambiguous.
    """
    if (built_screen / "index.html").is_file():
        application.mount(
            path,
            StaticFiles(directory=built_screen, html=True),
            name="review-screen",
        )
        return

    @application.get(path, response_class=PlainTextResponse)
    async def unbuilt_review_screen() -> PlainTextResponse:
        return PlainTextResponse(
            f"the review screen is not built — run `{BUILD_COMMAND}` from the "
            "repository root, then restart the application (`docker compose "
            f"up --build`) and open {path}/ again. Reloading this page will "
            "not help: whether the screen is served is decided when the "
            "application starts.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
