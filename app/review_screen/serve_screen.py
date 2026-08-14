from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, status
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles


BUILD_COMMAND = "npm --prefix ui ci && npm --prefix ui run build"


def serve_review_screen(application: FastAPI, built_screen: Path, path: str) -> None:
    """Serve the built review screen, or answer with the command that builds it.

    The screen is built by Node, which this image does not carry, so a checkout
    that has not run the build must be told so rather than answer 404 and leave
    a reviewer guessing whether the route exists at all.
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
            f"repository root, then reload {path}/.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
