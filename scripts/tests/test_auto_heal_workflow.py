"""Structural assertions for .github/workflows/auto-heal.yml.

These checks encode the parts of the design.md threat matrix and security
contract that live in workflow YAML and cannot be executed locally:

- Git repository selection: checkout pins the failing run's ``head_sha``.
- Fork safety gate + failure-only job condition.
- Minimal permissions and serialized concurrency.
- The gradle re-run step never receives ``SLACK_WEBHOOK_URL`` (design.md
  line 60) and uses ``-Dcucumber.filter.name`` (never ``cucumber.features``).
"""

from pathlib import Path
import re

import pytest
import yaml

WORKFLOW_PATH = (
    Path(__file__).resolve().parent.parent.parent / ".github" / "workflows" / "auto-heal.yml"
)


@pytest.fixture(scope="module")
def workflow() -> dict:
    with open(WORKFLOW_PATH, encoding="utf-8") as handle:
        doc = yaml.safe_load(handle)
    assert isinstance(doc, dict), "auto-heal.yml must parse to a mapping"
    return doc


def _trigger(workflow: dict) -> dict:
    # PyYAML (YAML 1.1) parses the bare key `on` as boolean True.
    return workflow.get("on") or workflow.get(True)


def _steps(workflow: dict) -> list[dict]:
    jobs = workflow["jobs"]
    assert len(jobs) == 1, "exactly one job expected"
    return next(iter(jobs.values()))["steps"]


def _find_step(steps: list[dict], predicate) -> dict:
    for step in steps:
        if predicate(step):
            return step
    raise AssertionError("no step matched the predicate")


def test_workflow_run_trigger_on_tests_completed(workflow: dict) -> None:
    trigger = _trigger(workflow)
    workflow_run = trigger["workflow_run"]
    assert "Run tests and publish report" in workflow_run["workflows"]
    assert "completed" in workflow_run["types"]


def test_concurrency_serializes_without_cancel(workflow: dict) -> None:
    concurrency = workflow["concurrency"]
    assert concurrency["group"] == "auto-heal"
    assert concurrency["cancel-in-progress"] is False


def test_minimal_permissions(workflow: dict) -> None:
    assert workflow["permissions"] == {
        "contents": "write",
        "pull-requests": "write",
        "actions": "read",
        "models": "read",
    }


def test_job_condition_failure_only_and_fork_gate(workflow: dict) -> None:
    job = next(iter(workflow["jobs"].values()))
    condition = job["if"]
    assert "github.event.workflow_run.conclusion == 'failure'" in condition
    assert "github.event.workflow_run.head_repository.full_name == github.repository" in condition
    # Both clauses must be ANDed: a forked failure must not heal.
    assert "&&" in condition


def test_checkout_pins_failing_head_sha(workflow: dict) -> None:
    steps = _steps(workflow)
    checkout = _find_step(steps, lambda s: str(s.get("uses", "")).startswith("actions/checkout@"))
    assert checkout["with"]["ref"] == "${{ github.event.workflow_run.head_sha }}"


def test_cross_run_artifact_download(workflow: dict) -> None:
    steps = _steps(workflow)
    downloads = [
        s for s in steps if str(s.get("uses", "")).startswith("actions/download-artifact@")
    ]
    names = {d["with"]["name"] for d in downloads}
    assert {"allure-results", "debug-artifacts"} <= names
    for step in downloads:
        assert step["with"]["run-id"] == "${{ github.event.workflow_run.id }}"
        assert step["with"]["github-token"] == "${{ secrets.GITHUB_TOKEN }}"


def test_quota_cache_uses_utc_day_key(workflow: dict) -> None:
    """UTC-day quota over actions/cache.

    actions/cache entries are immutable per key: re-saving the same key on
    the day's second heal would fail and silently reset the quota (breaking
    the Cost Guard spec requirement). The workflow therefore saves with a
    run-unique key under the UTC-day prefix and restores by that prefix —
    same-day restores pick the latest counter, a new day is a prefix miss.
    """
    steps = _steps(workflow)
    restores = [s for s in steps if str(s.get("uses", "")).startswith("actions/cache/restore@")]
    saves = [s for s in steps if str(s.get("uses", "")).startswith("actions/cache/save@")]
    assert restores, "quota restore step missing"
    assert saves, "quota save step missing"
    restore = restores[0]
    assert "heal-quota-" in restore["with"]["key"]
    restore_keys = restore["with"]["restore-keys"]
    assert "heal-quota-" in restore_keys, "day-prefix restore-keys required for same-day re-reads"
    save = saves[0]
    assert "heal-quota-" in save["with"]["key"]
    assert "run_id" in save["with"]["key"], "save key must be unique per run (cache is immutable)"


