"""Locator JSON edit (task 2.6).

The edit targets the key in exactly one file under the locators directory and
retains the old type+value in the returned edit record for the PR body.
"""

import json

import pytest

import heal_locator


def test_edit_updates_only_the_target_entry(locators_dir):
    matches = heal_locator.find_locator_entries(locators_dir, "userNameField")
    edit = heal_locator.apply_locator_edit(
        locators_dir, "userNameField", "css", "#username-input", matches
    )
    data = json.loads((locators_dir / "login.json").read_text(encoding="utf-8"))
    assert data["userNameField"] == {"type": "css", "value": "#username-input"}
    # Sibling keys and other files are untouched.
    assert data["loginButton"] == {"type": "xpath", "value": "//button[text()='Login']"}
    success = json.loads((locators_dir / "success.json").read_text(encoding="utf-8"))
    assert success["msgStatus"]["value"] == "//h2 | //h4"


def test_edit_retains_old_value_for_pr_body(locators_dir):
    matches = heal_locator.find_locator_entries(locators_dir, "userNameField")
    edit = heal_locator.apply_locator_edit(
        locators_dir, "userNameField", "css", "#username-input", matches
    )
    assert edit.file == "login.json"
    assert edit.key == "userNameField"
    assert edit.old_type == "xpath"
    assert edit.old_value == "//label[text()='Username']/following-sibling::div//input"
    assert edit.new_type == "css"
    assert edit.new_value == "#username-input"


def test_edit_rejects_ambiguous_key(locators_dir):
    (locators_dir / "duplicate.json").write_text(
        json.dumps({"userNameField": {"type": "xpath", "value": "//dup"}}),
        encoding="utf-8",
    )
    matches = heal_locator.find_locator_entries(locators_dir, "userNameField")
    with pytest.raises(ValueError, match="exactly one"):
        heal_locator.apply_locator_edit(
            locators_dir, "userNameField", "css", "#username-input", matches
        )


def test_edit_rejects_unknown_key(locators_dir):
    matches = heal_locator.find_locator_entries(locators_dir, "ghost")
    with pytest.raises(ValueError, match="exactly one"):
        heal_locator.apply_locator_edit(locators_dir, "ghost", "css", "#x", matches)
