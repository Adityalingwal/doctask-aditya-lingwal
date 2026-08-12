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


MODEL_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "model.yaml"


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

    assert API_KEY_ENVIRONMENT_VARIABLE in str(refusal.value)
    assert ".env.example" in str(refusal.value)


def test_unknown_model_client_names_both_supported_clients() -> None:
    with pytest.raises(RuntimeError) as refusal:
        build_model_client(
            MODEL_CONFIG_PATH,
            {MODEL_CLIENT_ENVIRONMENT_VARIABLE: "ollama"},
        )

    assert "openrouter" in str(refusal.value)
    assert SCRIPTED_CLIENT in str(refusal.value)