def test_heal_engine_step_invokes_script_with_slack(workflow: dict) -> None:
    steps = _steps(workflow)
    engine = _find_step(
        steps, lambda s: "scripts/heal_locator.py" in str(s.get("run", ""))
    )
    assert engine["env"]["SLACK_WEBHOOK_URL"] == "${{ secrets.SLACK_WEBHOOK_URL }}"
    assert "GITHUB_TOKEN" in engine["env"]


def test_gradle_rerun_step_contract(workflow: dict) -> None:
    steps = _steps(workflow)
    rerun = _find_step(
        steps,
        lambda s: "./gradlew" in str(s.get("run", "")) and "filter.name" in str(s.get("run", "")),
    )
    run_cmd = rerun["run"]
    assert "-Dcucumber.filter.name" in run_cmd
    assert "-Dcucumber.execution.parallel.enabled=false" in run_cmd
    assert "-Dcucumber.features" not in run_cmd
    assert "clean" not in run_cmd
    # design.md line 60: SLACK_WEBHOOK_URL must never reach the re-run env.
    assert "SLACK_WEBHOOK_URL" not in rerun.get("env", {})


def test_slack_webhook_is_never_job_level_env(workflow: dict) -> None:
    job = next(iter(workflow["jobs"].values()))
    assert "SLACK_WEBHOOK_URL" not in job.get("env", {})
    assert "SLACK_WEBHOOK_URL" not in workflow.get("env", {})


def test_delivery_step_uses_delivery_script(workflow: dict) -> None:
    steps = _steps(workflow)
    _find_step(steps, lambda s: "scripts/deliver_healing.sh" in str(s.get("run", "")))


def test_rerun_filter_is_built_from_allure_results(workflow: dict) -> None:
    steps = _steps(workflow)
    _find_step(steps, lambda s: "scripts/build_rerun_filter.py" in str(s.get("run", "")))


def test_rerun_filter_targets_healed_scenario_only(workflow: dict) -> None:
    """G1: the engine heals at most one failure per run; the verification
    re-run must filter to ONLY the healed scenario from the engine summary,
    or unhealed bug/pending failures keep the re-run red forever."""
    steps = _steps(workflow)
    build = _find_step(
        steps, lambda s: "scripts/build_rerun_filter.py" in str(s.get("run", ""))
    )
    assert "--summary heal-summary.json" in build["run"]


def test_rerun_step_requires_nonempty_filter(workflow: dict) -> None:
    """G1: with nothing healed the filter is empty; the re-run must then be
    skipped gracefully (never run the whole suite, never deliver)."""
    steps = _steps(workflow)
    rerun = _find_step(
        steps,
        lambda s: "./gradlew" in str(s.get("run", "")) and "filter.name" in str(s.get("run", "")),
    )
    condition = str(rerun.get("if", ""))
    assert "steps.heal.outputs.healed == 'true'" in condition
    assert "steps.rerun.outputs.filter != ''" in condition


def test_red_rerun_restores_locator_file(workflow: dict) -> None:
    steps = _steps(workflow)
    _find_step(
        steps,
        lambda s: "git restore" in str(s.get("run", ""))
        and "src/test/resources/locators" in str(s.get("run", "")),
    )


def test_github_output_uses_heredoc_for_multiline_safe_writes(workflow: dict) -> None:
    """G2: heal-step outputs include LLM-influenced old_value/new_value
    (validate_proposal allows newlines up to 500 chars), so the single-line
    ``name=value`` GITHUB_OUTPUT form would corrupt them. The workflow must
    use the heredoc delimiter form (``name<<delimiter`` / value / delimiter)
    per GitHub docs."""
    steps = _steps(workflow)
    engine = _find_step(
        steps, lambda s: "scripts/heal_locator.py" in str(s.get("run", ""))
    )
    run_script = engine["run"]
    assert "GITHUB_OUTPUT" in run_script
    # Heredoc delimiter form: every output is written as name<<DELIMITER.
    assert re.search(r"\w+\}?<<", run_script), (
        "outputs must use the heredoc delimiter form for multiline safety"
    )
    # The vulnerable single-line form must be gone.
    assert 'f"{name}={value}' not in run_script
