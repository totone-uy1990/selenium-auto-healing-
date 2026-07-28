# Tasks: Auto-Healing Pipeline

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~900–1100 authored (bootstrap copy excluded as vendored) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 (stacked-to-main) |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Bootstrap + CI plumbing | PR 1 (base: main) | `./gradlew clean compileTestJava` | `./gradlew test -Dcucumber.filter.tags=@Smoke` (N/A if no tag exists — use smallest feature) | `tests.yml` edits, `TestRunner.java` plugin, gemini deletion; bootstrap revert = delete repo files |
| 2 | Healing engine + tests | PR 2 (base: main) | `pytest scripts/tests/ -q` | `pytest scripts/tests/test_integration.py` (fixture DOM → edit) | `scripts/heal_locator.py` + `scripts/tests/` only |
| 3 | Healing workflow + docs | PR 3 (base: main) | `python -c "import yaml; yaml.safe_load(open('.github/workflows/auto-heal.yml'))"` | Manual E2E checklist (docs) | `.github/workflows/auto-heal.yml`, `docs/`, `.agent/` |

## Phase 1: Bootstrap and CI Plumbing (PR 1)

- [x] 1.1 Copy full framework from `/home/ronal/Escritorio/Opencode-QA-Core-Selenium` into repo root (read-only source; exclude `.git/`); verify `./gradlew clean compileTestJava` passes
- [x] 1.2 Modify `.github/workflows/tests.yml`: add two `actions/upload-artifact@v4` steps (`build/allure-results`, `build/debug-artifacts`) each with `if: failure()`; remove all Gemini diagnose steps
- [x] 1.3 Delete `scripts/gemini_diagnose.py`
- [x] 1.4 Modify `src/test/java/runner/TestRunner.java`: add `rerun:build/rerun.txt` to `PLUGIN_PROPERTY_NAME` annotation
- [x] 1.5 RED test: assert `-Dcucumber.features="@build/rerun.txt"` (no `clean`) re-runs only failed scenarios; if annotation wins, assert `-Dcucumber.filter.name` fallback path works
- [x] 1.6 Verify: `./gradlew test -Dcucumber.features="@build/rerun.txt" -Dcucumber.execution.parallel.enabled=false`

## Phase 2: Healing Engine (PR 2)

- [x] 2.1 Create `scripts/heal_locator.py` skeleton: arg parsing, `*-result.json` trace parser, Slack notifier (webhook from env only)
- [x] 2.2 RED: pytest classifier fixtures — `FrameworkException` → eligible + extract `By.toString()` type/value; `VerificationException`/other → bug, no LLM call
- [x] 2.3 GREEN: implement deterministic classifier in `heal_locator.py`
- [x] 2.4 RED: pytest schema validation — accept valid `{key,type,value}`; reject unknown key, wrong type enum, empty/>500-char value, value == old
- [x] 2.5 GREEN: implement `get_llm_client()` (GitHub Models default via `GITHUB_TOKEN`; Anthropic swap when `ANTHROPIC_API_KEY` set) + schema validator
- [x] 2.6 Implement locator JSON edit: match key in exactly one file under `src/test/resources/locators/`, retain old value for PR body
- [x] 2.7 RED: pytest quota counter — UTC-day cache key `heal-quota-<date>`, max 3, over-quota → Slack-only, eviction fails open
- [x] 2.8 GREEN: implement quota read/increment via Actions cache file
- [x] 2.9 Integration: LLM (mocked/fixture) → validated edit on fixture DOM; end-to-end script dry-run on fixture result JSONs

## Phase 3: Workflow, Docs, and Validation (PR 3)

- [x] 3.1 Create `.github/workflows/auto-heal.yml`: `workflow_run` on tests.yml `[completed]`, job `if: conclusion == 'failure'`; fork gate `head_repository.full_name == github.repository`; `concurrency: auto-heal` (no cancel); minimal permissions (`contents: write`, `pull-requests: write`, `actions: read`, `models: read`)
- [x] 3.2 Add steps: cross-run `actions/download-artifact@v4` (run-id + github-token), checkout `head_sha`, quota gate, run `heal_locator.py`, re-run gradle command (`-Dcucumber.filter.name` from `scripts/build_rerun_filter.py`, serial, no clean), green → branch `auto-heal/<key>-<sha8>` + `gh pr create --head/--base` explicit (via `scripts/deliver_healing.sh`) + Slack + quota++; red → `git restore` + Slack; extras → Slack "pending"
- [x] 3.3 RED→GREEN (threat matrix): `scripts/tests/test_deliver_healing.py` (behavioral git harness: staged diff = exactly one locator JSON, push targets healing branch only, PR head/base explicit, extra staged changes abort) + `scripts/tests/test_auto_heal_workflow.py` (checkout pins failing SHA, fork gate, permissions, no SLACK in re-run env)
- [x] 3.4 Create `docs/auto-healing-setup.md`: secrets (`SLACK_WEBHOOK_URL`, optional `ANTHROPIC_API_KEY`), permissions, <15-min quick path, pytest note, GitHub Models rate-limit assumption + Slack fallback
- [x] 3.5 Create `.agent/skills/locator-healing-specialist/SKILL.md` (optional LLM prompt context)
- [x] 3.6 E2E manual checklist: `docs/auto-healing-e2e-checklist.md` (break locator → single-file JSON PR; break assertion → Slack-only; optional quota case). Manual only — no live E2E attempted
- [x] 3.7 Resolve open questions: `-Dcucumber.features` precedence RESOLVED in Slice 1 (rerun via `-Dcucumber.filter.name`); GitHub Models free-tier assumption + Slack fallback documented in setup doc (design.md open questions all [x])
