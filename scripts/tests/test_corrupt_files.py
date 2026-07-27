"""F2: one corrupt JSON file must not abort the whole run.

A malformed Allure ``*-result.json`` is skipped (with a stderr warning) while
the remaining valid results are still classified; a malformed locator JSON is
skipped while other locator files remain searchable.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import heal_locator
from conftest import FRAMEWORK_TRACE, make_result_file

NOW = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)


class FakeNotifier:
    def __init__(self):
        self.messages: list[str] = []

    def notify(self, text: str) -> bool:
        self.messages.append(text)
        return True


def test_corrupt_result_file_is_skipped_and_valid_results_still_load(
    results_dir, capsys
):
    make_result_file(results_dir, "Login with valid credentials", FRAMEWORK_TRACE)
    (results_dir / "corrupt-result.json").write_text(
        '{"name": "truncated', encoding="utf-8"
    )
    results = heal_locator.load_results(results_dir)
    assert [r.name for r in results] == ["Login with valid credentials"]
    assert "corrupt-result.json" in capsys.readouterr().err


def test_load_results_skips_non_object_json(results_dir, capsys):
    make_result_file(results_dir, "Login with valid credentials", FRAMEWORK_TRACE)
    (results_dir / "array-result.json").write_text("[1, 2, 3]", encoding="utf-8")
    results = heal_locator.load_results(results_dir)
    assert [r.name for r in results] == ["Login with valid credentials"]
    assert "array-result.json" in capsys.readouterr().err


def test_non_dict_status_details_does_not_abort_valid_results(results_dir):
    # A parseable result file whose statusDetails is not an object (string,
    # list, number) must not crash the run: its message/trace degrade to
    # empty and the valid files are still processed.
    make_result_file(results_dir, "Login with valid credentials", FRAMEWORK_TRACE)
    (results_dir / "weird-result.json").write_text(
        json.dumps(
            {"name": "weird", "status": "failed", "statusDetails": "oops"}
        ),
        encoding="utf-8",
    )
    results = heal_locator.load_results(results_dir)
    assert "Login with valid credentials" in [r.name for r in results]
    weird = next(r for r in results if r.name == "weird")
    assert weird.message == ""
    assert weird.trace == ""


def test_corrupt_result_file_does_not_abort_full_run(
    results_dir, locators_dir, tmp_path
):
    make_result_file(results_dir, "Login with valid credentials", FRAMEWORK_TRACE)
    (results_dir / "corrupt-result.json").write_text("not json at all", encoding="utf-8")
    args = argparse.Namespace(
        allure_results=str(results_dir),
        locators_dir=str(locators_dir),
        dom_file=None,
        quota_dir=str(tmp_path / "quota"),
        max_attempts=3,
        dry_run=True,
        quota_increment=False,
    )
    outcome = heal_locator.run(args, notifier=FakeNotifier(), now=NOW)
    # The valid scenario was still classified and reached the dry-run prompt.
    assert outcome.bugs == []
    assert outcome.validation_error == ""


def test_corrupt_locator_file_is_skipped_and_others_still_searchable(
    locators_dir, capsys
):
    (locators_dir / "broken.json").write_text("{unclosed", encoding="utf-8")
    matches = heal_locator.find_locator_entries(locators_dir, "userNameField")
    assert len(matches) == 1
    assert matches[0].file == "login.json"
    assert "broken.json" in capsys.readouterr().err


def test_corrupt_locator_file_does_not_abort_healing_run(
    results_dir, locators_dir, tmp_path
):
    make_result_file(results_dir, "Login with valid credentials", FRAMEWORK_TRACE)
    (locators_dir / "broken.json").write_text("{unclosed", encoding="utf-8")
    proposal = {"key": "userNameField", "type": "css", "value": "#username-input"}

    class FakeClient:
        def complete(self, prompt: str) -> str:
            return json.dumps(proposal)

    args = argparse.Namespace(
        allure_results=str(results_dir),
        locators_dir=str(locators_dir),
        dom_file=None,
        quota_dir=str(tmp_path / "quota"),
        max_attempts=3,
        dry_run=False,
        quota_increment=False,
    )
    outcome = heal_locator.run(
        args, llm_client=FakeClient(), notifier=FakeNotifier(), now=NOW
    )
    assert outcome.edit is not None
    assert outcome.edit.key == "userNameField"
