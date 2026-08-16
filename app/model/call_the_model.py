from __future__ import annotations

from langchain_core.language_models import BaseChatModel, LanguageModelInput
from pydantic import BaseModel

from app.model.answer_schema import strict_answer_format


async def call_the_model(
    model_client: BaseChatModel,
    prompt: LanguageModelInput,
    answer_model: type[BaseModel],
) -> str:
    """Make one model call in the shape of `answer_model` and return its reply.

    Every stage calls the model through here, so one place decides both how the
    answer's shape is asked for and how a reply is read.
    """
    reply = await model_client.ainvoke(
        prompt, response_format=strict_answer_format(answer_model)
    )
    return str(reply.content)
