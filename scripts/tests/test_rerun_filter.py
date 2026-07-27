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
