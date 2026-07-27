#!/usr/bin/env python3
"""Build a ``-Dcucumber.filter.name`` value from Allure ``*-result.json`` files.

The ``-Dcucumber.features="@build/rerun.txt"`` rerun-file syntax is rejected
by the Cucumber JUnit Platform engine (see design.md, Slice 1 finding), so
the healing workflow re-runs failed scenarios by exact name instead. This
script collects the names of every failed/broken result, regex-escapes them
(``cucumber.filter.name`` is a regex), and prints them joined by ``|`` —
Cucumber's union semantics for exact-name matching. Stdlib only.

Two modes:

- Default (``--allure-results`` only): every failed/broken scenario.
- ``--summary <heal-summary.json>``: ONLY the scenario the healing engine
  actually healed in this run. The engine heals at most one locator failure
  per run; re-running unhealed bug/pending failures would keep the
  verification red at the same SHA and deadlock delivery forever (G1).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RESULT_FILE_SUFFIX = "-result.json"
FAILED_STATUSES = {"failed", "broken"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print a cucumber.filter.name regex for failed Allure scenarios."
    )
    parser.add_argument(
        "--allure-results",
        required=True,
        help="Directory containing Allure *-result.json files.",
    )
    parser.add_argument(
        "--summary",
        default=None,
        help="Healing engine summary JSON (stdout contract of heal_locator.py). "
        "When given, the filter contains ONLY the healed scenario.",
    )
    return parser.parse_args(argv)


def failed_scenario_names(results_dir: Path) -> list[str]:
    """Collect sorted names of failed/broken results.

    Per-file isolation: a corrupt, unreadable, or non-object result file is
    skipped with a stderr warning instead of aborting the run.
    """
    results_dir = Path(results_dir)
    if not results_dir.is_dir():
        raise FileNotFoundError(f"Allure results directory not found: {results_dir}")
    names = []
    for path in sorted(results_dir.glob(f"*{RESULT_FILE_SUFFIX}")):
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                raise ValueError(f"expected a JSON object, got {type(data).__name__}")
        except (OSError, ValueError) as exc:
            print(f"[rerun-filter:skip] {path.name}: {exc}", file=sys.stderr)
            continue
        if data.get("status") in FAILED_STATUSES and data.get("name"):
            names.append(str(data["name"]))
    return sorted(names)


def healed_scenario_name(summary_path: Path) -> str:
    """Read the engine summary JSON and return the healed scenario name.

    Fail-open: a missing, unreadable, or corrupt summary yields an empty
    name (and therefore an empty filter) so the workflow skips the re-run
    instead of falling back to re-running every failure.
    """
    summary_path = Path(summary_path)
    try:
        with open(summary_path, encoding="utf-8") as handle:
            summary = json.load(handle)
        if not isinstance(summary, dict):
            raise ValueError(f"expected a JSON object, got {type(summary).__name__}")
    except (OSError, ValueError) as exc:
        print(f"[rerun-filter:skip] {summary_path.name}: {exc}", file=sys.stderr)
        return ""
    if not summary.get("healed"):
        return ""
    return str(summary.get("scenario") or "")


def build_filter(results_dir: Path, summary_path: Path | None = None) -> str:
    """Return the regex-escaped, ``|``-joined scenario-name filter.

    With ``summary_path``, the filter contains ONLY the scenario the engine
    healed — and only when that scenario actually failed in these results
    (a stale summary must never fabricate a re-run target).
    """
    if summary_path is None:
        return "|".join(re.escape(name) for name in failed_scenario_names(results_dir))
    healed = healed_scenario_name(summary_path)
    if not healed or healed not in failed_scenario_names(results_dir):
        return ""
    return re.escape(healed)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = Path(args.summary) if args.summary else None
    print(build_filter(Path(args.allure_results), summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
