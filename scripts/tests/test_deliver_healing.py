"""Threat-matrix tests for scripts/deliver_healing.sh (design.md).

Behavioral harness: each test runs the delivery script against a real
temporary git repository with a bare ``origin`` and a fake ``gh`` CLI that
records its argv. This verifies, not just string-matches, the four threat
boundaries:

- Commit state: the pushed commit contains exactly one locator JSON file.
- Push state: the push targets the healing branch only.
- PR commands: ``gh pr create`` receives explicit ``--head``/``--base``.
- Guard: extra staged changes abort the delivery with no push and no PR.
"""

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "deliver_healing.sh"

LOCATOR_REL = "src/test/resources/locators/login.json"
BRANCH = "auto-heal/userNameField-deadbeef"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )


@pytest.fixture
def harness(tmp_path: Path) -> dict:
    """A git repo with a healing edit plus an unrelated dirty file, a bare
    origin, and a fake ``gh`` binary that logs invocations."""
    repo = tmp_path / "repo"
    (repo / Path(LOCATOR_REL).parent).mkdir(parents=True)
    locator = repo / LOCATOR_REL
    locator.write_text(
        json.dumps({"userNameField": {"type": "xpath", "value": "//old"}}, indent=2) + "\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text("fixture repo\n", encoding="utf-8")
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "heal@example.com")
    _git(repo, "config", "user.name", "Auto Heal")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "initial")

    origin = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "--bare", str(origin)], capture_output=True, check=True
    )
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-u", "origin", "main")

    # The healing edit + an unrelated dirty file that must NOT be delivered.
    locator.write_text(
        json.dumps({"userNameField": {"type": "xpath", "value": "//new"}}, indent=2) + "\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text("unrelated local change\n", encoding="utf-8")

    gh_log = tmp_path / "gh_calls.log"
    gh_argv_log = tmp_path / "gh_argv.log"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    gh = fake_bin / "gh"
    gh.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "$@" >> "{gh_log}"\n'
        # Per-token argv log: lets tests verify flags and values arrive as
        # separate argv tokens (no shell composition).
        f'printf "%s\\n" "$@" >> "{gh_argv_log}"\n'
        "echo 'https://example.com/pull/42'\n",
        encoding="utf-8",
    )
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)

    body_file = tmp_path / "pr_body.md"
    body_file.write_text("Heals `userNameField`: `//old` -> `//new`.\n", encoding="utf-8")

    env = dict(os.environ)
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    return {
        "repo": repo,
        "origin": origin,
        "gh_log": gh_log,
        "gh_argv_log": gh_argv_log,
        "body_file": body_file,
        "env": env,
    }


def _run_delivery(harness: dict, *extra_args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--branch",
            BRANCH,
            "--base",
            "main",
            "--edit-file",
            LOCATOR_REL,
            "--title",
            "fix(locators): heal userNameField",
            "--body-file",
            str(harness["body_file"]),
            *extra_args,
        ],
        cwd=harness["repo"],
        env=harness["env"],
        capture_output=True,
        text=True,
    )


def test_pushed_commit_contains_exactly_one_locator_json_file(harness: dict) -> None:
    completed = _run_delivery(harness)
    assert completed.returncode == 0, completed.stderr

    changed = _git(
        harness["repo"], "diff", "--name-only", f"main...{BRANCH}"
    ).stdout.splitlines()
    assert changed == [LOCATOR_REL]
    # The unrelated dirty file stays uncommitted on the working tree.
    status = _git(harness["repo"], "status", "--porcelain").stdout
    assert "README.md" in status


def test_push_targets_healing_branch_only(harness: dict) -> None:
    completed = _run_delivery(harness)
    assert completed.returncode == 0, completed.stderr

    refs = _git(
        harness["origin"], "for-each-ref", "--format=%(refname)"
    ).stdout.splitlines()
    assert refs == ["refs/heads/" + BRANCH, "refs/heads/main"]


def test_pr_create_uses_explicit_head_and_base(harness: dict) -> None:
    completed = _run_delivery(harness)
    assert completed.returncode == 0, completed.stderr

    calls = harness["gh_log"].read_text(encoding="utf-8").splitlines()
    pr_calls = [line for line in calls if line.startswith("pr create")]
    assert len(pr_calls) == 1
    call = pr_calls[0]
    assert f"--head {BRANCH}" in call
    assert "--base main" in call
    assert "--title" in call
    assert "--body-file" in call

    # Real argv contract (G4): --head/--base and their values are separate
    # argv tokens — no shell composition such as a single "--head X --base Y"
    # token (which unquoted expansion like `gh pr create $FLAGS` would produce).
    tokens = harness["gh_argv_log"].read_text(encoding="utf-8").splitlines()
    assert tokens[0:2] == ["pr", "create"]
    head_index = tokens.index("--head")
    assert tokens[head_index + 1] == BRANCH
    base_index = tokens.index("--base")
    assert tokens[base_index + 1] == "main"
    # No token merges a flag with its value or both flags into one string.
    assert not any(token.startswith(("--head ", "--base ")) for token in tokens)
    assert not any("--head" in token and "--base" in token for token in tokens)


def test_pre_staged_extra_changes_abort_without_push_or_pr(harness: dict) -> None:
    repo = harness["repo"]
    extra = repo / "src" / "test" / "resources" / "locators" / "other.json"
    extra.write_text("{}\n", encoding="utf-8")
    _git(repo, "add", "src/test/resources/locators/other.json")

    completed = _run_delivery(harness)
    assert completed.returncode != 0

    # Nothing was pushed: origin still has only main.
    refs = _git(
        harness["origin"], "for-each-ref", "--format=%(refname)"
    ).stdout.splitlines()
    assert refs == ["refs/heads/main"]
    # No PR was created.
    assert not harness["gh_log"].exists() or "pr create" not in harness[
        "gh_log"
    ].read_text(encoding="utf-8")


def test_missing_edit_file_aborts(harness: dict) -> None:
    completed = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--branch",
            BRANCH,
            "--base",
            "main",
            "--edit-file",
            "src/test/resources/locators/does-not-exist.json",
            "--title",
            "fix(locators): heal nothing",
            "--body-file",
            str(harness["body_file"]),
        ],
        cwd=harness["repo"],
        env=harness["env"],
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
