# Design: Auto-Healing Pipeline

## Technical Approach

Python healing engine (`scripts/heal_locator.py`) orchestrated by `auto-heal.yml` (`workflow_run` on Pipeline 1). Exception classification gates one LLM call (GitHub Models default); the validated locator edit is verified by re-running only failed scenarios at the failing SHA. Green → branch + PR + Slack; else Slack only.

## Architecture Decisions

| Decision | Choice | Rejected | Rationale |
|---|---|---|---|
| Green runs | Job-level `if: github.event.workflow_run.conclusion == 'failure'` | Fire-and-noop | `workflow_run: [completed]` fires on green too; `if:` costs zero minutes |
| Cross-run download | `actions/download-artifact@v4` with `run-id` + `github-token` (`actions: read`) | `dawidd6/action-download-artifact`; REST/`gh api` | v4.1+ does cross-run natively — no third-party supply-chain risk; REST needs manual unzip. Fallback documented, not implemented |
| Quota store | Actions cache, key `heal-quota-<UTC date>`, integer file; no restore-keys → new day = miss = reset | Repo file (pollutes history); artifacts (immutable) | Mutable, date-scoped, no extra permissions. Eviction fails open toward healing; fine for a cost guard |
| Batching | 1 quota unit + max 1 healed failure per run (first eligible, lexical order); extras Slack-reported "pending". 5 failures/day → 3 PRs, 2 Slack-only. `concurrency: group: auto-heal, cancel-in-progress: false` serializes the counter | Multi-heal per run; parallel runs (counter race) | Deterministic; matches spec quota scenario |
| Rerun | `rerun:build/rerun.txt` in `TestRunner.java` `PLUGIN_PROPERTY_NAME` (annotation beats `junit-platform.properties`). Verify: `./gradlew test -Dcucumber.features="@build/rerun.txt" -Dcucumber.execution.parallel.enabled=false` (NO `clean` — deletes rerun.txt). Fallback: `-Dcucumber.filter.name="<scenario>"` | Full-suite re-run (slow); manual filter parsing | Cucumber supports `@path` rerun files; serial = deterministic. Precedence risk covered by RED test + fallback |
| LLM provider | GitHub Models (`models.github.ai/inference`, `openai/gpt-4o-mini`) via `GITHUB_TOKEN` (`models: read`); Anthropic swap if `ANTHROPIC_API_KEY` set, isolated in `get_llm_client()` | Gemini (weak edits); agentic CLI (unbounded) | Zero-secret free default; swap in setup doc |
| Fork safety | Heal only when `workflow_run.head_repository.full_name == github.repository`; forks → Slack-only | Heal forks; skip PR triggers | Job checks out the SHA and runs its code with write tokens — untrusted fork code = privilege escalation |

## Data Flow

    Pipeline 1 fails → upload allure-results + debug-artifacts
    auto-heal.yml (if: conclusion==failure)
      ├─ download-artifact(run-id) → checkout head_sha
      ├─ quota restore (UTC-day cache) → over? → Slack, stop
      ├─ classify *-result.json traces
      │    ├─ FrameworkException → extract By.toString() type+value
      │    └─ VerificationException/other → Slack (bug), stop
      ├─ LLM(locator + DOM dump + message) → schema validate
      │    └─ invalid → Slack (unhealed), stop
      ├─ edit locators/<file>.json (old value retained for PR body)
      ├─ ./gradlew test -Dcucumber.features="@build/rerun.txt"
      │    ├─ green → branch auto-heal/<key>-<sha8> → gh pr create → Slack(key, old→new, PR) → quota++
      │    └─ red → git restore → Slack, stop
      └─ remaining eligible failures → Slack "pending"

## File Changes

