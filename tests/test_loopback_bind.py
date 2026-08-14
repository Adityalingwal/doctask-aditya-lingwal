from __future__ import annotations

import re
from pathlib import Path

from tests.runs.application import PROJECT_ROOT


def test_dockerfile_bind_host_defaults_to_loopback_via_app_host() -> None:
    """Never-do: the app must never listen on a non-loopback interface unless
    a deliberate configuration value (APP_HOST) says so.

    A hardcoded `--host 0.0.0.0` binds every interface unconditionally, which
    is exactly what must never happen without a deliberate config value.
    """
    dockerfile = _read(PROJECT_ROOT / "Dockerfile")
    assert "0.0.0.0" not in dockerfile, (
        "Dockerfile hardcodes a non-loopback bind host — the host must come "
        "from APP_HOST, defaulting to 127.0.0.1."
    )
    assert "APP_HOST" in dockerfile, (
        "Dockerfile does not read APP_HOST — the bind host must be "
        "configurable, not fixed at image-build time."
    )
    assert "127.0.0.1" in dockerfile, (
        "Dockerfile has no loopback default — an unset APP_HOST must still "
        "bind loopback only."
    )


def test_compose_publishes_app_port_on_loopback_only() -> None:
    """Never-do: Docker must never publish the app port on every interface.

    Docker Compose publishes on every host interface regardless of what the
    application itself bound inside the container, so the `ports:` mapping
    must itself be loopback-qualified — matching the `db` service.
    """
    compose = _read(PROJECT_ROOT / "docker-compose.yml")
    app_service = _service_block(compose, "app")
    assert '"127.0.0.1:8000:8000"' in app_service, (
        "the app service's ports mapping does not bind 127.0.0.1 — Docker "
        "publishes 8000 on every host interface without it, regardless of "
        "what host the application inside the container bound."
    )
    assert not re.search(r'-\s*"8000:8000"\s*$', app_service, re.MULTILINE), (
        "the app service still has a bare '8000:8000' port mapping, which "
        "publishes on every host interface."
    )
    assert 'APP_HOST' in app_service and '0.0.0.0' in app_service, (
        "the app service does not set APP_HOST=0.0.0.0 — inside the "
        "container the app must bind every interface or the published port "
        "is unreachable."
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
