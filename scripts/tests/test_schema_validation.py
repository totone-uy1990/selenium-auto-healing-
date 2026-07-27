"""RED (task 2.4): LLM proposal schema validation.

A proposal is applied only when the key exists in exactly one locator file
whose type+value matches the trace's By.toString(), the proposed type is in
the JSON enum, and the value is non-empty, <=500 chars, and != the old value.
"""

import heal_locator

TRACE_TYPE = "xpath"
TRACE_VALUE = "//label[text()='Username']/following-sibling::div//input"


def _valid_proposal() -> dict:
    return {"key": "userNameField", "type": "css", "value": "#username-input"}


def _matches(locators_dir, key="userNameField"):
    return heal_locator.find_locator_entries(locators_dir, key)


def _validate(proposal, matches):
    return heal_locator.validate_proposal(
        proposal, trace_type=TRACE_TYPE, trace_value=TRACE_VALUE, matches=matches
    )


def test_valid_proposal_is_accepted(locators_dir):
    result = _validate(_valid_proposal(), _matches(locators_dir))
    assert result.ok, result.error


def test_unknown_key_is_rejected(locators_dir):
    proposal = {"key": "doesNotExist", "type": "css", "value": "#x"}
    result = _validate(proposal, _matches(locators_dir, key="doesNotExist"))
    assert not result.ok
    assert "exactly one" in result.error


def test_ambiguous_key_is_rejected(locators_dir):
    # Same key in a second file -> not exactly one match.
    import json

    (locators_dir / "duplicate.json").write_text(
        json.dumps(
            {
                "userNameField": {
                    "type": "xpath",
                    "value": "//label[text()='Username']/following-sibling::div//input",
                }
            }
        ),
        encoding="utf-8",
    )
    result = _validate(_valid_proposal(), _matches(locators_dir))
    assert not result.ok
    assert "exactly one" in result.error


def test_wrong_type_enum_is_rejected(locators_dir):
    proposal = {"key": "userNameField", "type": "jquery", "value": "#username-input"}
    result = _validate(proposal, _matches(locators_dir))
    assert not result.ok
    assert "type" in result.error


def test_empty_value_is_rejected(locators_dir):
    proposal = {"key": "userNameField", "type": "css", "value": "   "}
    result = _validate(proposal, _matches(locators_dir))
    assert not result.ok
    assert "empty" in result.error


def test_overlong_value_is_rejected(locators_dir):
    proposal = {"key": "userNameField", "type": "xpath", "value": "//" + "a" * 500}
    result = _validate(proposal, _matches(locators_dir))
    assert not result.ok
    assert "500" in result.error


def test_value_equal_to_old_is_rejected(locators_dir):
    proposal = {
        "key": "userNameField",
        "type": "xpath",
        "value": "//label[text()='Username']/following-sibling::div//input",
    }
    result = _validate(proposal, _matches(locators_dir))
    assert not result.ok
    assert "old" in result.error


def test_mismatched_trace_locator_is_rejected(locators_dir):
    # The trace says the broken locator was the loginButton, not userNameField.
    result = heal_locator.validate_proposal(
        _valid_proposal(),
        trace_type=TRACE_TYPE,
        trace_value="//button[text()='Login']",
        matches=_matches(locators_dir),
    )
    assert not result.ok
    assert "trace" in result.error


def test_all_supported_types_are_accepted(locators_dir):
    for locator_type in ("id", "name", "xpath", "css", "classname", "linktext"):
        proposal = {"key": "userNameField", "type": locator_type, "value": f"new-{locator_type}"}
        result = _validate(proposal, _matches(locators_dir))
        assert result.ok, f"{locator_type}: {result.error}"
