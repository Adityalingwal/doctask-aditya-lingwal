from __future__ import annotations

import ast
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
# `#` before a digit reads as a database key rather than as the row a person
# is looking at, and it reached the screen from four directions at once: a
# refusal, a failure reason, a prompt's worked example and the export. Every
# sentence this repository writes is checked in one place.
#
# The screen's own half of this sweep is
# `ui/tests/no_number_this_screen_writes_is_prefixed_with_a_hash.test.jsx`,
# which walks `ui/src` for the same thing: `ui/dist` is git-ignored and built
# on demand, so a check over committed files cannot reach the bundle.
A_HASH_BEFORE_A_DIGIT = re.compile(r"#\d")
MARKDOWN_FIXTURE = PROJECT_ROOT / "tests/register/fixtures/register.md"


def test_no_string_the_application_can_print_puts_a_hash_before_a_number() -> None:
    offenders = [
        f"{path.relative_to(PROJECT_ROOT)}: {text!r}"
        for path in sorted((PROJECT_ROOT / "app").rglob("*.py"))
        for text in _string_literals(path)
        if A_HASH_BEFORE_A_DIGIT.search(text)
    ]
    assert offenders == []


def test_no_configuration_value_puts_a_hash_before_a_number() -> None:
    offenders = [
        f"{path.relative_to(PROJECT_ROOT)}: {line!r}"
        for path in sorted((PROJECT_ROOT / "config").glob("*.yaml"))
        for line in path.read_text(encoding="utf-8").splitlines()
        # A YAML comment starts with `#`, and a comment is not a sentence
        # anyone reads on a screen.
        if not line.lstrip().startswith("#")
        and A_HASH_BEFORE_A_DIGIT.search(line)
    ]
    assert offenders == []


def test_the_markdown_register_puts_no_hash_before_a_number() -> None:
    assert not A_HASH_BEFORE_A_DIGIT.search(
        MARKDOWN_FIXTURE.read_text(encoding="utf-8")
    )


def _string_literals(path: Path) -> list[str]:
    """Every string the module holds — docstrings and prompts included.

    Read with `ast` rather than by grepping the file, so a `#` inside a Python
    comment is never mistaken for one inside a sentence.
    """
    return [
        node.value
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
