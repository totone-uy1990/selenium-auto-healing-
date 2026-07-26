"""F1: LLM network/API failures must fail open.

A URLError, HTTPError, timeout, or malformed API response shape during the
LLM call must never crash the run: the failure is treated as "unhealed",
Slack is notified, and the summary JSON is still emitted.
"""

import argparse
import json
import urllib.error
from datetime import datetime, timezone

import pytest

import heal_locator
from conftest import FRAMEWORK_TRACE, make_result_file

NOW = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)


class RaisingClient:
    """LLM client double whose complete() always raises the given error."""

    def __init__(self, exc: BaseException):
        self._exc = exc

    def complete(self, prompt: str) -> str:
        raise self._exc


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


def _run_with_raising_client(exc, results_dir, locators_dir, tmp_path):
    make_result_file(results_dir, "Login with valid credentials", FRAMEWORK_TRACE)
    notifier = FakeNotifier()
    outcome = heal_locator.run(
        _args(results_dir, locators_dir, tmp_path / "quota"),
        llm_client=RaisingClient(exc),
        notifier=notifier,
        now=NOW,
    )
    return outcome, notifier


@pytest.mark.parametrize(
    "exc",
    [
        urllib.error.URLError("connection refused"),
        urllib.error.HTTPError("https://models.github.ai", 500, "Server Error", {}, None),
        TimeoutError("timed out"),
        OSError("network unreachable"),
    ],
    ids=["url-error", "http-error", "timeout", "os-error"],
)
def test_llm_transport_failure_is_unhealed_and_notified(
    exc, results_dir, locators_dir, tmp_path
):
    outcome, notifier = _run_with_raising_client(exc, results_dir, locators_dir, tmp_path)
    assert outcome.edit is None
    assert outcome.validation_error
    assert any("unhealed" in message.lower() for message in notifier.messages)


@pytest.mark.parametrize(
    "malformed_payload",
    [
        {},  # missing "choices" -> KeyError
        {"choices": []},  # empty choices -> IndexError
        {"choices": [None]},  # None entry -> TypeError
        {"choices": [{"message": "not-a-dict"}]},  # wrong shape -> TypeError
    ],
    ids=["missing-choices", "empty-choices", "none-choice", "string-message"],
)
def test_malformed_api_response_shape_is_unhealed_and_notified(
    monkeypatch, malformed_payload, results_dir, locators_dir, tmp_path
):
    monkeypatch.setattr(heal_locator, "_post_json", lambda *a, **k: malformed_payload)
    client = heal_locator.GitHubModelsClient(token="fake-token")
    make_result_file(results_dir, "Login with valid credentials", FRAMEWORK_TRACE)
    notifier = FakeNotifier()
    outcome = heal_locator.run(
        _args(results_dir, locators_dir, tmp_path / "quota"),
        llm_client=client,
        notifier=notifier,
        now=NOW,
    )
    assert outcome.edit is None
    assert outcome.validation_error
    assert any("unhealed" in message.lower() for message in notifier.messages)


def test_main_still_emits_summary_json_on_llm_failure(
    monkeypatch, capsys, results_dir, locators_dir, tmp_path
):
    make_result_file(results_dir, "Login with valid credentials", FRAMEWORK_TRACE)
    monkeypatch.setattr(
        heal_locator,
        "get_llm_client",
        lambda *a, **k: RaisingClient(urllib.error.URLError("down")),
    )
    exit_code = heal_locator.main(
        [
            "--allure-results",
            str(results_dir),
            "--locators-dir",
            str(locators_dir),
            "--quota-dir",
            str(tmp_path / "quota"),
        ]
    )
    summary = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert exit_code == 0
    assert summary["healed"] is False
    assert summary["validation_error"]
