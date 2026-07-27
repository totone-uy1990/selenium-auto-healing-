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
import http.client
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

SLACK_WEBHOOK_ENV = "SLACK_WEBHOOK_URL"
SLACK_TIMEOUT_SECONDS = 10

DEFAULT_ALLURE_RESULTS_DIR = "build/allure-results"
DEFAULT_LOCATORS_DIR = "src/test/resources/locators"
DEFAULT_QUOTA_DIR = ".heal-quota"

RESULT_FILE_SUFFIX = "-result.json"

# Selenium By.toString() prefixes mapped to the locator JSON type enum
# (id|name|xpath|css|classname|linktext). By types outside this map are not
# healable because the locator JSON contract cannot express them.
BY_TO_JSON_TYPE = {
    "id": "id",
    "name": "name",
    "xpath": "xpath",
    "cssSelector": "css",
    "className": "classname",
    "linkText": "linktext",
}

# BasePage embeds By.toString() inside a Spanish sentence; the locator value
# is recovered by stripping these known trailing fragments.
TRACE_VALUE_SUFFIXES = (
    " tras el tiempo de espera configurado.",
    " pasado el tiempo de espera configurado",
)

BY_PATTERN = re.compile(r"By\.(cssSelector|className|linkText|xpath|id|name):\s*(.+)$", re.MULTILINE)

FRAMEWORK_EXCEPTION = "FrameworkException"

# Locator JSON contract: "key": {"type": <enum>, "value": "..."}.
ALLOWED_LOCATOR_TYPES = frozenset({"id", "name", "xpath", "css", "classname", "linktext"})
MAX_LOCATOR_VALUE_LENGTH = 500

GITHUB_TOKEN_ENV = "GITHUB_TOKEN"
ANTHROPIC_API_KEY_ENV = "ANTHROPIC_API_KEY"
LLM_TIMEOUT_SECONDS = 60


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
    if not isinstance(data, dict):
        raise ValueError(f"expected a JSON object, got {type(data).__name__}")
    details = data.get("statusDetails")
    if not isinstance(details, dict):
        details = {}
    return ScenarioResult(
        name=data.get("name", ""),
        full_name=data.get("fullName", ""),
        status=data.get("status", ""),
        message=details.get("message", ""),
        trace=details.get("trace", ""),
    )


def load_results(results_dir: Path) -> list[ScenarioResult]:
    """Load every failed/broken Allure result in the directory.

    Per-file isolation: a corrupt, unreadable, or non-object result file is
    skipped with a stderr warning instead of aborting the whole run.
    """
    if not results_dir.is_dir():
        raise FileNotFoundError(f"Allure results directory not found: {results_dir}")
    results = []
    for path in sorted(results_dir.glob(f"*{RESULT_FILE_SUFFIX}")):
        try:
            result = parse_result_file(path)
        except (OSError, ValueError) as exc:
            print(f"[load_results:skip] {path.name}: {exc}", file=sys.stderr)
            continue
        if result.status in {"failed", "broken"}:
            results.append(result)
    return results


@dataclass(frozen=True)
class Classification:
    """Deterministic classification of one failed scenario.

    ``kind`` is ``"locator"`` (healing-eligible) or ``"bug"`` (Slack-only,
    never reaches the LLM). Locator fields are populated only for eligible
    failures whose trace carries a mappable ``By.toString()``.
    """

    kind: str
    scenario: str = ""
    locator_type: str | None = None
    locator_value: str | None = None
    message: str = ""


