from __future__ import annotations

from pathlib import Path
from typing import Any

from app.examine.frozen_rules import load_rules
from tests.documents.register_documents import (
    examine_marker,
    extract_marker,
    extraction_answer,
    match_answer,
    match_marker,
    no_findings_answer,
    write_meeting_note,
)
from tests.runs.application import (
    ApplicationProcess,
    approve_every_decision_and_finish_review,
    temporary_database,
    temporary_project_folder,
    wait_for_run_status,
    write_script,
)


SOURCE_FILE = "meeting-note.md"
REQUIREMENT = "an email to the operations team on intake form submit"
ONE_RULE_ONLY = """\
rules:
  - id: R1
    text: "Anything built must have a written requirement."
"""


def test_no_rule_is_judged_outside_config_rules_yaml(tmp_path: Path) -> None:
    """Every rule a run reports is one it froze from the rules file, and no other.

    A rule judged in code would be appended here without appearing in the file,
    which is exactly what a reader editing the file could never discover.
    """
    reported = _run_against(tmp_path, ONE_RULE_ONLY)

    assert [rule["id"] for rule in reported["at_review"]["rules"]] == ["R1"]
    assert [rule["id"] for rule in reported["exported"]["rules"]] == ["R1"]
    assert reported["at_review"]["findings"] == []
    assert reported["exported"]["findings"] == []
    assert "R1" in reported["markdown"]
    for named_in_code in ("D1", "D2"):
        assert named_in_code not in reported["markdown"]


def test_no_rule_in_config_rules_yaml_asks_for_a_document_date() -> None:
    """The register keeps no document date, so no shipped rule may ask for one.

    An elapsed-time rule would be judged against evidence the register no
    longer holds, leaving the model to invent the days it counted.
    """
    shipped = Path(__file__).resolve().parents[2] / "config" / "rules.yaml"

    for rule in load_rules(shipped):
        wording = " ".join([rule["text"], *rule["params"]]).lower()
        for date_word in ("date", "day", "week", "month", "elapsed"):
            assert date_word not in wording, (
                f"rule {rule['id']} names '{date_word}', and the register no "
                "longer keeps a document date for a rule to count from"
            )


def _run_against(tmp_path: Path, rules_file: str) -> dict[str, Any]:
    rules_path = tmp_path / "rules.yaml"
    rules_path.write_text(rules_file, encoding="utf-8")
    script_path = tmp_path / "script.json"

    with temporary_project_folder("rules-in-config") as (folder, folder_path):
        quote = write_meeting_note(folder, SOURCE_FILE, REQUIREMENT)
        write_script(
            script_path,
            {
                extract_marker(SOURCE_FILE): extraction_answer(REQUIREMENT, quote),
                match_marker(): match_answer(1),
                examine_marker(): no_findings_answer(),
            },
        )
        with temporary_database() as database_url:
            application = ApplicationProcess(
                database_url=database_url,
                script_path=script_path,
                call_log_path=tmp_path / "model-calls.jsonl",
                rules_config_path=rules_path,
            )
            application.start()
            try:
                with application.client() as client:
                    project_id = client.post(
                        "/projects", json={"source_folder_path": folder_path}
                    ).json()["project_id"]
                    run_id = client.post(
                        "/runs", json={"project_id": project_id}
                    ).json()["run_id"]
                    at_review = wait_for_run_status(client, run_id, "needs review")
                    approve_every_decision_and_finish_review(client, run_id)
                    wait_for_run_status(client, run_id, "done")
                    exported = client.get(f"/runs/{run_id}/export").json()
                    markdown = client.get(
                        f"/runs/{run_id}/export", params={"format": "markdown"}
                    ).text
                return {
                    "at_review": at_review["examine"],
                    "exported": exported["examine"],
                    "markdown": markdown,
                }
            finally:
                application.stop()
