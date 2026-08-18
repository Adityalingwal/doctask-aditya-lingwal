from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.model.client import (
    API_KEY_ENVIRONMENT_VARIABLE,
    MODEL_CLIENT_ENVIRONMENT_VARIABLE,
    SCRIPTED_CLIENT,
    build_model_client,
)
from app.model.scripted_client import (
    CALL_LOG_PATH_ENVIRONMENT_VARIABLE,
    SCRIPT_PATH_ENVIRONMENT_VARIABLE,
)
from tests.runs.application import PROJECT_ROOT


MODEL_CONFIG_PATH = PROJECT_ROOT / "config" / "model.yaml"


def _write_script(tmp_path: Path) -> Path:
    script_path = tmp_path / "script.json"
    script_path.write_text(
        json.dumps(
            [
                {"when_prompt_contains": "notes-a.md", "answer": "answer for a"},
                {"when_prompt_contains": "notes-b.md", "answer": "answer for b"},
            ]
        ),
        encoding="utf-8",
    )
    return script_path


def test_scripted_client_answers_by_marker_and_records_every_call(
    tmp_path: Path,
) -> None:
    call_log_path = tmp_path / "calls.jsonl"
    client = build_model_client(
        MODEL_CONFIG_PATH,
        {
            MODEL_CLIENT_ENVIRONMENT_VARIABLE: SCRIPTED_CLIENT,
            SCRIPT_PATH_ENVIRONMENT_VARIABLE: str(_write_script(tmp_path)),
            CALL_LOG_PATH_ENVIRONMENT_VARIABLE: str(call_log_path),
        },
    )

    second = client.invoke("please read notes-b.md")
    first = client.invoke("please read notes-a.md")

    assert second.content == "answer for b"
    assert first.content == "answer for a"
    recorded_markers = [
        json.loads(line)["marker"]
        for line in call_log_path.read_text(encoding="utf-8").splitlines()
    ]
    assert recorded_markers == ["notes-b.md", "notes-a.md"]


def test_scripted_client_refuses_a_prompt_it_has_no_answer_for(
    tmp_path: Path,
) -> None:
    client = build_model_client(
        MODEL_CONFIG_PATH,
        {
            MODEL_CLIENT_ENVIRONMENT_VARIABLE: SCRIPTED_CLIENT,
            SCRIPT_PATH_ENVIRONMENT_VARIABLE: str(_write_script(tmp_path)),
        },
    )

    with pytest.raises(RuntimeError) as refusal:
        client.invoke("please read notes-c.md")

    assert "notes-a.md" in str(refusal.value)
    assert "Add the missing marker" in str(refusal.value)


def test_missing_api_key_names_the_cause_and_the_fix() -> None:
    with pytest.raises(RuntimeError) as refusal:
        build_model_client(MODEL_CONFIG_PATH, {API_KEY_ENVIRONMENT_VARIABLE: ""})

    assert str(refusal.value) == (
        "The OpenRouter key is missing. Add it to your environment variables."
    )


def test_unknown_model_client_names_both_supported_clients() -> None:
    with pytest.raises(RuntimeError) as refusal:
        build_model_client(
            MODEL_CONFIG_PATH,
            {MODEL_CLIENT_ENVIRONMENT_VARIABLE: "ollama"},
        )

    assert "openrouter" in str(refusal.value)
    assert SCRIPTED_CLIENT in str(refusal.value)


def test_the_client_asks_for_the_reasoning_effort_the_configuration_names(
    tmp_path: Path,
) -> None:
    """A reasoning model's effort is a configuration value, not a code change.

    Trading answer quality against cost is exactly the kind of knob an
    evaluator changes without touching code, so it lives in `config/model.yaml`
    beside the model id.
    """
    configured = tmp_path / "model.yaml"
    configured.write_text(
        "provider: openrouter\n"
        "model_id: openai/gpt-5.6-terra\n"
        "base_url: https://openrouter.ai/api/v1\n"
        "call:\n"
        "  attempts: 2\n"
        "  timeout_seconds: 120\n"
        "  reasoning_effort: high\n",
        encoding="utf-8",
    )

    client = build_model_client(configured, {API_KEY_ENVIRONMENT_VARIABLE: "test-key"})

    assert client.reasoning_effort == "high"
    assert client.model_name == "openai/gpt-5.6-terra"


def test_a_configuration_naming_no_reasoning_effort_sends_none(
    tmp_path: Path,
) -> None:
    """A model with no reasoning setting must not be sent an effort it cannot
    take — the key is optional, and its absence means "do not ask"."""
    configured = tmp_path / "model.yaml"
    configured.write_text(
        "provider: openrouter\n"
        "model_id: openai/gpt-4.1\n"
        "base_url: https://openrouter.ai/api/v1\n"
        "call:\n"
        "  attempts: 2\n"
        "  timeout_seconds: 120\n",
        encoding="utf-8",
    )

    client = build_model_client(configured, {API_KEY_ENVIRONMENT_VARIABLE: "test-key"})

    assert client.reasoning_effort is None
