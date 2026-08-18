from __future__ import annotations

from pathlib import Path

from tests.runs.application import PROJECT_ROOT


def test_the_app_service_forwards_the_model_key_it_is_started_with() -> None:
    """Never-do: the documented setup must never leave the key outside the
    container.

    `README.md` tells an evaluator to put `OPENROUTER_API_KEY` in `.env` and
    run `docker compose up`. Compose reads `.env` for its own substitution but
    passes nothing into a service it is not told to pass, so without this the
    key is present on the host, absent inside the container, and every run
    fails at the model boundary on a fresh clone that followed the README.
    """
    app_service = _service_block(
        _read(PROJECT_ROOT / "docker-compose.yml"), "app"
    )
    assert "${OPENROUTER_API_KEY" in app_service, (
        "the app service does not forward OPENROUTER_API_KEY — add it to the "
        "service's environment so the key in .env reaches the container."
    )
    assert "${OPENROUTER_API_KEY:?" not in app_service, (
        "the app service demands OPENROUTER_API_KEY before it will start, but "
        "the application is documented to start without one and refuse runs "
        "with a reason — forward it with an empty default instead."
    )


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _service_block(compose_text: str, service: str) -> str:
    """The lines of one top-level Compose service, by indentation."""
    lines = compose_text.splitlines()
    start = next(
        index for index, line in enumerate(lines) if line.strip() == f"{service}:"
    )
    end = start + 1
    while end < len(lines) and (lines[end].startswith("  ") or not lines[end].strip()):
        end += 1
    return "\n".join(lines[start:end])
