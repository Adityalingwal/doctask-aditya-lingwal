from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, NamedTuple

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
RATES_KEY = "rates_usd_per_token"
PROMPT_RATE_KEY = "prompt"
COMPLETION_RATE_KEY = "completion"


class CostRates(NamedTuple):
    """The per-token rates an estimate multiplies, or why there are none."""

    prompt_usd_per_token: Decimal | None
    completion_usd_per_token: Decimal | None
    missing_reason: str | None


def read_cost_rates(model_config_path: Path) -> CostRates:
    """The configured rates a run estimates its cost with.

    A rate that is missing or unusable is reported rather than replaced: a run
    that assumed one would present a made-up figure as an estimate.
    """
    model_config = _read_model_config(model_config_path)
    rates = model_config.get(RATES_KEY)
    if not isinstance(rates, dict):
        return _rates_missing(
            model_config_path,
            model_config["model_id"],
            f"it has no {RATES_KEY} block",
        )
    prompt_rate = _rate(rates.get(PROMPT_RATE_KEY))
    completion_rate = _rate(rates.get(COMPLETION_RATE_KEY))
    unusable = [
        name
        for name, rate in (
            (PROMPT_RATE_KEY, prompt_rate),
            (COMPLETION_RATE_KEY, completion_rate),
        )
        if rate is None
    ]
    if unusable:
        return _rates_missing(
            model_config_path,
            model_config["model_id"],
            f"{RATES_KEY}.{' and '.join(unusable)} is missing or is not a number",
        )
    return CostRates(prompt_rate, completion_rate, None)


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
            f"{API_KEY_ENVIRONMENT_VARIABLE} is empty — copy .env.example to "
            ".env and put an OpenRouter API key in it, then start the run "
            "again."
        )
    call_settings = model_config["call"]
    return ChatOpenAI(
        model=model_config["model_id"],
        base_url=model_config["base_url"],
        api_key=api_key,
        timeout=float(call_settings["timeout_seconds"]),
        max_retries=int(call_settings["attempts"]) - 1,
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


def _rate(configured: Any) -> Decimal | None:
    if isinstance(configured, bool) or not isinstance(configured, (int, float, str)):
        return None
    try:
        rate = Decimal(str(configured))
    except InvalidOperation:
        return None
    return rate if rate >= 0 else None


def _rates_missing(
    model_config_path: Path,
    model_id: str,
    what_is_wrong: str,
) -> CostRates:
    return CostRates(
        None,
        None,
        f"no per-token rate is configured for model '{model_id}': "
        f"{model_config_path} — {what_is_wrong}. Add the rates your provider "
        "charges and start another run to have one estimated.",
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