def classify_trace(trace: str) -> Classification:
    """Classify a stack trace before any LLM call.

    Only ``FrameworkException`` traces that embed a supported Selenium
    ``By.toString()`` are locator-eligible. ``VerificationException`` and any
    other exception — including FrameworkExceptions without a locator (e.g.
    missing locator file) — are real bugs.
    """
    if FRAMEWORK_EXCEPTION not in trace:
        return Classification(kind="bug")
    match = BY_PATTERN.search(trace)
    if not match:
        return Classification(kind="bug")
    by_type, raw_value = match.group(1), match.group(2).strip()
    locator_value = raw_value
    for suffix in TRACE_VALUE_SUFFIXES:
        if locator_value.endswith(suffix):
            locator_value = locator_value[: -len(suffix)].rstrip()
            break
    return Classification(
        kind="locator",
        locator_type=BY_TO_JSON_TYPE[by_type],
        locator_value=locator_value,
    )


def classify_result(result: ScenarioResult) -> Classification:
    """Classify a parsed Allure result, keeping the scenario name."""
    classification = classify_trace(result.trace or result.message)
    return Classification(
        kind=classification.kind,
        scenario=result.name,
        locator_type=classification.locator_type,
        locator_value=classification.locator_value,
        message=result.message,
    )


@dataclass(frozen=True)
class LocatorMatch:
    """One locator entry found while scanning the locators directory."""

    file: str
    type: str
    value: str


@dataclass(frozen=True)
class Validation:
    """Result of validating an LLM proposal against the schema contract."""

    ok: bool
    error: str = ""


def _iter_locator_files(locators_dir: Path):
    """Yield ``(path, entries)`` for each readable locator JSON file.

    Per-file isolation: a corrupt, unreadable, or non-object locator file is
    skipped with a stderr warning instead of aborting the whole run.
    """
    for path in sorted(Path(locators_dir).glob("*.json")):
        try:
            with open(path, encoding="utf-8") as handle:
                entries = json.load(handle)
            if not isinstance(entries, dict):
                raise ValueError(f"expected a JSON object, got {type(entries).__name__}")
        except (OSError, ValueError) as exc:
            print(f"[locators:skip] {path.name}: {exc}", file=sys.stderr)
            continue
        yield path, entries


def find_locator_entries(locators_dir: Path, key: str) -> list[LocatorMatch]:
    """Find every locator entry named ``key`` across all JSON files."""
    matches = []
    for path, entries in _iter_locator_files(locators_dir):
        if key in entries:
            entry = entries[key]
            if not isinstance(entry, dict):
                continue
            matches.append(
                LocatorMatch(file=path.name, type=entry.get("type", ""), value=entry.get("value", ""))
            )
    return matches


def find_keys_by_value(
    locators_dir: Path, locator_type: str, value: str
) -> list[tuple[str, LocatorMatch]]:
    """Reverse-lookup: find every ``(key, match)`` whose type+value equals the
    broken locator extracted from the trace.

    This makes healing independent of LLM key hallucination: when exactly one
    key carries the broken type+value, that key is used directly and the LLM
    only proposes the new value.
    """
    resolved = []
    for path, entries in _iter_locator_files(locators_dir):
        for key, entry in entries.items():
            if not isinstance(entry, dict):
                continue
            if entry.get("type", "") == locator_type and entry.get("value", "") == value:
                resolved.append(
                    (key, LocatorMatch(file=path.name, type=locator_type, value=value))
                )
    return resolved


def validate_proposal(
    proposal: dict,
    *,
    trace_type: str,
    trace_value: str,
    matches: list[LocatorMatch],
) -> Validation:
    """Validate an LLM ``{key, type, value}`` proposal before any file edit.

    The key must exist in exactly one locator file whose type+value matches
    the trace's ``By.toString()``; the proposed type must be in the JSON enum;
    the value must be non-empty, at most 500 chars, and different from the
    old value.
    """
    if len(matches) != 1:
        return Validation(False, f"key must exist in exactly one locator file, found {len(matches)}")
    match = matches[0]
    if match.type != trace_type or match.value != trace_value:
        return Validation(False, "matched locator does not match the trace's By.toString()")
    proposed_type = str(proposal.get("type", "")).strip()
    if proposed_type not in ALLOWED_LOCATOR_TYPES:
        return Validation(False, f"type '{proposed_type}' is not in the locator type enum")
    proposed_value = str(proposal.get("value", "")).strip()
    if not proposed_value:
        return Validation(False, "value must not be empty")
    if len(proposed_value) > MAX_LOCATOR_VALUE_LENGTH:
        return Validation(False, f"value exceeds {MAX_LOCATOR_VALUE_LENGTH} characters")
    if proposed_value == match.value:
        return Validation(False, "value is identical to the old value")
    return Validation(True)


