from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from psycopg import AsyncConnection

from app.database import build_connection_pool
from app.examine.frozen_rules import (
    APPLIES_WHEN_KEY,
    RulesFileUnusable,
    fingerprint_of_rules,
    freeze_rules_for_run,
    frozen_rules_of_run,
    load_rules,
)
from app.extract.answer import (
    DOCUMENT_WORKFLOW_ORDER,
    HANDOVER_SUMMARY,
    TESTING_FEEDBACK,
)
from app.runs.statuses import RUNNING
from tests.runs.application import PROJECT_ROOT, temporary_database


SHIPPED_RULES_FILE = PROJECT_ROOT / "config" / "rules.yaml"

PLAIN_RULES = """\
rules:
  - id: R3
    text: "No requirement stays blocked beyond max_days without follow-up."
    params:
      max_days: 14
"""
SAME_RULES_COMMENTED_AND_RESPACED = """\
# The rules this project is judged against.
rules:

  - id:    R3

    text:  "No requirement stays blocked beyond max_days without follow-up."
    params:
      max_days:   14   # two weeks
"""
RULES_WITH_A_CHANGED_VALUE = PLAIN_RULES.replace("max_days: 14", "max_days: 30")
UNKNOWN_DOCUMENT_KIND = "invoice"
RULES_NAMING_AN_UNKNOWN_KIND = f"""\
rules:
  - id: R1
    text: "Anything built must have a written requirement."
    applies_when:
      - {UNKNOWN_DOCUMENT_KIND}
"""


def test_the_shipped_rules_file_loads_as_the_default_rules() -> None:
    rules = load_rules(SHIPPED_RULES_FILE)

    assert [rule["id"] for rule in rules] == ["R1", "R2", "R4", "R5"]
    assert all(rule["params"] == {} for rule in rules)
    # Every shipped rule waits for the kind of document it is about, so none of
    # them is ever judged against a register nothing has spoken about.
    assert {rule["id"]: rule[APPLIES_WHEN_KEY] for rule in rules} == {
        "R1": [HANDOVER_SUMMARY],
        "R2": [TESTING_FEEDBACK],
        "R4": [TESTING_FEEDBACK],
        "R5": [HANDOVER_SUMMARY, TESTING_FEEDBACK],
    }


def test_a_rule_naming_no_document_kind_always_applies(tmp_path: Path) -> None:
    """The field is absent, not empty: a rule that waits for nothing says so.

    An empty list would be the same claim written differently, and it would
    move every fingerprint of every rules file that never named a kind.
    """
    plain = tmp_path / "plain.yaml"
    plain.write_text(PLAIN_RULES, encoding="utf-8")

    (rule,) = load_rules(plain)

    assert APPLIES_WHEN_KEY not in rule


def test_an_unknown_applies_when_value_is_refused_at_freeze_naming_the_four_kinds(
    tmp_path: Path,
) -> None:
    """A rule waiting on a kind that can never be read would never run again.

    The file is re-read on every run, so this is refused where a run freezes
    it as firmly as it is refused at startup.
    """
    broken = tmp_path / "rules.yaml"
    broken.write_text(RULES_NAMING_AN_UNKNOWN_KIND, encoding="utf-8")

    with pytest.raises(RulesFileUnusable) as refused:
        load_rules(broken)

    message = str(refused.value)
    assert UNKNOWN_DOCUMENT_KIND in message
    assert "R1" in message
    for kind in DOCUMENT_WORKFLOW_ORDER:
        assert kind in message
    assert "start another run" in message


def test_rules_fingerprint_ignores_comments_and_layout(tmp_path: Path) -> None:
    plain = tmp_path / "plain.yaml"
    plain.write_text(PLAIN_RULES, encoding="utf-8")
    commented = tmp_path / "commented.yaml"
    commented.write_text(SAME_RULES_COMMENTED_AND_RESPACED, encoding="utf-8")

    assert fingerprint_of_rules(load_rules(plain)) == fingerprint_of_rules(
        load_rules(commented)
    )


