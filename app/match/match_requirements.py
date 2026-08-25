from __future__ import annotations

import json
from typing import Any, Literal, NoReturn

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.extract.answer import json_object_in
from app.model.call_the_model import call_the_model


NEW_ROW = "new row"
EXISTING_ROW = "existing row"
POSSIBLE_MATCH = "possible match"

# The same three words as a type. Pydantic builds the answer schema out of it,
# so the provider refuses an invented outcome before the reply reaches us. A
# Literal cannot be written in terms of the constants above, which is why the
# words appear twice and a test holds the two copies in step.
Outcome = Literal["new row", "existing row", "possible match"]

MATCH_PROMPT_MARKER = "Match these requirements against the register"
OBSERVATION_PROMPT_MARKER = "Match these observations against the register"
INCOMPLETE_ANSWER_FIX = (
    " Nothing was proposed for the register, because an item Match did not "
    "answer for is not a new row. Start another run so Match is asked "
    "again; if it keeps answering incompletely, name a stronger model in "
    "config/model.yaml."
)

_INSTRUCTIONS = """A small software provider is building something for a client. A register
holds one row per client requirement. You decide, for each requirement found
in this batch of documents, whether it is already accounted for.

Two kinds of candidate exist, and a requirement may match either:

- a register row that already exists, named by its row_number;
- an earlier requirement in this same batch, named by its
  requirement_index. Two documents read together often state one ask —
  a meeting note and the client's written requirements are the usual pair.

Each requirement carries the kind of document it came from, as
document_type — use that word, never a guess from the file name.

Answer exactly one outcome per requirement, using its requirement_index:

- "new row" — nothing above traces this requirement. Leave both
  row_number and same_as_requirement_index null.
- "existing row" — a candidate traces exactly this requirement, and you are
  certain. Name it: row_number for a register row,
  same_as_requirement_index for an earlier requirement in this batch.
  Fill exactly one, never both.
- "possible match" — it may be the same as a candidate, but you are not
  certain. Name it the same way.

A requirement may only be matched against a requirement that comes before it
in the list. Never point forward.

## Never merge when unsure

Wrongly merging two different requirements into one row corrupts the register
silently — a person reading it later has no way to see it happened. Where
there is real doubt, answer "possible match". That is not a fallback for
laziness: it is the correct answer whenever a reasonable person could read
the wording either way.

Example — clearly different, answer "new row":
"Send the appointment reminder by SMS" and "Send the appointment reminder by
email" are two requirements. They share a purpose but ask for two channels,
and both would be expected built.

Example — clearly the same, answer "existing row":
Candidate: "Send a reminder email 24 hours before the appointment."
Requirement: "The reminder emails should go out a day in advance, like we
discussed." One ask, restated in a later document.

Example — genuinely uncertain, answer "possible match":
Candidate: "Clients should be able to reschedule their own appointment
online." Requirement: "Add a way for clients to change their booking time
without calling the clinic." These may be one ask in different words, or the
second may also cover cancelling. Flag it rather than guessing either way.

## You write no sentence

Answer with the outcome and the candidate it names, and nothing else.
Where a person has to decide, the question they read is written from
the register's own rows and this batch's own quotes, not by you.

## Answer every requirement exactly once

You are given a list of requirement_index values. Answer for every one of
them, exactly once each. An outcome for an index you were not given, or a
missing index, makes the whole answer unusable — nothing is proposed for the
register and Match has to run again. Do not pad a skipped requirement with a
guessed outcome, and do not stop early.

Reply with nothing but the structured answer your schema defines."""


_OBSERVATION_INSTRUCTIONS = f"""You decide, for each observation found in this \
batch of documents, which register row it is about.

An observation is something a document says about work the client already \
asked for: what testing found, or what was handed over. It never states a new \
ask, so it never becomes a row of its own — it either belongs to a row that \
already exists, or it belongs to none of them.

Answer one of three outcomes per observation:
- "{NEW_ROW}" — no existing row is what this observation is about.
- "{EXISTING_ROW}" — this observation is about exactly this row; give its \
row_number.
- "{POSSIBLE_MATCH}" — it may be about an existing row but you are not \
certain; give that row_number.

Never attach an observation to a row you are unsure about. Attaching "the \
daily schedule screen shows the wrong day" to a row about email reminders \
puts a false testing verdict on the register, so where there is real doubt \
answer "{POSSIBLE_MATCH}" and a person will decide. An observation about work \
no row traces is answered "{NEW_ROW}"; it is reported to a person rather than \
forced onto the nearest row.

## You write no sentence

Answer with the outcome and the row it names, and nothing else. Where
a person has to decide, the question they read is written from the
register's own row and this batch's own quote, not by you.

Answer for every observation you were sent, exactly once each, and reply with \
nothing but the structured answer your schema defines."""


