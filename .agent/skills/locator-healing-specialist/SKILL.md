---
name: locator-healing-specialist
description: "Prompt context for LLM-based Selenium locator healing. Trigger: auto-healing pipeline LLM calls, locator repair, stale locator triage."
license: MIT
metadata:
  author: gentleman-programming
  version: "1.0"
---

# Locator Healing Specialist

Optional prompt context for the auto-healing pipeline
(`openspec/changes/auto-healing-pipeline`). The healing engine
(`scripts/heal_locator.py`) builds its own prompt at runtime; this skill
captures the domain rules so an agent (or a human reviewing a healing PR)
applies the same criteria.

## Locator JSON contract

Each file under `src/test/resources/locators/` maps a key to exactly one
locator:

```json
"key": { "type": "id|name|xpath|css|classname|linktext", "value": "..." }
```

- `type` MUST be one of the six enum values above (Selenium `By.toString()`
  mapping: `cssSelector` → `css`, `className` → `classname`,
  `linkText` → `linktext`).
- `value` MUST be non-empty, at most 500 characters, and different from the
  broken value.

## Proposal rules

1. Propose ONE replacement that uniquely matches the same logical element in
   the provided DOM dump — never a different element that happens to match.
2. Prefer robustness in this order: stable `id` → stable `name` →
   data-attribute CSS → structural XPath. Avoid text-content XPath when the
   copy is likely to change, and avoid positional indexes (`[1]`, `:nth-child`)
   unless nothing else exists.
3. Answer with ONLY a JSON object: `{"key": "...", "type": "...", "value": "..."}`.
   No prose, no Markdown fences.
4. Never propose a locator whose type escapes the enum, and never reuse the
   broken value — both are rejected by the validation gate before any edit.

## Hard boundaries (never cross)

- Only `FrameworkException` failures with an embedded `By.toString()` are
  locator-eligible. `VerificationException` or any other exception is a real
  bug: no proposal, no edit — Slack notification only.
- One failure healed per run; extra eligible failures stay pending.
- A healing PR is created ONLY after the failed scenarios re-run green at the
  failing SHA (`-Dcucumber.filter.name`, serial, no `clean`).
- PRs are never auto-merged; a human reviews the single-file JSON diff.
