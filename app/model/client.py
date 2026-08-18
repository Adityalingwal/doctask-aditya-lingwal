from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.model.scripted_client import (
    CALL_LOG_PATH_ENVIRONMENT_VARIABLE,
    DELAY_ENVIRONMENT_VARIABLE,
    SCRIPT_PATH_ENVIRONMENT_VARIABLE,
    ScriptedChatModel,
    build_scripted_client,
)


MODEL_CLIENT_ENVIRONMENT_VARIABLE = "MODEL_CLIENT"
API_KEY_ENVIRONMENT_VARIABLE = "OPENROUTER_API_KEY"
OPENROUTER_CLIENT = "openrouter"
SCRIPTED_CLIENT = "scripted"
DEFAULT_DELAY_SECONDS = 0.0
REASONING_EFFORT_SETTING = "reasoning_effort"


def build_model_client(
    model_config_path: Path,
    environment: Mapping[str, str],
) -> BaseChatModel:
    """Construct the one model client Extract and Match are handed."""
    requested_client = environment.get(
        MODEL_CLIENT_ENVIRONMENT_VARIABLE,
        OPENROUTER_CLIENT,
    )
    if requested_client == SCRIPTED_CLIENT:
        return _build_scripted_client_from_environment(environment)
    if requested_client != OPENROUTER_CLIENT:
        raise RuntimeError(
            f"{MODEL_CLIENT_ENVIRONMENT_VARIABLE} is set to "
            f"'{requested_client}' — set it to '{OPENROUTER_CLIENT}' for real "
            f"runs or '{SCRIPTED_CLIENT}' for the automated tests."
        )
    return _build_openrouter_client(model_config_path, environment)


def _build_openrouter_client(
    model_config_path: Path,
    environment: Mapping[str, str],
) -> ChatOpenAI:
    model_config = _read_model_config(model_config_path)
    api_key = environment.get(API_KEY_ENVIRONMENT_VARIABLE, "")
    if not api_key:
        raise RuntimeError(
            "The OpenRouter key is missing. Add it to your environment "
            "variables."
        )
    call_settings = model_config["call"]
    return ChatOpenAI(
        model=model_config["model_id"],
        base_url=model_config["base_url"],
        api_key=api_key,
        timeout=float(call_settings["timeout_seconds"]),
        max_retries=int(call_settings["attempts"]) - 1,
        # Absent for a model that has no reasoning setting to give.
        reasoning_effort=call_settings.get(REASONING_EFFORT_SETTING),
    )


def _build_scripted_client_from_environment(
    environment: Mapping[str, str],
) -> ScriptedChatModel:
    script_path = environment.get(SCRIPT_PATH_ENVIRONMENT_VARIABLE)
    if not script_path:
        raise RuntimeError(
            f"{MODEL_CLIENT_ENVIRONMENT_VARIABLE} is '{SCRIPTED_CLIENT}' but "
            f"{SCRIPT_PATH_ENVIRONMENT_VARIABLE} is not set — point it at a "
            "scripted-answer file or use the OpenRouter client."
        )
    call_log_path = environment.get(CALL_LOG_PATH_ENVIRONMENT_VARIABLE)
    return build_scripted_client(
        Path(script_path),
        Path(call_log_path) if call_log_path else None,
        float(
            environment.get(DELAY_ENVIRONMENT_VARIABLE, DEFAULT_DELAY_SECONDS)
        ),
    )


def _read_model_config(model_config_path: Path) -> dict[str, Any]:
    try:
        model_config = yaml.safe_load(
            model_config_path.read_text(encoding="utf-8")
        )
    except FileNotFoundError as error:
        raise RuntimeError(
            f"{model_config_path} is missing — restore config/model.yaml "
            "before starting a run."
        ) from error
    except yaml.YAMLError as error:
        raise RuntimeError(
            f"{model_config_path} is not valid YAML — fix its YAML syntax "
            "before starting a run."
        ) from error

    required_keys = ("model_id", "base_url", "call")
    missing_keys = [key for key in required_keys if key not in model_config]
    if missing_keys:
        raise RuntimeError(
            f"{model_config_path} is missing {', '.join(missing_keys)} — add "
            "the missing keys before starting a run."
        )
    return model_config
