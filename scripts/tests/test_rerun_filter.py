"""Tests for scripts/build_rerun_filter.py.

The workflow re-runs failed scenarios with -Dcucumber.filter.name (the
@cucumber.features rerun-file syntax is broken on the JUnit Platform engine,
see design.md). This builder parses the Allure *-result.json traces into an
exact, regex-escaped scenario-name filter.
"""

import json
import re
import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build_rerun_filter  # noqa: E402

SCRIPT = Path(__file__).resolve().parent.parent / "build_rerun_filter.py"


def _write_result(directory: Path, name: str, status: str) -> Path:
    payload = {"name": name, "fullName": f"com.qa.{name}", "status": status}
    path = directory / f"{uuid.uuid4()}-result.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_failed_and_broken_names_are_collected_sorted(tmp_path: Path) -> None:
    results = tmp_path / "allure-results"
    results.mkdir()
    _write_result(results, "Zulu scenario fails", "failed")
    _write_result(results, "Alpha scenario breaks", "broken")
    _write_result(results, "Passing scenario", "passed")

    expected = f"{re.escape('Alpha scenario breaks')}|{re.escape('Zulu scenario fails')}"
    assert build_rerun_filter.build_filter(results) == expected


def test_regex_metacharacters_are_escaped(tmp_path: Path) -> None:
    results = tmp_path / "allure-results"
    results.mkdir()
    _write_result(results, "Login (admin) [fast] v2.0", "failed")

    filter_value = build_rerun_filter.build_filter(results)
    # Every regex metacharacter must be escaped so cucumber.filter.name
    # matches the exact scenario name instead of treating it as a pattern.
    for char in "().[]":
        assert f"\\{char}" in filter_value
    assert "v2\\.0" in filter_value


def test_no_failures_produce_empty_filter(tmp_path: Path) -> None:
    results = tmp_path / "allure-results"
    results.mkdir()
    _write_result(results, "Passing scenario", "passed")

    assert build_rerun_filter.build_filter(results) == ""


def test_corrupt_result_file_is_skipped(tmp_path: Path) -> None:
    results = tmp_path / "allure-results"
    results.mkdir()
    _write_result(results, "Real failure", "failed")
    (results / f"{uuid.uuid4()}-result.json").write_text("{not json", encoding="utf-8")

    assert re.escape("Real failure") in build_rerun_filter.build_filter(results)


def test_missing_directory_raises(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(FileNotFoundError):
        build_rerun_filter.build_filter(tmp_path / "does-not-exist")


def test_cli_prints_filter_to_stdout(tmp_path: Path) -> None:
    results = tmp_path / "allure-results"
    results.mkdir()
    _write_result(results, "CLI failure scenario", "failed")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--allure-results", str(results)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert completed.stdout.strip() == re.escape("CLI failure scenario")


def _write_summary(path: Path, healed: bool, scenario: str = "") -> Path:
    summary_path = path / "heal-summary.json"
    summary_path.write_text(
        json.dumps({"healed": healed, "scenario": scenario}), encoding="utf-8"
    )
    return summary_path


def test_summary_mode_filters_to_healed_scenario_only(tmp_path: Path) -> None:
    """G1: with 2 failed scenarios (1 healed locator + 1 bug), the filter
    must contain ONLY the healed scenario — re-running the unhealed bug
    failure would keep the verification red forever and deadlock delivery.
    """
    results = tmp_path / "allure-results"
    results.mkdir()
    _write_result(results, "Healed locator scenario", "failed")
    _write_result(results, "Real bug scenario", "broken")
    summary = _write_summary(tmp_path, healed=True, scenario="Healed locator scenario")

    assert build_rerun_filter.build_filter(results, summary) == re.escape(
        "Healed locator scenario"
    )


def test_summary_mode_single_healed_failure(tmp_path: Path) -> None:
    results = tmp_path / "allure-results"
    results.mkdir()
    _write_result(results, "Only failure, now healed", "failed")
    summary = _write_summary(tmp_path, healed=True, scenario="Only failure, now healed")

    assert build_rerun_filter.build_filter(results, summary) == re.escape(
        "Only failure, now healed"
    )


def test_summary_mode_without_heal_produces_empty_filter(tmp_path: Path) -> None:
    """G1: nothing healed -> empty filter, so the workflow skips the re-run
    gracefully and never delivers an unverified edit."""
    results = tmp_path / "allure-results"
    results.mkdir()
    _write_result(results, "Still broken scenario", "broken")
    summary = _write_summary(tmp_path, healed=False)

    assert build_rerun_filter.build_filter(results, summary) == ""


def test_summary_mode_rejects_scenario_absent_from_failed_results(tmp_path: Path) -> None:
    """A stale/mismatched summary must never produce a filter for a scenario
    that did not actually fail in these Allure results."""
    results = tmp_path / "allure-results"
    results.mkdir()
    _write_result(results, "Actual failure", "failed")
    summary = _write_summary(tmp_path, healed=True, scenario="Ghost scenario")

    assert build_rerun_filter.build_filter(results, summary) == ""


def test_summary_mode_corrupt_summary_produces_empty_filter(tmp_path: Path) -> None:
    results = tmp_path / "allure-results"
    results.mkdir()
    _write_result(results, "Actual failure", "failed")
    summary = tmp_path / "heal-summary.json"
    summary.write_text("{not json", encoding="utf-8")

    assert build_rerun_filter.build_filter(results, summary) == ""


def test_cli_summary_mode_prints_healed_only_filter(tmp_path: Path) -> None:
    results = tmp_path / "allure-results"
    results.mkdir()
    _write_result(results, "Healed via CLI", "failed")
    _write_result(results, "Unhealed bug", "failed")
    summary = _write_summary(tmp_path, healed=True, scenario="Healed via CLI")

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--allure-results",
            str(results),
            "--summary",
            str(summary),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert completed.stdout.strip() == re.escape("Healed via CLI")
