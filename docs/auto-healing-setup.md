# Auto-Healing Pipeline — Setup Guide

Goal: a failed Pipeline 1 run caused by a stale locator produces a verified,
human-reviewed healing PR plus a Slack notification — with no manual triage.
This guide gets a new repository configured in **under 15 minutes**.

## What the pipeline does

1. `tests.yml` (Pipeline 1) fails → uploads `allure-results` and
   `debug-artifacts` as workflow artifacts.
2. `auto-heal.yml` fires (`workflow_run: [completed]`, only when the run
   concluded `failure` **and** the run belongs to this repository — forks are
   never healed because the job checks out untrusted code with write tokens).
3. The healing engine (`scripts/heal_locator.py`) classifies each failure:
   `FrameworkException` with a Selenium `By.toString()` → locator-eligible;
   anything else (`VerificationException`, NPE, …) → real bug → Slack only.
4. For the first eligible failure, the LLM proposes a replacement locator,
   the engine validates it against the schema contract, and edits exactly one
   JSON file under `src/test/resources/locators/`.
5. **Verification gate**: the workflow re-runs exactly the failed scenarios at
   the failing SHA via `-Dcucumber.filter.name` (serial execution, no
   `clean`). Green → branch `auto-heal/<key>-<sha8>` + PR (no auto-merge) +
   Slack. Red → the edit is reverted and Slack is notified.
6. Cost guard: at most **3 healing attempts per UTC day**; beyond that,
   Slack-only notifications.

## 1. Required secrets

| Secret | Required | Purpose |
|--------|----------|---------|
| `SLACK_WEBHOOK_URL` | **Yes** | Incoming-webhook URL receiving all notifications (bugs, pending failures, unhealed locators, quota reached, PR links). |
| `ANTHROPIC_API_KEY` | No | When set, the engine uses Anthropic (`claude-haiku-4-5`) instead of GitHub Models. |

Create them under **Settings → Secrets and variables → Actions → New
repository secret**.

### Slack webhook (≈5 min)

1. In Slack: **Apps → Incoming Webhooks → Add to Slack** (or create an app at
   api.slack.com → *Incoming Webhooks* → *Add New Webhook to Workspace*).
2. Pick the notification channel and copy the `https://hooks.slack.com/...`
   URL.
3. Save it as the `SLACK_WEBHOOK_URL` repository secret.

No Slack app reinstall is needed later; rotating the webhook only means
updating the secret.

### LLM provider: default needs **no secret**

The default provider is **GitHub Models** (`openai/gpt-4o-mini`), called with
the workflow's built-in `GITHUB_TOKEN` — nothing to configure beyond the
`models: read` permission already declared in `auto-heal.yml`.

To swap to Anthropic instead, add the `ANTHROPIC_API_KEY` secret; the engine
detects it and switches provider automatically (no workflow change).

> **Rate-limit assumption (GitHub Models free tier):** free-tier GitHub
> Models quotas are limited per day and per model. The pipeline makes **one
> LLM call per healing attempt, max 3 per day**, which is expected to fit
> comfortably within free-tier limits. If throttling ever occurs, the engine
> fails open: the failure is reported to Slack as *unhealed* (no PR, no
> locator edit) and the next Pipeline 1 failure retries. No live verification
> of the quota was possible during implementation — treat the first weeks as
> a observation period; if Slack shows recurring LLM throttling, set
> `ANTHROPIC_API_KEY` to switch providers.

## 2. Workflow permissions

`auto-heal.yml` declares the minimal permission set — nothing to grant
manually:

| Permission | Why |
|------------|-----|
| `contents: write` | Push the `auto-heal/<key>-<sha8>` branch. |
| `pull-requests: write` | `gh pr create` with explicit `--head`/`--base`. |
| `actions: read` | Cross-run artifact download (`run-id`). |
| `models: read` | GitHub Models inference via `GITHUB_TOKEN`. |

Repository settings check (one-time):

- **Settings → Actions → General → Workflow permissions** must allow the
  default `GITHUB_TOKEN` *read and write* (or be permissive enough for the
  table above).
- No environments, CODEOWNERS exceptions, or branch-protection bypasses are
  required; healing PRs go through normal human review.

## 3. Runtime requirements (already satisfied in CI)

- **Python 3** on `ubuntu-latest` — the healing engine is **stdlib-only**
  (`json`, `urllib`, `re`, …); no `pip install` step exists in the workflow.
- **pytest** is only needed to run the engine's test-suite
  (`scripts/tests/`). It is *not* installed in `auto-heal.yml` because the
  workflow executes the engine, not its tests. If you ever add a "run engine
  tests" step to a workflow, install it first
  (`pip install pytest pyyaml`) — locally we use the untracked `.venv-heal`
  virtualenv.
- **JDK 21** via `actions/setup-java@v4` (Temurin), same as Pipeline 1.

## 4. Quick path (< 15 min)

1. (5 min) Create the Slack incoming webhook → save `SLACK_WEBHOOK_URL`.
2. (1 min) Confirm *Workflow permissions* allow `GITHUB_TOKEN` write.
3. (2 min) Push a trivial commit to `main` so both workflows are registered.
4. (5 min) Sanity check: open **Actions → Auto-heal locators** — it appears
   and stays idle until Pipeline 1 fails (it fires on every completed run and
   no-ops on green via the job-level `if`).
5. Optional: run the [E2E manual checklist](auto-healing-e2e-checklist.md) to
   validate end-to-end on a throwaway branch.

## 5. Operating notes

- **Quota store**: Actions cache under the UTC-day prefix
  `heal-quota-<date>-`. Cache entries are immutable per key, so each verified
  heal saves a run-unique key (`heal-quota-<date>-<run_id>-<attempt>`) and
  restores by day prefix; a new UTC day is a cache miss and the counter
  resets. Cache eviction fails open (toward healing) — acceptable for a cost
  guard.
- **One heal per run**: the first eligible failure (lexical order) is healed;
  extra eligible failures are reported to Slack as *pending* and are picked
  up by subsequent runs.
- **No auto-merge**: healing PRs always require human review.
- **Rollback**: disable `auto-heal.yml` (delete the file or add `if: false`).
  Pipeline 1's artifact upload is additive and harmless.

## 6. Troubleshooting

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| Workflow never runs | Pipeline 1 succeeded (job `if` skips green runs) or workflow not on default branch | Check **Actions → Auto-heal locators** after a failed run |
| "unhealed: no LLM credential" | `GITHUB_TOKEN` lacked `models: read` and no Anthropic key | Verify permissions block; optionally set `ANTHROPIC_API_KEY` |
| Slack shows LLM throttling | GitHub Models free-tier quota | Set `ANTHROPIC_API_KEY` to switch providers |
| Healing PR created but CI red on it | Flaky re-run passed | Close the PR; the next failure will re-heal |
| No artifacts downloaded | Pipeline 1 failed before the test step uploaded them | Check the triggering run's artifact list |
