from __future__ import annotations

from typing import NamedTuple

from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import BaseMessage


class ReportedUsage(NamedTuple):
    """The tokens the provider said one call spent, or nothing where it said none."""

    prompt_tokens: int | None
    completion_tokens: int | None


class ModelAnswer(NamedTuple):
    text: str
    usage: ReportedUsage


NO_USAGE_REPORTED = ReportedUsage(None, None)


async def call_the_model(
    model_client: BaseChatModel,
    prompt: LanguageModelInput,
) -> ModelAnswer:
    """Make one model call and report what the provider said it spent.

    Every stage calls the model through here, so a token count is read off the
    reply in one place rather than in each node that happens to make a call.
    """
    reply = await model_client.ainvoke(prompt)
    return ModelAnswer(str(reply.content), _reported_usage(reply))


def _reported_usage(reply: BaseMessage) -> ReportedUsage:
    """What the reply reported, never a zero standing in for an absent count."""
    reported = getattr(reply, "usage_metadata", None)
    if not reported:
        return NO_USAGE_REPORTED
    prompt_tokens = reported.get("input_tokens")
    completion_tokens = reported.get("output_tokens")
    if prompt_tokens is None or completion_tokens is None:
        return NO_USAGE_REPORTED
    return ReportedUsage(int(prompt_tokens), int(completion_tokens))
