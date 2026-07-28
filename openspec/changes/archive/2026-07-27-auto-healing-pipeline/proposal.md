# Proposal: Auto-Healing Pipeline

## Intent

Pipeline 1 failures caused by stale locators currently require manual triage and produce only a diagnosis message (Gemini script). This change replaces that script with an automated healing system that detects locator failures, proposes a fix via LLM, verifies it by re-running failed scenarios, and delivers the fix as a human-reviewed PR with a Slack notification.

## Scope

### In Scope
- Bootstrap: copy full framework from `/home/ronal/Escritorio/Opencode-QA-Core-Selenium` into `/home/ronal/Escritorio/selenium-auto-healing-`.
- Modify `tests.yml` (Pipeline 1): upload `build/allure-results` + `build/debug-artifacts` as workflow artifacts on failure.
- New `.github/workflows/auto-heal.yml` (`workflow_run` trigger): downloads artifacts cross-run, checks out the failing commit SHA.
- New `scripts/heal_locator.py`: parses allure-results JSON, deterministic classification (`FrameworkException` = locator → heal; anything else = real bug → Slack only), LLM call, JSON locator edit, validation.
- Cucumber rerun support (`rerun:build/rerun.txt` plugin) to re-run only failed scenarios; `-Dcucumber.filter.name` fallback.
- Verification gate: healing PR created ONLY if re-run of failed scenarios passes at the failing SHA.
- Auto-PR + Slack notification (locator key, old → new value, PR link). No auto-merge; human reviews.
- LLM provider: GitHub Models via `GITHUB_TOKEN` (`models: read`), swappable to Anthropic via documented `ANTHROPIC_API_KEY` secret.
- Cost guard: max 3 healing attempts/day; beyond that Slack notification only.
- New `docs/auto-healing-setup.md`: secrets/permissions setup guidance (deliverable).
- Remove `scripts/gemini_diagnose.py` (replaced); optional new repo skill `.agent/skills/locator-healing-specialist/`.

### Out of Scope
- Auto-merge of healing PRs.
- Healing non-locator failures (real bugs, infra).
- Multi-failure batch healing in one PR.

## Capabilities

### New Capabilities
- `auto-healing-pipeline`: detection, classification, LLM-based locator healing, verification-gated PR delivery, and Slack notification of CI locator failures.

### Modified Capabilities
- None (no existing specs in the target repo yet; Pipeline 1 changes are captured within the new capability).

## Approach

Python script + GitHub Models REST API (Approach 1 from exploration). `workflow_run` on Pipeline 1 (all triggers: push, PR, cron) → download artifacts → parse `*-result.json` + DOM dumps/screenshots (never gh-pages SPA) → exception-type pre-classifier → LLM proposes new locator from `By.toString()` + DOM context → validate JSON schema + edit locator file → re-run failed scenarios at failing SHA → on green: branch + PR + Slack; on red/bug/over-quota: Slack only.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| Whole repo | New | Bootstrap copy of framework into target repo |
| `.github/workflows/tests.yml` | Modified | Artifact upload on failure |
| `.github/workflows/auto-heal.yml` | New | Healing workflow |
| `scripts/heal_locator.py` | New | Healing engine |
| `scripts/gemini_diagnose.py` | Removed | Replaced |
| `TestRunner.java` / `junit-platform.properties` | Modified | Rerun plugin |
| `docs/auto-healing-setup.md` | New | Secrets setup guide |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Cross-run artifact download needs REST/`dawidd6` action | High | Pin known-good action; fallback to REST API |
| `cucumber.features` may not override `@ConfigurationParameter` | Med | `-Dcucumber.filter.name` fallback; verify in design |
| Valid-but-wrong LLM locator | Med | Mandatory re-run gate before PR |
| Flaky test false "healed" | Med | Single-retry semantics; human merge gate |

## Rollback Plan

Disable `auto-heal.yml` (delete or `if: false`); Pipeline 1 artifact upload is additive and harmless. Re-add `gemini_diagnose.py` from git history if diagnosis-only mode is wanted.

## Dependencies

- GitHub Models availability on the repo (`models: read` permission).
- Existing `SLACK_WEBHOOK_URL` secret.

## Success Criteria

- [ ] Locator failure on any Pipeline 1 trigger produces a verified healing PR + Slack message within the daily quota
- [ ] Non-locator failures produce Slack-only notification, zero LLM fix attempts
- [ ] No PR is created unless failed scenarios pass re-run
- [ ] Setup doc lets a new user configure secrets in <15 min