| File | Action | Description |
|------|--------|-------------|
| *(whole repo)* | Create | Bootstrap copy of framework from reference repo |
| `.github/workflows/tests.yml` | Modify | `upload-artifact` ×2 `if: failure`; remove Gemini steps |
| `.github/workflows/auto-heal.yml` | Create | Healing workflow |
| `scripts/heal_locator.py` | Create | Parse/classify/LLM/validate/edit/notify engine |
| `scripts/gemini_diagnose.py` | Delete | Replaced |
| `src/test/java/runner/TestRunner.java` | Modify | Add rerun plugin to annotation |
| `docs/auto-healing-setup.md` | Create | Secrets/permissions guide (<15 min) |
| `.agent/skills/locator-healing-specialist/SKILL.md` | Create | Optional LLM prompt context |

## Interfaces / Contracts

Locator JSON unchanged: `"key": {"type": "id|name|xpath|css|classname|linktext", "value": "..."}`.
LLM output contract (validated before any edit):

```json
{"key": "<locator key>", "type": "xpath|css|id|name|classname|linktext", "value": "<new locator>"}
```

Validation: `key` exists in exactly one locator file whose type+value matches the trace's `By.toString()`; `type` in enum; `value` non-empty, ≤500 chars, ≠ old. PR body: file, key, old → new, scenario, run URL. Slack payloads per spec.

`auto-heal.yml` permissions: `contents: write` (branch push), `pull-requests: write` (`gh pr create --head/--base` explicit), `actions: read`, `models: read`. `SLACK_WEBHOOK_URL` secret only; never exposed to the gradle re-run step's env.

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | Classifier (Framework/Verification/other), schema accept/reject, quota counter | pytest + fixture result JSONs |
| Integration | LLM→validated edit on fixture DOM; `-Dcucumber.features` precedence RED test (fallback asserts `filter.name` path) | pytest + local Gradle smoke run |
| E2E | Break a locator on a branch → PR with only JSON change; break an assertion → Slack-only | Manual validation on new repo |

## Threat Matrix

| Boundary | Applicability | Design response | RED tests |
|---|---|---|---|
| Documentation-like paths | N/A — no executable-file classification | — | — |
| Git repository selection | Applicable — checkout `head_sha`, branch create | Explicit `ref: head_sha`; branch in repo root only | Checkout lands on failing SHA, not default HEAD |
| Commit state | Applicable — PR = ONLY locator JSON | `git add` single explicit path; `git restore` on red | Staged diff contains exactly one file |
| Push state | Applicable — first push of new branch | Explicit refspec `git push -u origin auto-heal/...` | Push targets healing branch only |
| PR commands | Applicable — `gh pr create` | Explicit `--head`/`--base`, args as list (no shell composition) | PR head == healing branch, base == default |

Fork-code execution handled by Fork Safety Gate (no CI-testable RED; manual review item).

## Migration / Rollout

None. Healing is additive except `gemini_diagnose.py` removal. Rollback: disable `auto-heal.yml`.

## Spec Requirement Mapping

| Spec Requirement | Design Decision |
|---|---|
| Failure Context Capture | `upload-artifact` on failure, both dirs; gh-pages never read |
| Healing Workflow Trigger | `workflow_run` + `if: conclusion==failure` + run-id download + head_sha checkout |
| Deterministic Classification | Exception-class pre-classifier before any LLM call |
| LLM-Based Healing | GitHub Models default, Anthropic swap, schema gate |
| Verification Gate | rerun.txt re-run at failing SHA; red → no PR |
| Healing Delivery | Branch + PR, no auto-merge, Slack key/old→new/link, 1 failure/PR |
| Slack for Non-Locator | Bugs/unhealed/over-quota → Slack-only |
| Cost Guard | UTC-day cache counter, max 3, serialized; Gemini script deleted |

## Open Questions

- [ ] GitHub Models free-tier rate limits vs 3 heals/day — verify model availability at apply time; Slack fallback covers throttling.
- [ ] `-Dcucumber.features` precedence over `@ConfigurationParameter` — RED test at apply; fallback specified.
