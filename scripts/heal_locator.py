#!/usr/bin/env python3
"""Auto-healing engine for locator failures (SDD change: auto-healing-pipeline).

Reads Allure ``*-result.json`` files produced by Pipeline 1, classifies each
failure deterministically (FrameworkException = locator, anything else = bug),
asks an LLM for a replacement locator, validates and applies the edit, and
notifies Slack. The verification re-run, branch, and PR creation live in the
GitHub Actions workflow; this script is the parse/classify/LLM/edit/notify
engine plus the daily-quota counter.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

SLACK_WEBHOOK_ENV = "SLACK_WEBHOOK_URL"
SLACK_TIMEOUT_SECONDS = 10

DEFAULT_ALLURE_RESULTS_DIR = "build/allure-results"
DEFAULT_LOCATORS_DIR = "src/test/resources/locators"
DEFAULT_QUOTA_DIR = ".heal-quota"

RESULT_FILE_SUFFIX = "-result.json"


@dataclass(frozen=True)
class ScenarioResult:
    """Parsed Allure ``*-result.json`` entry for a single scenario."""

    name: str
    full_name: str
    status: str
    message: str
    trace: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect, classify, and heal locator failures from Allure results."
    )
    parser.add_argument(
        "--allure-results",
        default=DEFAULT_ALLURE_RESULTS_DIR,
        help="Directory containing Allure *-result.json files.",
    )
    parser.add_argument(
        "--locators-dir",
        default=DEFAULT_LOCATORS_DIR,
        help="Directory containing locator JSON files.",
    )
    parser.add_argument(
        "--dom-file",
        default=None,
        help="Optional DOM dump file to include as LLM context.",
    )
    parser.add_argument(
        "--quota-dir",
        default=DEFAULT_QUOTA_DIR,
        help="Directory holding the UTC-day quota counter file.",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Maximum healing attempts per UTC day.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Classify and propose without editing files or calling the network.",
    )
    parser.add_argument(
        "--quota-increment",
        action="store_true",
        help="Increment today's quota counter and exit (used by the workflow "
        "after a verified green re-run).",
    )
    return parser.parse_args(argv)


def parse_result_file(path: Path) -> ScenarioResult:
    """Parse one Allure ``*-result.json`` file into a ScenarioResult."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    details = data.get("statusDetails") or {}
    return ScenarioResult(
        name=data.get("name", ""),
        full_name=data.get("fullName", ""),
        status=data.get("status", ""),
        message=details.get("message", ""),
        trace=details.get("trace", ""),
    )


def load_results(results_dir: Path) -> list[ScenarioResult]:
    """Load every failed/broken Allure result in the directory."""
    if not results_dir.is_dir():
        raise FileNotFoundError(f"Allure results directory not found: {results_dir}")
    results = []
    for path in sorted(results_dir.glob(f"*{RESULT_FILE_SUFFIX}")):
        result = parse_result_file(path)
        if result.status in {"failed", "broken"}:
            results.append(result)
    return results


class SlackNotifier:
    """Posts plain-text messages to a Slack incoming webhook.

    The webhook URL comes exclusively from the ``SLACK_WEBHOOK_URL``
    environment variable; it is never accepted as a CLI argument and never
    hardcoded. When the variable is absent the notifier degrades to stdout so
    local dry-runs keep working. Notification failures never raise: healing
    must not crash because Slack is unreachable.
    """

    def __init__(self, webhook_url: str | None) -> None:
        self._webhook_url = webhook_url

    @classmethod
    def from_env(cls, env: dict | None = None) -> "SlackNotifier":
        source = os.environ if env is None else env
        return cls(source.get(SLACK_WEBHOOK_ENV))

    def notify(self, text: str) -> bool:
        """Send ``text`` to Slack. Returns True on delivery, False otherwise."""
        if not self._webhook_url:
            print(f"[slack:disabled] {text}")
            return False
        payload = json.dumps({"text": text}).encode("utf-8")
        request = urllib.request.Request(
            self._webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=SLACK_TIMEOUT_SECONDS) as response:
                return 200 <= response.status < 300
        except (urllib.error.URLError, OSError) as exc:
            print(f"[slack:error] delivery failed: {exc}", file=sys.stderr)
            return False


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    notifier = SlackNotifier.from_env()
    results = load_results(Path(args.allure_results))
    print(f"Loaded {len(results)} failed scenario result(s).")
    for result in results:
        print(f"- {result.name} [{result.status}]")
    if not results:
        notifier.notify("Auto-heal: no failed scenarios found in Allure results.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