def test_rules_fingerprint_changes_when_a_rule_value_changes(
    tmp_path: Path,
) -> None:
    before = tmp_path / "before.yaml"
    before.write_text(PLAIN_RULES, encoding="utf-8")
    after = tmp_path / "after.yaml"
    after.write_text(RULES_WITH_A_CHANGED_VALUE, encoding="utf-8")

    assert fingerprint_of_rules(load_rules(before)) != fingerprint_of_rules(
        load_rules(after)
    )


@pytest.mark.parametrize(
    ("broken_rules", "cause"),
    [
        ("rules:\n  - id: R1\n   text: bad indent\n", "not valid YAML"),
        ("checks:\n  - id: R1\n", "must hold a 'rules:' list"),
        ("rules:\n", "must hold a 'rules:' list"),
        ("rules:\n  - text: no id here\n", "has no 'id:'"),
        ("rules:\n  - id: R1\n", "has no 'text:'"),
        (
            "rules:\n  - id: R1\n    text: one\n  - id: R1\n    text: two\n",
            "two rules the id R1",
        ),
    ],
)
def test_an_unusable_rules_file_names_its_cause_and_its_fix(
    tmp_path: Path,
    broken_rules: str,
    cause: str,
) -> None:
    broken = tmp_path / "rules.yaml"
    broken.write_text(broken_rules, encoding="utf-8")

    with pytest.raises(RulesFileUnusable) as refused:
        load_rules(broken)

    assert cause in str(refused.value)
    assert "start another run" in str(refused.value)


def test_a_missing_rules_file_is_never_read_as_having_no_rules(
    tmp_path: Path,
) -> None:
    with pytest.raises(RulesFileUnusable) as refused:
        load_rules(tmp_path / "absent.yaml")

    assert "not the same as having no rules" in str(refused.value)
    assert "start another run" in str(refused.value)


def test_rules_edited_after_a_run_froze_them_do_not_reach_that_run(
    tmp_path: Path,
) -> None:
    rules_path = tmp_path / "rules.yaml"
    rules_path.write_text(PLAIN_RULES, encoding="utf-8")

    frozen = asyncio.run(_freeze_twice_around_an_edit(rules_path))

    assert frozen["first"] == frozen["second"] == frozen["stored"]
    assert frozen["second"][0]["params"]["max_days"] == 14
    assert frozen["fingerprint"] == fingerprint_of_rules(frozen["first"])


async def _freeze_twice_around_an_edit(rules_path: Path) -> dict[str, Any]:
    with temporary_database() as database_url:
        pool = build_connection_pool(database_url)
        await pool.open(wait=True)
        try:
            async with pool.connection() as connection:
                run_id = await _running_run(connection)
                first = await freeze_rules_for_run(connection, run_id, rules_path)

                rules_path.write_text(RULES_WITH_A_CHANGED_VALUE, encoding="utf-8")
                # The stage that freezes is re-entered after a crash; a second
                # pass must read what the run already froze.
                second = await freeze_rules_for_run(connection, run_id, rules_path)

                stored = await connection.execute(
                    "SELECT rules_fingerprint FROM runs WHERE id = %s",
                    (run_id,),
                )
                return {
                    "first": first,
                    "second": second,
                    "stored": await frozen_rules_of_run(connection, run_id),
                    "fingerprint": (await stored.fetchone())["rules_fingerprint"],
                }
        finally:
            await pool.close()


async def _running_run(connection: AsyncConnection) -> UUID:
    project_id, run_id = uuid4(), uuid4()
    await connection.execute(
        "INSERT INTO projects (id, name, source_folder_path) VALUES (%s, %s, %s)",
        (project_id, "Frozen rules portal", "/projects/intake-portal"),
    )
    await connection.execute(
        "INSERT INTO runs (id, project_id, status) VALUES (%s, %s, %s)",
        (run_id, project_id, RUNNING),
    )
    return run_id