class MatchOutcome(BaseModel):
    requirement_index: int = Field(
        description="The index of the requirement this answer is about."
    )
    outcome: Outcome = Field(description="One of the three outcomes above.")
    row_number: int | None = Field(
        default=None,
        description=(
            "The register row this requirement matched, or null for a new row."
        ),
    )
    same_as_requirement_index: int | None = Field(
        default=None,
        description=(
            "The earlier requirement in this same batch stating the same ask, "
            "or null when no earlier requirement does."
        ),
    )


class MatchAnswer(BaseModel):
    # Required: a reply without it is a failed Match, not a register in which
    # every requirement quietly became a new row.
    outcomes: list[MatchOutcome]


# Observations get their own model rather than borrowing the requirement one.
# The generated schema is what the model is actually asked for, so a field
# described as "the requirement this answer is about" while the prompt asks
# about observations makes the contract contradict itself.
class ObservationOutcome(BaseModel):
    observation_index: int = Field(
        description="The index of the observation this answer is about."
    )
    outcome: Outcome = Field(description="One of the three outcomes above.")
    row_number: int | None = Field(
        default=None,
        description=(
            "The register row this observation is about, or null when no row "
            "is."
        ),
    )


class ObservationAnswer(BaseModel):
    outcomes: list[ObservationOutcome]


class IncompleteMatchAnswer(RuntimeError):
    """Match answered about a different set of items than it was sent."""


async def match_requirements(
    model_client: BaseChatModel,
    register_rows: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
) -> MatchAnswer:
    answered = await call_the_model(
        model_client, _match_prompt(register_rows, requirements), MatchAnswer
    )
    answer = MatchAnswer.model_validate_json(json_object_in(answered))
    _refuse_an_incomplete_answer(answer, len(requirements))
    return answer


