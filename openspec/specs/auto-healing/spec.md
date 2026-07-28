# Auto-Healing Pipeline Specification

## Purpose

Automated detection, classification, and healing of locator failures in Pipeline 1 (`tests.yml`). Broken locators produce a verified, human-reviewed healing PR; real bugs produce a Slack-only notification. Replaces `scripts/gemini_diagnose.py`.

## Requirements

### Requirement: Failure Context Capture

Pipeline 1 MUST upload `build/allure-results` and `build/debug-artifacts` as workflow artifacts whenever the test step fails, on every trigger (push, PR, cron). The gh-pages rendered report MUST NOT be used as a healing input.

#### Scenario: Failed run publishes artifacts

- GIVEN a Pipeline 1 run with at least one failed scenario
- WHEN the run completes
- THEN `allure-results` and `debug-artifacts` artifacts exist for that run
- AND the workflow run conclusion is failure

#### Scenario: Green run

- GIVEN a Pipeline 1 run with zero failures
- WHEN the run completes
- THEN no healing workflow is triggered with healing work

### Requirement: Healing Workflow Trigger

The healing workflow MUST trigger via `workflow_run` on any failed Pipeline 1 run (push, PR, cron), MUST download artifacts from the triggering run (cross-run download), and MUST check out the failing commit SHA — not the default-branch HEAD.

#### Scenario: Cross-run context recovery

- GIVEN a failed Pipeline 1 run at commit SHA `abc123`
- WHEN the healing workflow starts
- THEN it downloads that run's artifacts
- AND the working tree is checked out at `abc123`

### Requirement: Deterministic Failure Classification

The system MUST classify each failed scenario from `*-result.json` stack traces before any LLM call: `FrameworkException` (locator) SHALL be eligible for healing; `VerificationException` or any other exception SHALL be classified as a real bug and MUST NOT trigger an LLM call or locator edit.

#### Scenario: Locator failure is eligible

- GIVEN a failure whose trace contains `FrameworkException`
- WHEN classification runs
- THEN the scenario is marked locator-eligible and the `By.toString()` type+value is extracted

#### Scenario: Real bug is never healed

- GIVEN a failure whose trace contains `VerificationException`
- WHEN classification runs
- THEN no LLM call is made, no locator file is edited, and only a Slack notification is sent

### Requirement: LLM-Based Locator Healing

For locator-eligible failures, the system MUST invoke the LLM (GitHub Models via `GITHUB_TOKEN`, swappable to Anthropic via documented secret) with the broken locator type+value, DOM dump, and failure message; the LLM output MUST pass JSON schema validation before the locator file under `src/test/resources/locators/` is edited.

#### Scenario: Proposal applied after validation

- GIVEN an LLM response proposing a new locator value
- WHEN the response passes schema validation
- THEN the matching locator JSON entry is updated and the old value is retained for the PR body

#### Scenario: Invalid proposal rejected

- GIVEN an LLM response failing schema validation
- WHEN validation runs
- THEN no file is edited and the failure is handled as unhealed (Slack only)

### Requirement: Verification Gate

A healing PR MUST be created only if re-running exactly the failed scenarios (Cucumber rerun file, `-Dcucumber.filter.name` fallback) at the failing SHA passes. On re-run failure, the system MUST NOT create a PR and MUST send a Slack notification instead.

#### Scenario: Green re-run opens PR

- GIVEN a healed locator at the failing SHA
- WHEN the failed scenarios re-run green
- THEN a branch + PR is opened containing only the locator JSON change

#### Scenario: Red re-run blocks PR

- GIVEN a healed locator at the failing SHA
- WHEN the re-run fails
- THEN no PR is created and Slack is notified

### Requirement: Healing Delivery

Healing PRs MUST require human review (no auto-merge) and MUST trigger a Slack notification containing the locator key, old → new value, and PR link. Only one failure SHALL be healed per PR.

#### Scenario: PR and Slack delivered

- GIVEN a verified healing PR
- WHEN it is opened
- THEN Slack shows locator key, old → new value, and PR link

### Requirement: Slack Notification for Non-Locator Failures

Failures classified as real bugs, unhealed locator failures, and over-quota runs MUST produce a Slack-only notification; no PR, no locator edit, and no LLM fix attempt SHALL occur for real bugs.

#### Scenario: Bug notification content

- GIVEN a `VerificationException` failure
- WHEN notification is sent
- THEN Slack includes scenario name and exception summary, with no fix proposal

### Requirement: Cost Guard

The system MUST allow at most 3 healing attempts per day; beyond the quota, failures MUST produce Slack-only notifications. The Gemini diagnosis script MUST be removed as part of this change.

#### Scenario: Quota exceeded

- GIVEN 3 healing attempts already consumed today
- WHEN another locator failure occurs
- THEN no healing attempt runs and Slack notes the quota was reached
