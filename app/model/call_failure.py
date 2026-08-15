from __future__ import annotations


CONFIGURATION_FAILURE_FIXES = {
    401: (
        "the model provider refused the API key (HTTP 401) — check the "
        "OpenRouter key in your environment variables"
    ),
    402: (
        "the OpenRouter account has no credit left (HTTP 402) — add credit to "
        "the account"
    ),
    403: (
        "the model provider refused this key for this model (HTTP 403) — use "
        "a key that may, or name a model the key may use in "
        "config/model.yaml"
    ),
    404: (
        "the model named in config/model.yaml does not exist at the provider "
        "(HTTP 404) — correct model_id there"
    ),
}


class ModelConfigurationFailure(RuntimeError):
    """The setup is wrong, so every model call in the run would fail alike."""


class ModelCallFailed(RuntimeError):
    """A model call failed at a stage that has nothing smaller to skip."""


def raise_if_configuration_failure(error: Exception) -> None:
    """Turn a wrong key, an empty account or a wrong model name into a stop.

    Classified by status code and never by the words in the message: a
    provider rewords its responses, and the status code stays what it is.
    """
    fix = CONFIGURATION_FAILURE_FIXES.get(_status_code_of(error))
    if fix is None:
        return
    raise ModelConfigurationFailure(
        f"{fix}. Every call in this run would have failed the same way."
    ) from error


def _status_code_of(error: Exception) -> int | None:
    status_code = getattr(error, "status_code", None)
    if status_code is None:
        status_code = getattr(getattr(error, "response", None), "status_code", None)
    return status_code if isinstance(status_code, int) else None
