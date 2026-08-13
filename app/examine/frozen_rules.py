from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, NoReturn
from uuid import UUID

import yaml
from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from app.examine.deliverable_checks import DELIVERABLE_CHECK_IDS


RULES_KEY = "rules"
ID_KEY = "id"
TEXT_KEY = "text"
PARAMS_KEY = "params"
FIX_THE_FILE = (
    "Fix the file, or point RULES_CONFIG_PATH at a rules file of your own, "
    "then start another run."
)


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
        if rule_id in DELIVERABLE_CHECK_IDS:
            _refuse(
                f"{config_path} uses the id {rule_id}, which belongs to a "
                "deliverable check this system runs itself"
            )
        params = rule.get(PARAMS_KEY, {})
        if not isinstance(params, dict):
            _refuse(f"rule {rule_id} in {config_path} has a '{PARAMS_KEY}:' "
                    "that is not a mapping")
        seen_ids.add(rule_id)
        rules.append({ID_KEY: rule_id, TEXT_KEY: rule_text, PARAMS_KEY: params})
    return rules


def _refuse(cause: str) -> NoReturn:
    raise RulesFileUnusable(f"{cause}. {FIX_THE_FILE}")