async def match_observations(
    model_client: BaseChatModel,
    register_rows: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> ObservationAnswer:
    """Which register row each of this batch's observations is about."""
    answered = await call_the_model(
        model_client,
        _observation_prompt(register_rows, observations),
        ObservationAnswer,
    )
    answer = ObservationAnswer.model_validate_json(json_object_in(answered))
    _refuse_an_incomplete_observation_answer(answer, len(observations))
    return answer


def _refuse_an_incomplete_answer(answer: MatchAnswer, asked_about: int) -> None:
    """Check the answer covers every requirement sent, exactly once, usably.

    The shape being valid says nothing about the content: an answer can be
    well-formed JSON and still leave out the one requirement that mattered.
    """
    answered: set[int] = set()
    for outcome in answer.outcomes:
        index = outcome.requirement_index
        if index in answered:
            _refuse(f"Match answered twice for requirement {index}")
        answered.add(index)
        _refuse_an_unusable_requirement_outcome(outcome, asked_about)

    if answered != set(range(asked_about)):
        _refuse(
            f"Match was asked about {asked_about} requirement(s), numbered 0 to "
            f"{asked_about - 1}, and answered for {sorted(answered)}"
        )


def _refuse_an_incomplete_observation_answer(
    answer: ObservationAnswer,
    asked_about: int,
) -> None:
    """The same coverage check, in the words of what was actually asked about.

    An observation left unanswered is not "no row is about it"; it is an answer
    we never received, and the two must not read alike in a failure message.
    """
    answered: set[int] = set()
    for outcome in answer.outcomes:
        index = outcome.observation_index
        if index in answered:
            _refuse(f"Match answered twice for observation {index}")
        answered.add(index)
        _refuse_an_unusable_observation_outcome(outcome)

    if answered != set(range(asked_about)):
        _refuse(
            f"Match was asked about {asked_about} observation(s), numbered 0 to "
            f"{asked_about - 1}, and answered for {sorted(answered)}"
        )


def _refuse_an_unusable_requirement_outcome(
    outcome: MatchOutcome,
    asked_about: int,
) -> None:
    """Refuse an answer whose named candidates do not fit the outcome it gave.

    A requirement matches a register row or an earlier requirement of this same
    batch, and exactly one of the two can be true of one answer.
    """
    index = outcome.requirement_index
    named_row = outcome.row_number is not None
    same_as = outcome.same_as_requirement_index

    if outcome.outcome == NEW_ROW and named_row:
        _refuse(
            f"Match answered '{NEW_ROW}' for requirement {index} and still "
            f"named row {outcome.row_number}"
        )
    if outcome.outcome == NEW_ROW and same_as is not None:
        _refuse(
            f"Match answered '{NEW_ROW}' for requirement {index} and still "
            f"named requirement {same_as}"
        )
    if outcome.outcome != NEW_ROW and named_row and same_as is not None:
        _refuse(
            f"Match answered '{outcome.outcome}' for requirement {index} and "
            f"named both row {outcome.row_number} and requirement {same_as}"
        )
    if outcome.outcome != NEW_ROW and not named_row and same_as is None:
        _refuse(
            f"Match answered '{outcome.outcome}' for requirement {index} "
            "without naming the register row it matched, or the earlier "
            "requirement in this batch it is the same as"
        )
    if same_as is not None:
        _refuse_an_unreachable_batch_candidate(index, same_as, asked_about)


def _refuse_an_unreachable_batch_candidate(
    index: int,
    same_as: int,
    asked_about: int,
) -> None:
    """A requirement may only be matched against one that comes before it.

    Without that rule requirement 0 can name 1 while 1 names 0, and no row is
    ever reached. Pointing forward is refused, never quietly reordered.
    """
    if not 0 <= same_as < asked_about:
        _refuse(
            f"Match answered that requirement {index} is the same as "
            f"requirement {same_as}, which is not in this batch"
        )
    if same_as >= index:
        _refuse(
            f"Match answered that requirement {index} is the same as "
            f"requirement {same_as}, which does not come before it"
        )


def _refuse_an_unusable_observation_outcome(outcome: ObservationOutcome) -> None:
    """Refuse an observation answer whose named row does not fit its outcome."""
    index = outcome.observation_index
    row_number = outcome.row_number

    if outcome.outcome == NEW_ROW and row_number is not None:
        _refuse(
            f"Match answered '{NEW_ROW}' for observation {index} and still "
            f"named row {row_number}"
        )
    if outcome.outcome != NEW_ROW and row_number is None:
        _refuse(
            f"Match answered '{outcome.outcome}' for observation {index} "
            "without naming the register row it matched"
        )


def _refuse(cause: str) -> NoReturn:
    raise IncompleteMatchAnswer(f"{cause}.{INCOMPLETE_ANSWER_FIX}")


def _observation_prompt(
    register_rows: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> list[BaseMessage]:
    observation_view = [
        {
            "observation_index": index,
            "kind": observation["kind"],
            "summary": observation["summary"],
            "source_file": observation["source_file"],
            "source_words": observation["source_words"],
        }
        for index, observation in enumerate(observations)
    ]
    return [
        SystemMessage(content=_OBSERVATION_INSTRUCTIONS),
        HumanMessage(
            content=(
                f"{OBSERVATION_PROMPT_MARKER}.\n\n"
                f"Register rows:\n{json.dumps(_register_view(register_rows), indent=2)}"
                f"\n\nObservations found in this batch:\n"
                f"{json.dumps(observation_view, indent=2)}"
            )
        ),
    ]


def _register_view(register_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"row_number": row["row_number"], "what_was_asked": row["what_was_asked"]}
        for row in register_rows
    ]


def _match_prompt(
    register_rows: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
) -> list[BaseMessage]:
    register_view = _register_view(register_rows)
    requirement_view = [
        {
            "requirement_index": index,
            "summary": requirement["summary"],
            "document_type": requirement["document_type"],
            "source_file": requirement["source_file"],
            "source_words": requirement["source_words"],
        }
        for index, requirement in enumerate(requirements)
    ]
    return [
        SystemMessage(content=_INSTRUCTIONS),
        HumanMessage(
            content=(
                f"{MATCH_PROMPT_MARKER}.\n\n"
                f"Register rows:\n{json.dumps(register_view, indent=2)}\n\n"
                f"Requirements found in this batch:\n"
                f"{json.dumps(requirement_view, indent=2)}"
            )
        ),
    ]
