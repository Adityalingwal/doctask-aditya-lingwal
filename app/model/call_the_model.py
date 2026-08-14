from __future__ import annotations

from langchain_core.language_models import BaseChatModel, LanguageModelInput


async def call_the_model(
    model_client: BaseChatModel,
    prompt: LanguageModelInput,
) -> str:
    """Make one model call and return the text of its reply.

    Every stage calls the model through here, so a reply is read the same way
    in one place rather than in each node that happens to make a call.
    """
    reply = await model_client.ainvoke(prompt)
    return str(reply.content)
