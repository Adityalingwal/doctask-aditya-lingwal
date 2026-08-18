from __future__ import annotations

import re

from langchain_core.language_models import BaseChatModel, LanguageModelInput
from pydantic import BaseModel

from app.model.answer_schema import strict_answer_format


# Every C0 control character, written either as itself or as the JSON escape
# the model sends it as. A newline, tab and carriage return are ordinary text.
_CONTROL_CHARACTER = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]|\\u00(?:0[0-8bcef]|1[0-9a-f])", re.IGNORECASE)


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
    # A model that is sent an em dash has been seen returning U+0014 in its
    # own sentence, which then reaches a cell and the screen.
    return _CONTROL_CHARACTER.sub("", str(reply.content))
