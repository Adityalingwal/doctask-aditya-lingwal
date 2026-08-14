from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.messages.ai import UsageMetadata
from langchain_core.outputs import ChatGeneration, ChatResult


SCRIPT_PATH_ENVIRONMENT_VARIABLE = "SCRIPTED_MODEL_SCRIPT"
CALL_LOG_PATH_ENVIRONMENT_VARIABLE = "SCRIPTED_MODEL_CALL_LOG"
DELAY_ENVIRONMENT_VARIABLE = "SCRIPTED_MODEL_DELAY_SECONDS"
PROMPT_MARKER_KEY = "when_prompt_contains"
ANSWER_KEY = "answer"
USAGE_KEY = "usage"
PROMPT_TOKENS_KEY = "prompt_tokens"
COMPLETION_TOKENS_KEY = "completion_tokens"
ERROR_KEY = "error"
ERROR_MESSAGE_KEY = "message"
ERROR_STATUS_CODE_KEY = "status_code"


class ScriptedModelFailure(RuntimeError):
    """A call failure a script asked for, carrying the provider's status code.

    The status code is where it sits on the provider SDK's own exceptions, so
    the code that classifies a failure is driven exactly as it is in a run.
    """

    def __init__(self, message: str, status_code: int | None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ScriptedChatModel(GenericFakeChatModel):
    """The key-free model the locked slice 1 test strategy runs against.

    It answers by matching a marker in the prompt rather than by call order, so
    a run that is killed and continued in a second process still gets the right
    answer for whichever call it makes next. Every call is appended to a log
    file so a test can assert which documents the model was actually asked
    about.
    """

    script: list[dict[str, Any]]
    call_log_path: Path | None = None
    delay_seconds: float = 0.0

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        prompt = "\n".join(str(message.content) for message in messages)
        marker, scripted = self._answer_for(prompt)
        self._record_call(marker)
        if self.delay_seconds:
            time.sleep(self.delay_seconds)
        failure = scripted.get(ERROR_KEY)
        if failure is not None:
            raise ScriptedModelFailure(
                failure[ERROR_MESSAGE_KEY],
                failure.get(ERROR_STATUS_CODE_KEY),
            )
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content=scripted[ANSWER_KEY],
                        usage_metadata=_scripted_usage(scripted),
                    )
                )
            ]
        )

    def _answer_for(self, prompt: str) -> tuple[str, dict[str, Any]]:
        for scripted_answer in self.script:
            marker = scripted_answer[PROMPT_MARKER_KEY]
            if marker in prompt:
                return marker, scripted_answer
        markers = ", ".join(entry[PROMPT_MARKER_KEY] for entry in self.script)
        raise RuntimeError(
            "The scripted model has no answer for this call — its prompt matches "
            f"none of the scripted markers ({markers}). Add the missing marker "
            "and answer to the script file."
        )

    def _record_call(self, marker: str) -> None:
        if self.call_log_path is None:
            return
        line = json.dumps(
            {
                "marker": marker,
                "asked_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        # Opened and closed per call so the entry survives a SIGKILL that gives
        # nothing a chance to flush.
        with self.call_log_path.open("a", encoding="utf-8") as call_log:
            call_log.write(f"{line}\n")


def _scripted_usage(scripted: dict[str, Any]) -> UsageMetadata | None:
    """What this scripted call reports having spent, where the script says.

    A script that says nothing reports nothing, which is the shape a provider
    that returns no usage block has: the run must call that unknown, not zero.
    """
    reported = scripted.get(USAGE_KEY)
    if reported is None:
        return None
    prompt_tokens = int(reported[PROMPT_TOKENS_KEY])
    completion_tokens = int(reported[COMPLETION_TOKENS_KEY])
    return UsageMetadata(
        input_tokens=prompt_tokens,
        output_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )


def build_scripted_client(
    script_path: Path,
    call_log_path: Path | None,
    delay_seconds: float,
) -> ScriptedChatModel:
    script = json.loads(script_path.read_text(encoding="utf-8"))
    return ScriptedChatModel(
        messages=iter(()),
        script=script,
        call_log_path=call_log_path,
        delay_seconds=delay_seconds,
    )
