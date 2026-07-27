"""Integration (task 2.9): mocked LLM -> validated edit; end-to-end dry-run.

No real network calls: the LLM client and Slack notifier are test doubles.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import heal_locator
from conftest import FRAMEWORK_TRACE, VERIFICATION_TRACE, make_result_file

FIXTURES = Path(__file__).resolve().parent / "fixtures"
DOM_DUMP = FIXTURES / "dom_dump.html"
NOW = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)

PROPOSAL = {"key": "userNameField", "type": "css", "value": "#username-input"}


class FakeClient:
    def __init__(self, response: str):
        self.response = response
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response


class ExplodingClient:
    def complete(self, prompt: str) -> str:
        raise AssertionError("LLM must not be called in this scenario")


class FakeNotifier:
    def __init__(self):
        self.messages: list[str] = []

    def notify(self, text: str) -> bool:
        self.messages.append(text)
        return True


def _args(results_dir, locators_dir, quota_dir, dry_run=False) -> argparse.Namespace:
    return argparse.Namespace(
        allure_results=str(results_dir),
        locators_dir=str(locators_dir),
        dom_file=str(DOM_DUMP),
        quota_dir=str(quota_dir),
        max_attempts=3,
        dry_run=dry_run,
        quota_increment=False,
    )


def test_mocked_llm_proposal_is_validated_and_applied(results_dir, locators_dir, tmp_path):
    make_result_file(results_dir, "Login with valid credentials", FRAMEWORK_TRACE)
    client = FakeClient(json.dumps(PROPOSAL))
    outcome = heal_locator.run(
        _args(results_dir, locators_dir, tmp_path / "quota"),
        llm_client=client,
        notifier=FakeNotifier(),
        now=NOW,
    )
    assert outcome.edit is not None
    assert outcome.edit.old_value == "//label[text()='Username']/following-sibling::div//input"
    assert outcome.edit.new_value == "#username-input"
    data = json.loads((locators_dir / "login.json").read_text(encoding="utf-8"))
    assert data["userNameField"] == {"type": "css", "value": "#username-input"}
    # The DOM dump reached the LLM prompt as healing context.
    assert "username-input" in client.prompts[0]


def test_dry_run_proposes_without_editing(results_dir, locators_dir, tmp_path):
    make_result_file(results_dir, "Login with valid credentials", FRAMEWORK_TRACE)
    make_result_file(results_dir, "Success modal is shown", VERIFICATION_TRACE)
    notifier = FakeNotifier()
    before = (locators_dir / "login.json").read_text(encoding="utf-8")
    outcome = heal_locator.run(
        _args(results_dir, locators_dir, tmp_path / "quota", dry_run=True),
        llm_client=FakeClient(json.dumps(PROPOSAL)),
        notifier=notifier,
        now=NOW,
    )
    assert (locators_dir / "login.json").read_text(encoding="utf-8") == before
    assert outcome.proposal == PROPOSAL
    assert outcome.edit is None
    # The VerificationException scenario was reported as a bug, never healed.
    assert [b.scenario for b in outcome.bugs] == ["Success modal is shown"]
    assert any("Success modal is shown" in message for message in notifier.messages)


def test_over_quota_is_slack_only(results_dir, locators_dir, tmp_path):
    make_result_file(results_dir, "Login with valid credentials", FRAMEWORK_TRACE)
    quota_dir = tmp_path / "quota"
    quota_dir.mkdir()
    (quota_dir / "heal-quota-2026-07-26.txt").write_text("3", encoding="utf-8")
    notifier = FakeNotifier()
    outcome = heal_locator.run(
        _args(results_dir, locators_dir, quota_dir),
        llm_client=ExplodingClient(),
        notifier=notifier,
        now=NOW,
    )
    assert outcome.quota_blocked
    assert outcome.edit is None
    assert any("quota" in message.lower() for message in notifier.messages)


def test_bug_only_run_never_calls_llm(results_dir, locators_dir, tmp_path):
    make_result_file(results_dir, "Success modal is shown", VERIFICATION_TRACE)
    notifier = FakeNotifier()
    outcome = heal_locator.run(
        _args(results_dir, locators_dir, tmp_path / "quota"),
        llm_client=ExplodingClient(),
        notifier=notifier,
        now=NOW,
    )
    assert outcome.edit is None
    assert not outcome.quota_blocked
    assert [b.scenario for b in outcome.bugs] == ["Success modal is shown"]
    assert any("Success modal is shown" in message for message in notifier.messages)


def test_invalid_proposal_is_unhealed_and_notified(results_dir, locators_dir, tmp_path):
    make_result_file(results_dir, "Login with valid credentials", FRAMEWORK_TRACE)
    bad = {"key": "userNameField", "type": "jquery", "value": ":input"}
    notifier = FakeNotifier()
    outcome = heal_locator.run(
        _args(results_dir, locators_dir, tmp_path / "quota"),
        llm_client=FakeClient(json.dumps(bad)),
        notifier=notifier,
        now=NOW,
    )
    assert outcome.edit is None
    assert outcome.validation_error
    assert any("unhealed" in message.lower() for message in notifier.messages)


def test_extract_json_object_tolerates_surrounding_text():
    raw = 'Here is the fix:\n```json\n{"key": "k", "type": "css", "value": "#v"}\n```\nDone.'
    assert heal_locator.extract_json_object(raw) == {"key": "k", "type": "css", "value": "#v"}


def test_quota_increment_mode(tmp_path):
    args = argparse.Namespace(
        allure_results="unused",
        locators_dir="unused",
        dom_file=None,
        quota_dir=str(tmp_path),
        max_attempts=3,
        dry_run=False,
        quota_increment=True,
    )
    outcome = heal_locator.run(args, notifier=FakeNotifier(), now=NOW)
    assert outcome.quota_count == 1
    assert heal_locator.read_quota(tmp_path, NOW) == 1
