from __future__ import annotations

from collections.abc import Callable
from typing import NamedTuple


PLACE_BEFORE_FIRST_HEADING = "before the first heading"
HEADING_MARKER = "#"


class QuoteLocation(NamedTuple):
    place: str
    source_words: str


def nearest_heading_above(document_text: str, character_offset: int) -> str:
    text_above = document_text[: character_offset + 1]
    for line in reversed(text_above.splitlines()):
        stripped_line = line.strip()
        if stripped_line.startswith(HEADING_MARKER):
            return stripped_line.lstrip(HEADING_MARKER).strip()
    return PLACE_BEFORE_FIRST_HEADING


def locate_quote(
    document_text: str,
    quote: str,
    place_of: Callable[[str, int], str] = nearest_heading_above,
) -> QuoteLocation | None:
    """Find where the model's quoted words actually sit in the document.

    A quote can genuinely sit in more than one place — a testing feedback
    document restating the same finding against several requirements is the
    obvious case — so every occurrence is found and every place it names is
    reported, in document order. `source_words` still comes from the first
    occurrence; it is the document's own characters either way, and the
    reader is told where all of them are by `place`.
    """
    normalised_document, original_offsets = _normalise_with_offsets(document_text)
    normalised_quote = _normalise(quote)
    if not normalised_quote:
        return None

    match_starts = _find_all(normalised_document, normalised_quote)
    if not match_starts:
        return None

    match_end = match_starts[0] + len(normalised_quote) - 1
    first_character = original_offsets[match_starts[0]]
    last_character = original_offsets[match_end]

    places: list[str] = []
    for match_start in match_starts:
        place = place_of(document_text, original_offsets[match_start])
        if place not in places:
            places.append(place)

    return QuoteLocation(
        place=", ".join(places),
        source_words=document_text[first_character : last_character + 1],
    )


def _find_all(haystack: str, needle: str) -> list[int]:
    """Every start offset `needle` occurs at in `haystack`, in order."""
    positions: list[int] = []
    start = 0
    while True:
        index = haystack.find(needle, start)
        if index < 0:
            return positions
        positions.append(index)
        start = index + len(needle)


def _normalise(text: str) -> str:
    return " ".join(text.split())


def _normalise_with_offsets(text: str) -> tuple[str, list[int]]:
    characters: list[str] = []
    offsets: list[int] = []
    previous_was_space = False
    for index, character in enumerate(text):
        if character.isspace():
            if characters and not previous_was_space:
                characters.append(" ")
                offsets.append(index)
            previous_was_space = True
            continue
        characters.append(character)
        offsets.append(index)
        previous_was_space = False
    return "".join(characters), offsets
