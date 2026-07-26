"""F3: deterministic reverse-lookup of the locator key from the broken value.

The classifier already extracts the broken locator value/type from the trace.
When exactly one key in the locators directory carries that type+value, the
run must heal using that key — even if the LLM hallucinates a wrong key.
Zero or multiple reverse matches fall back to the LLM-proposed key path.
"""

import argparse
import json
from datetime import datetime, timezone

import heal_locator
from conftest import FRAMEWORK_TRACE, make_result_file

NOW = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)

BROKEN_VALUE = "//label[text()='Username']/following-sibling::div//input"


class FakeClient:
    def __init__(self, response: str):
        self.response = response

    def complete(self, prompt: str) -> str:
        return self.response


class FakeNotifier:
    def __init__(self):
        self.messages: list[str] = []

    def notify(self, text: str) -> bool:
        self.messages.append(text)
        return True


def _args(results_dir, locators_dir, quota_dir) -> argparse.Namespace:
    return argparse.Namespace(
        allure_results=str(results_dir),
        locators_dir=str(locators_dir),
        dom_file=None,
        quota_dir=str(quota_dir),
        max_attempts=3,
        dry_run=False,
        quota_increment=False,
    )


def test_reverse_lookup_heals_despite_hallucinated_llm_key(
    results_dir, locators_dir, tmp_path
):
    make_result_file(results_dir, "Login with valid credentials", FRAMEWORK_TRACE)
    hallucinated = {"key": "noSuchKeyAnywhere", "type": "css", "value": "#username-input"}
    outcome = heal_locator.run(
        _args(results_dir, locators_dir, tmp_path / "quota"),
        llm_client=FakeClient(json.dumps(hallucinated)),
        notifier=FakeNotifier(),
        now=NOW,
    )
    assert outcome.edit is not None
    assert outcome.edit.key == "userNameField"
    assert outcome.edit.old_value == BROKEN_VALUE
    assert outcome.edit.new_value == "#username-input"
    data = json.loads((locators_dir / "login.json").read_text(encoding="utf-8"))
    assert data["userNameField"] == {"type": "css", "value": "#username-input"}


def test_find_keys_by_value_matches_type_and_value(locators_dir):
    resolved = heal_locator.find_keys_by_value(locators_dir, "xpath", BROKEN_VALUE)
    assert [(key, match.file) for key, match in resolved] == [
        ("userNameField", "login.json")
    ]


def test_find_keys_by_value_ignores_same_value_with_wrong_type(locators_dir):
    # Same xpath string registered as "css" must not reverse-match.
    (locators_dir / "shadow.json").write_text(
        json.dumps({"shadowKey": {"type": "css", "value": BROKEN_VALUE}}),
        encoding="utf-8",
    )
    resolved = heal_locator.find_keys_by_value(locators_dir, "xpath", BROKEN_VALUE)
    assert [key for key, _ in resolved] == ["userNameField"]


def test_zero_reverse_matches_falls_back_to_llm_key_path(
    results_dir, locators_dir, tmp_path
):
    make_result_file(results_dir, "Login with valid credentials", FRAMEWORK_TRACE)
    # Remove the broken value so reverse lookup finds nothing; the LLM key
    # then cannot match the trace either, so the run stays unhealed (the
    # validation gate is intact).
    (locators_dir / "login.json").write_text(
        json.dumps({"loginButton": {"type": "xpath", "value": "//button[text()='Login']"}}),
        encoding="utf-8",
    )
    proposal = {"key": "userNameField", "type": "css", "value": "#username-input"}
    notifier = FakeNotifier()
    outcome = heal_locator.run(
        _args(results_dir, locators_dir, tmp_path / "quota"),
        llm_client=FakeClient(json.dumps(proposal)),
        notifier=notifier,
        now=NOW,
    )
    assert outcome.edit is None
    assert outcome.validation_error
    assert any("unhealed" in message.lower() for message in notifier.messages)


def test_multiple_reverse_matches_fall_back_to_llm_key_path(
    results_dir, locators_dir, tmp_path
):
    make_result_file(results_dir, "Login with valid credentials", FRAMEWORK_TRACE)
    # Duplicate the broken value under a second key: ambiguous reverse lookup
    # must fall back to the LLM-proposed key, which still heals correctly.
    (locators_dir / "shadow.json").write_text(
        json.dumps({"shadowKey": {"type": "xpath", "value": BROKEN_VALUE}}),
        encoding="utf-8",
    )
    proposal = {"key": "userNameField", "type": "css", "value": "#username-input"}
    outcome = heal_locator.run(
        _args(results_dir, locators_dir, tmp_path / "quota"),
        llm_client=FakeClient(json.dumps(proposal)),
        notifier=FakeNotifier(),
        now=NOW,
    )
    assert outcome.edit is not None
    assert outcome.edit.key == "userNameField"
    # The ambiguous duplicate was not touched.
    shadow = json.loads((locators_dir / "shadow.json").read_text(encoding="utf-8"))
    assert shadow["shadowKey"]["value"] == BROKEN_VALUE
