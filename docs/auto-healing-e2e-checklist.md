# Auto-Healing Pipeline — E2E Manual Checklist

This is a **manual** validation checklist (design.md *Testing Strategy → E2E*
row). Do not run it on `main`: use a throwaway branch and close the artifacts
when done. Estimated time: 20–30 minutes.

Prerequisites: [setup guide](auto-healing-setup.md) completed
(`SLACK_WEBHOOK_URL` secret configured, workflows registered on the default
branch).

## Case 1 — Broken locator produces a healing PR

1. Create a branch: `git switch -c e2e/healing-check`.
2. Break one locator, e.g. in `src/test/resources/locators/login.json` change
   the `userNameField` value to `//input[@id='does-not-exist-e2e']`.
3. Push the branch and open a PR to `main` so Pipeline 1 runs on it
   (or push to `main` directly on a fork/sandbox).
4. Wait for Pipeline 1 to fail, then for **Actions → Auto-heal locators** to
   complete.
5. Expected results — verify ALL of them:
   - [ ] A branch `auto-heal/userNameField-<sha8>` exists.
   - [ ] A PR is open whose diff contains **exactly one file**: the locator
     JSON that was broken. No other file is modified.
   - [ ] The PR body lists the locator key, old → new value, and the
     triggering run URL.
   - [ ] The PR targets the repository default branch and requires human
     review (no auto-merge happened).
   - [ ] Slack received a message with the locator key, old → new value, and
     the PR link.
   - [ ] The job log shows the verification re-run used
     `-Dcucumber.filter.name` and **not** `-Dcucumber.features`.
   - [ ] The job log shows the re-run executed **only** the failed scenarios
     (not the full suite).
6. Cleanup: close the healing PR and the e2e PR, delete both branches.

## Case 2 — Broken assertion produces Slack-only notification

1. Create a branch: `git switch -c e2e/bug-check`.
2. Break an assertion expectation (e.g. in a step definition or page object,
   change an expected success message to a string that never appears) **or**
   temporarily modify `CustomAssertions` usage so a `VerificationException`
   is thrown. Do **not** touch any locator file.
3. Push and let Pipeline 1 fail; wait for **Auto-heal locators**.
4. Expected results — verify ALL of them:
   - [ ] No `auto-heal/*` branch was created.
   - [ ] No PR was opened.
   - [ ] No file under `src/test/resources/locators/` was modified (the run
     log shows no edit).
   - [ ] Slack received a "real bug detected" message including the scenario
     name and exception summary, with no fix proposal.
5. Cleanup: close the e2e PR and delete the branch.

## Case 3 — Quota exhaustion (optional, same UTC day)

1. Trigger 4 locator failures the same UTC day (repeat Case 1 with different
   locator keys/branches).
2. Expected results:
   - [ ] The first 3 produce healing PRs.
   - [ ] The 4th produces a Slack "daily quota reached" message, no PR.
   - [ ] The next UTC day, the counter is reset (a new locator failure heals
     again).

## Sign-off

| Case | Date | Tester | Result |
|------|------|--------|--------|
| 1 — Locator PR | | | ☐ pass ☐ fail |
| 2 — Bug Slack-only | | | ☐ pass ☐ fail |
| 3 — Quota (optional) | | | ☐ pass ☐ fail |
