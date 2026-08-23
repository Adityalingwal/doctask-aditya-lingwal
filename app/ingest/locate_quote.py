from __future__ import annotations

from collections.abc import Callable
from typing import NamedTuple


PLACE_BEFORE_FIRST_HEADING = "before the first heading"
HEADING_MARKER = "#"

# Rendering differences between a document's own characters and a live
# model's reply, or between what pdfplumber emits and a plain-text quote —
# the same character rendered another way, exactly as "\n" and a space
# already are. Case is deliberately not in this table: a changed case is a
# changed word, not a rendering difference.
CHARACTER_RENDERING_VARIANTS: dict[str, str] = {
    "‘": "'",  # left single quotation mark
    "’": "'",  # right single quotation mark / curly apostrophe
    "“": '"',  # left double quotation mark
    "”": '"',  # right double quotation mark
    "–": "-",  # en dash
    "—": "-",  # em dash
    "ﬁ": "fi",  # fi ligature
    "ﬂ": "fl",  # fl ligature
}


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
    obvious case. The first occurrence is the one named, because that is where
    `source_words` is read from: one citation states one place, and a
    comma-joined list of them cannot be written as the one sentence every
    surface prints (`app/ingest/source_line.py`).
    """
    normalised_document, original_offsets = _normalise_with_offsets(document_text)
    normalised_quote = _normalise(quote)
    if not normalised_quote:
        return None

    match_start = normalised_document.find(normalised_quote)
    if match_start < 0:
        return None

    match_end = match_start + len(normalised_quote) - 1
    first_character = original_offsets[match_start]
    last_character = original_offsets[match_end]

    return QuoteLocation(
        place=place_of(document_text, first_character),
        source_words=document_text[first_character : last_character + 1],
    )


def _normalise(text: str) -> str:
    mapped = "".join(CHARACTER_RENDERING_VARIANTS.get(character, character) for character in text)
    return " ".join(mapped.split())


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
        # A one-character-to-two-character replacement (ﬁ -> fi) must append
        # the original index for each character it produces, or every offset
        # after it shifts and the citation names the wrong place.
        for mapped_character in CHARACTER_RENDERING_VARIANTS.get(character, character):
            characters.append(mapped_character)
            offsets.append(index)
        previous_was_space = False
    return "".join(characters), offsets
