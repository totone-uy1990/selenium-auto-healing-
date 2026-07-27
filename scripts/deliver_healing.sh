#!/usr/bin/env bash
# Deliver a verified locator healing as a single-file commit on a new branch
# plus a human-reviewed pull request (SDD change: auto-healing-pipeline).
#
# Threat-matrix responses (design.md):
#   Commit state : stages ONE explicit path and verifies the staged diff
#                  contains exactly that file before committing.
#   Push state   : pushes an explicit refspec (the healing branch only).
#   PR commands  : gh pr create with explicit --head/--base, args passed as
#                  separate argv tokens (no shell composition).
#
# Usage:
#   deliver_healing.sh --branch <auto-heal/key-sha8> --base <default-branch> \
#       --edit-file <locator json path> --title <pr title> --body-file <path>
set -euo pipefail

BRANCH=""
BASE=""
EDIT_FILE=""
TITLE=""
BODY_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch)    BRANCH="$2";    shift 2 ;;
    --base)      BASE="$2";      shift 2 ;;
    --edit-file) EDIT_FILE="$2"; shift 2 ;;
    --title)     TITLE="$2";     shift 2 ;;
    --body-file) BODY_FILE="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

for required in BRANCH BASE EDIT_FILE TITLE BODY_FILE; do
  if [[ -z "${!required}" ]]; then
    echo "missing required argument: --$(echo "$required" | tr 'A-Z_' 'a-z-')" >&2
    exit 2
  fi
done

case "$EDIT_FILE" in
  src/test/resources/locators/*.json) ;;
  *) echo "edit file must be a locator JSON under src/test/resources/locators/: $EDIT_FILE" >&2; exit 2 ;;
esac

if [[ ! -f "$EDIT_FILE" ]]; then
  echo "edit file not found: $EDIT_FILE" >&2
  exit 1
fi

# Commit state: stage exactly one explicit path, never `git add -A` / `git add .`
git add -- "$EDIT_FILE"

staged="$(git diff --cached --name-only)"
if [[ "$staged" != "$EDIT_FILE" ]]; then
  echo "staged diff must contain exactly '$EDIT_FILE', got:" >&2
  echo "$staged" >&2
  git restore --staged .
  exit 1
fi

git switch -c "$BRANCH"
git commit -m "$TITLE"

# Push state: explicit refspec — the healing branch and nothing else.
git push -u origin "$BRANCH"

# PR commands: explicit head/base as separate argv tokens.
gh pr create --head "$BRANCH" --base "$BASE" --title "$TITLE" --body-file "$BODY_FILE"
