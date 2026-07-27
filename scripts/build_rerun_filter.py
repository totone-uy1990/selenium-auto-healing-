#!/usr/bin/env python3
"""Build a ``-Dcucumber.filter.name`` value from Allure ``*-result.json`` files.

The ``-Dcucumber.features="@build/rerun.txt"`` rerun-file syntax is rejected
by the Cucumber JUnit Platform engine (see design.md, Slice 1 finding), so
the healing workflow re-runs failed scenarios by exact name instead. This
script collects the names of every failed/broken result, regex-escapes them
(``cucumber.filter.name`` is a regex), and prints them joined by ``|`` —
Cucumber's union semantics for exact-name matching. Stdlib only.
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


def build_filter(results_dir: Path) -> str:
    """Return the regex-escaped, ``|``-joined scenario-name filter."""
    return "|".join(re.escape(name) for name in failed_scenario_names(results_dir))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    print(build_filter(Path(args.allure_results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
