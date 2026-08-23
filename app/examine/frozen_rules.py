from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, NoReturn
from uuid import UUID

import yaml
from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from app.extract.answer import DOCUMENT_WORKFLOW_ORDER


RULES_KEY = "rules"
ID_KEY = "id"
TEXT_KEY = "text"
PARAMS_KEY = "params"
APPLIES_WHEN_KEY = "applies_when"
FIX_THE_FILE = (
    "Fix the file, or point RULES_CONFIG_PATH at a rules file of your own, "
    "then start another run."
)
ALLOWED_DOCUMENT_KINDS = DOCUMENT_WORKFLOW_ORDER


class RulesFileUnusable(RuntimeError):
    """The rules file could not be read as the rules a run is judged against."""


def load_rules(config_path: Path) -> list[dict[str, Any]]:
    """Read the rules file into the rules a run freezes and is judged against."""
    try:
        parsed = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RulesFileUnusable(
            f"{config_path} is missing, so this run has no rules to examine "
            f"the register against — it is not the same as having no rules. "
            f"Restore the file with a rules: list in it, or point "
            f"RULES_CONFIG_PATH at a rules file of your own, then start "
            f"another run."
        ) from error
    except yaml.YAMLError as error:
        _refuse(f"{config_path} is not valid YAML ({error})")
    except OSError as error:
        raise RulesFileUnusable(
            f"{config_path} could not be read ({error}) — give the application "
            f"read access to it, then start another run."
        ) from error

    if not isinstance(parsed, dict) or not isinstance(parsed.get(RULES_KEY), list):
        _refuse(
            f"{config_path} must hold a '{RULES_KEY}:' list, and it does not"
        )
    return _normalised_rules(config_path, parsed[RULES_KEY])


def fingerprint_of_rules(rules: list[dict[str, Any]]) -> str:
    """Hash the parsed rules, so comments and layout never move the fingerprint."""
    parsed_only = json.dumps(rules, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(parsed_only.encode("utf-8")).hexdigest()


async def freeze_rules_for_run(
    connection: AsyncConnection,
    run_id: UUID,
    config_path: Path,
) -> list[dict[str, Any]]:
    """Freeze this run's rules once, however often the first stage is re-entered.

    A resumed run reads what it already froze rather than the file: editing the
    rules must change the next run, never the one already under way. That also
    means a file broken after a run started cannot stop that run finishing.
    """
    already_frozen = await frozen_rules_of_run(connection, run_id)
    if already_frozen is not None:
        return already_frozen

    rules = load_rules(config_path)
    await connection.execute(
        "UPDATE runs SET rules_snapshot = %s, rules_fingerprint = %s "
        "WHERE id = %s AND rules_snapshot IS NULL",
        (Jsonb(rules), fingerprint_of_rules(rules), run_id),
    )
    return await frozen_rules_of_run(connection, run_id)


async def rules_changed_since_the_register_was_last_examined(
    connection: AsyncConnection,
    run_id: UUID,
    project_id: UUID,
) -> bool:
    """Are this run's frozen rules different from the ones last judged this register?

    The comparison is between fingerprints of the parsed rules, so re-wording a
    comment or moving a line never sends a register back through Examine, and
    changing a value such as max_days always does.
    """
    last_examined = await connection.execute(
        "SELECT rules_fingerprint FROM runs WHERE project_id = %s AND id <> %s "
        "AND examined_row_count IS NOT NULL AND rules_fingerprint IS NOT NULL "
        "ORDER BY created_at DESC LIMIT 1",
        (project_id, run_id),
    )
    judged_against = await last_examined.fetchone()
    if judged_against is None:
        return False

    frozen = await connection.execute(
        "SELECT rules_fingerprint FROM runs WHERE id = %s",
        (run_id,),
    )
    this_run = await frozen.fetchone()
    return this_run["rules_fingerprint"] != judged_against["rules_fingerprint"]


async def frozen_rules_of_run(
    connection: AsyncConnection,
    run_id: UUID,
) -> list[dict[str, Any]] | None:
    result = await connection.execute(
        "SELECT rules_snapshot FROM runs WHERE id = %s",
        (run_id,),
    )
    run = await result.fetchone()
    return run["rules_snapshot"] if run else None


def _normalised_rules(
    config_path: Path,
    listed: list[Any],
) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for position, rule in enumerate(listed, start=1):
        if not isinstance(rule, dict):
            _refuse(f"rule {position} in {config_path} is not a mapping")
        rule_id = rule.get(ID_KEY)
        rule_text = rule.get(TEXT_KEY)
        if not isinstance(rule_id, str) or not rule_id.strip():
            _refuse(f"rule {position} in {config_path} has no '{ID_KEY}:'")
        if not isinstance(rule_text, str) or not rule_text.strip():
            _refuse(f"rule {rule_id} in {config_path} has no '{TEXT_KEY}:'")
        if rule_id in seen_ids:
            _refuse(f"{config_path} gives two rules the id {rule_id}")
        params = rule.get(PARAMS_KEY, {})
        if not isinstance(params, dict):
            _refuse(f"rule {rule_id} in {config_path} has a '{PARAMS_KEY}:' "
                    "that is not a mapping")
        seen_ids.add(rule_id)
        normalised = {ID_KEY: rule_id, TEXT_KEY: rule_text, PARAMS_KEY: params}
        # Absent rather than empty when the rule does not name kinds: a rule
        # naming none applies always, and an empty list would be the same
        # claim written differently — and would move every fingerprint.
        if APPLIES_WHEN_KEY in rule:
            normalised[APPLIES_WHEN_KEY] = _document_kinds(
                config_path, rule_id, rule[APPLIES_WHEN_KEY]
            )
        rules.append(normalised)
    return rules


def _document_kinds(
    config_path: Path,
    rule_id: str,
    named: Any,
) -> list[str]:
    """The document kinds one rule waits for, refusing anything else by name.

    An unknown kind can never be read, so a rule naming one would never run
    again — silently, and looking exactly like a rule that simply found
    nothing.
    """
    if not isinstance(named, list) or not named:
        _refuse(
            f"rule {rule_id} in {config_path} has an '{APPLIES_WHEN_KEY}:' that "
            f"is not a list of document kinds — write one or more of "
            f"{', '.join(ALLOWED_DOCUMENT_KINDS)}, or leave the field out so "
            "the rule always applies"
        )
    for kind in named:
        if kind not in ALLOWED_DOCUMENT_KINDS:
            _refuse(
                f"rule {rule_id} in {config_path} names '{kind}' under "
                f"'{APPLIES_WHEN_KEY}:', which is not a kind of document this "
                f"system reads — use one or more of "
                f"{', '.join(ALLOWED_DOCUMENT_KINDS)}"
            )
    return list(named)


def _refuse(cause: str) -> NoReturn:
    raise RulesFileUnusable(f"{cause}. {FIX_THE_FILE}")