@dataclass(frozen=True)
class LocatorEdit:
    """Record of an applied locator edit; old values feed the PR body."""

    file: str
    key: str
    old_type: str
    old_value: str
    new_type: str
    new_value: str


def apply_locator_edit(
    locators_dir: Path,
    key: str,
    new_type: str,
    new_value: str,
    matches: list[LocatorMatch],
) -> LocatorEdit:
    """Replace one locator entry, returning the edit with old values retained.

    The key must resolve to exactly one file (call ``validate_proposal``
    first); anything else raises to avoid editing an ambiguous locator.
    """
    if len(matches) != 1:
        raise ValueError(f"key '{key}' must match exactly one locator file, found {len(matches)}")
    match = matches[0]
    path = Path(locators_dir) / match.file
    with open(path, encoding="utf-8") as handle:
        entries = json.load(handle)
    entries[key] = {"type": new_type, "value": new_value}
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(entries, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return LocatorEdit(
        file=match.file,
        key=key,
        old_type=match.type,
        old_value=match.value,
        new_type=new_type,
        new_value=new_value,
    )


def quota_cache_key(now: datetime | None = None) -> str:
    """UTC-day cache key shared with the Actions cache (``heal-quota-<date>``).

    No restore-keys are used by the workflow, so a new UTC day is a cache
    miss and the counter resets naturally.
    """
    moment = now or datetime.now(timezone.utc)
    return f"heal-quota-{moment.astimezone(timezone.utc).date().isoformat()}"


def _quota_file(quota_dir: Path, now: datetime | None = None) -> Path:
    return Path(quota_dir) / f"{quota_cache_key(now)}.txt"


def read_quota(quota_dir: Path, now: datetime | None = None) -> int:
    """Read today's attempt count. Eviction/corruption fails open to 0."""
    try:
        return int(_quota_file(quota_dir, now).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 0


def increment_quota(quota_dir: Path, now: datetime | None = None) -> int:
    """Increment today's attempt count and return the new value."""
    path = _quota_file(quota_dir, now)
    path.parent.mkdir(parents=True, exist_ok=True)
    new_count = read_quota(quota_dir, now) + 1
    path.write_text(str(new_count), encoding="utf-8")
    return new_count


def quota_exceeded(quota_dir: Path, max_attempts: int = 3, now: datetime | None = None) -> bool:
    """True when today's attempts already reached ``max_attempts``."""
    return read_quota(quota_dir, now) >= max_attempts


# Fail-open contract: any transport error (URLError/HTTPError/timeout are
# OSError subclasses; IncompleteRead/BadStatusLine/RemoteDisconnected are
# http.client.HTTPException subclasses, NOT OSError) or malformed API
# response shape (KeyError/IndexError/TypeError from response drilling,
# AttributeError when a valid-JSON response is not an object,
# ValueError/JSONDecodeError from payload parsing) degrades the run to
# "unhealed" instead of crashing it.
LLM_FAILURE_EXCEPTIONS = (
    OSError,
    ValueError,
    KeyError,
    IndexError,
    TypeError,
    AttributeError,
    http.client.HTTPException,
)


class GitHubModelsClient:
    """GitHub Models inference API (OpenAI-compatible), auth via GITHUB_TOKEN."""

    endpoint = "https://models.github.ai/inference/chat/completions"
    model = "openai/gpt-4o-mini"

    def __init__(self, token: str) -> None:
        self._token = token

    def build_request(self, prompt: str) -> tuple[dict, dict]:
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        return body, headers

    def complete(self, prompt: str) -> str:
        body, headers = self.build_request(prompt)
        data = _post_json(self.endpoint, body, headers)
        return data["choices"][0]["message"]["content"]


class AnthropicClient:
    """Anthropic Messages API, used when ANTHROPIC_API_KEY is set."""

    endpoint = "https://api.anthropic.com/v1/messages"
    model = "claude-haiku-4-5"
    anthropic_version = "2023-06-01"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def build_request(self, prompt: str) -> tuple[dict, dict]:
        body = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": self.anthropic_version,
            "Content-Type": "application/json",
        }
        return body, headers

    def complete(self, prompt: str) -> str:
        body, headers = self.build_request(prompt)
        data = _post_json(self.endpoint, body, headers)
        return "".join(block.get("text", "") for block in data.get("content", []))


def _post_json(endpoint: str, body: dict, headers: dict) -> dict:
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=LLM_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def get_llm_client(env: dict | None = None):
    """Select the LLM provider.

    GitHub Models is the zero-secret default via ``GITHUB_TOKEN``
    (``models: read`` permission); setting ``ANTHROPIC_API_KEY`` swaps to
    Anthropic. Raises when no credential is available.
    """
    source = os.environ if env is None else env
    anthropic_key = source.get(ANTHROPIC_API_KEY_ENV)
    if anthropic_key:
        return AnthropicClient(anthropic_key)
    github_token = source.get(GITHUB_TOKEN_ENV)
    if github_token:
        return GitHubModelsClient(github_token)
    raise RuntimeError(
        f"no LLM credential available: set {GITHUB_TOKEN_ENV} (GitHub Models) "
        f"or {ANTHROPIC_API_KEY_ENV} (Anthropic)"
    )


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


@dataclass
class Outcome:
    """Result of one healing run, consumed by the workflow via stdout JSON."""

    edit: LocatorEdit | None = None
    proposal: dict | None = None
    validation_error: str = ""
    bugs: list[Classification] = field(default_factory=list)
    pending: list[Classification] = field(default_factory=list)
    quota_blocked: bool = False
    quota_count: int = 0
    dry_run: bool = False


def extract_json_object(text: str) -> dict:
    """Extract the first JSON object from an LLM response.

    Tolerates surrounding prose and Markdown code fences.
    """
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("LLM response contains no JSON object")
    return json.loads(text[start : end + 1])


def build_llm_prompt(classification: Classification, dom: str, message: str) -> str:
    """Build the healing prompt: broken locator, failure message, DOM context."""
    return (
        "A Selenium test failed because a locator no longer matches the DOM.\n"
        f"Scenario: {classification.scenario}\n"
        f"Broken locator type: {classification.locator_type}\n"
        f"Broken locator value: {classification.locator_value}\n"
        f"Failure message: {message}\n\n"
        "Current DOM:\n"
        f"{dom}\n\n"
        "Propose a replacement locator that uniquely matches the same element.\n"
        'Respond with ONLY a JSON object: {"key": "<locator key>", '
        '"type": "id|name|xpath|css|classname|linktext", "value": "<new locator>"}.\n'
        f'The key must be "{classification.scenario}"\'s broken locator key if known, '
        "otherwise your best candidate."
    )


def run(
    args: argparse.Namespace,
    llm_client=None,
    notifier: SlackNotifier | None = None,
    now: datetime | None = None,
) -> Outcome:
    """Orchestrate classification -> quota gate -> LLM -> validate -> edit.

    ``llm_client`` and ``notifier`` are injection seams for tests; in
    production they resolve from the environment. Dry-run never edits files
    and never resolves a real client. Only one failure is healed per run
    (first eligible, lexical order); extra eligible failures are reported as
    pending. The quota is consumed by the workflow via ``--quota-increment``
    only after a verified green re-run.
    """
    notifier = notifier or SlackNotifier.from_env()

    if args.quota_increment:
        count = increment_quota(Path(args.quota_dir), now)
        return Outcome(quota_count=count)

    outcome = Outcome(dry_run=args.dry_run)
    results = load_results(Path(args.allure_results))
    classifications = [classify_result(result) for result in results]

    outcome.bugs = [c for c in classifications if c.kind == "bug"]
    for bug in outcome.bugs:
        notifier.notify(
            f"Auto-heal: real bug detected (no fix attempted). "
            f"Scenario: {bug.scenario}. Exception: {bug.message}"
        )

    eligible = sorted(
        (c for c in classifications if c.kind == "locator"), key=lambda c: c.scenario
    )
    if not eligible:
        return outcome

    candidate, outcome.pending = eligible[0], eligible[1:]
    for extra in outcome.pending:
        notifier.notify(
            f"Auto-heal: locator failure pending (one heal per run). Scenario: {extra.scenario}."
        )

    if quota_exceeded(Path(args.quota_dir), max_attempts=args.max_attempts, now=now):
        outcome.quota_blocked = True
        notifier.notify(
            f"Auto-heal: daily quota of {args.max_attempts} healing attempts reached. "
            f"Scenario left unhealed: {candidate.scenario}."
        )
        return outcome

    dom = ""
    if args.dom_file and Path(args.dom_file).is_file():
        dom = Path(args.dom_file).read_text(encoding="utf-8")
    prompt = build_llm_prompt(candidate, dom, candidate.message)

    if args.dry_run and llm_client is None:
        print(f"[dry-run] would call LLM with prompt:\n{prompt}")
        return outcome

    client = llm_client or get_llm_client()
    try:
        outcome.proposal = extract_json_object(client.complete(prompt))
    except LLM_FAILURE_EXCEPTIONS as exc:
        outcome.validation_error = f"LLM call failed: {exc}"
        notifier.notify(
            f"Auto-heal: unhealed locator failure. Scenario: {candidate.scenario}. "
            f"Reason: {outcome.validation_error}"
        )
        return outcome

    # Deterministic key resolution: when exactly one locator key carries the
    # broken type+value extracted from the trace, use it directly (the LLM
    # only proposes the new value). Zero or ambiguous reverse matches fall
    # back to the LLM-proposed key path; the validation gate below is intact
    # for both paths.
    resolved = find_keys_by_value(
        Path(args.locators_dir), candidate.locator_type, candidate.locator_value
    )
    if len(resolved) == 1:
        key, match = resolved[0]
        outcome.proposal["key"] = key
        matches = [match]
    else:
        matches = find_locator_entries(
            Path(args.locators_dir), str(outcome.proposal.get("key", ""))
        )
    validation = validate_proposal(
        outcome.proposal,
        trace_type=candidate.locator_type,
        trace_value=candidate.locator_value,
        matches=matches,
    )
    if not validation.ok:
        outcome.validation_error = validation.error
        notifier.notify(
            f"Auto-heal: unhealed locator failure. Scenario: {candidate.scenario}. "
            f"Reason: {validation.error}"
        )
        return outcome

    if args.dry_run:
        print(f"[dry-run] validated proposal: {outcome.proposal}")
        return outcome

    outcome.edit = apply_locator_edit(
        Path(args.locators_dir),
        str(outcome.proposal["key"]),
        str(outcome.proposal["type"]).strip(),
        str(outcome.proposal["value"]).strip(),
        matches,
    )
    return outcome


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    outcome = run(args)
    summary = {
        "healed": outcome.edit is not None,
        "edit": outcome.edit.__dict__ if outcome.edit else None,
        "proposal": outcome.proposal,
        "validation_error": outcome.validation_error,
        "bugs": [bug.scenario for bug in outcome.bugs],
        "pending": [extra.scenario for extra in outcome.pending],
        "quota_blocked": outcome.quota_blocked,
        "quota_count": outcome.quota_count,
        "dry_run": outcome.dry_run,
    }
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
