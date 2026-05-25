#!/usr/bin/env bash
# Forbid private business identifiers from entering the open-source repo.
#
# Triggers on: vendor scope codes, internal product names, deploy hostnames,
# specific device names, internal sprint codes. False-positive risk is low
# because we use \b word boundaries for short bare names.
#
# Exit 0 = clean, exit 1 = leak found (print offending lines).
#
# Wire as a git pre-commit hook (recommended) or a CI step:
#   git config core.hooksPath .githooks
#   ln -sf ../../scripts/check-no-private-identifiers.sh .githooks/pre-commit
set -euo pipefail

# Determine scope: staged files only when run as a git hook; otherwise full tree.
if [ -n "${GIT_INDEX_FILE:-}" ] || git rev-parse --git-dir >/dev/null 2>&1 && \
   git diff --cached --name-only --diff-filter=ACMR | grep -qE '\.(py|md|yml|yaml|sh|toml|cfg|json)$'; then
  TARGETS=$(git diff --cached --name-only --diff-filter=ACMR -- \
    '*.py' '*.md' '*.yml' '*.yaml' '*.sh' '*.toml' '*.cfg' '*.json' 2>/dev/null \
    | grep -v 'check-no-private-identifiers' || true)
  CONTEXT="staged"
else
  # exclude this very script (its forbidden-pattern strings would self-trigger)
  TARGETS=$(find scripts tests docs -type f \
    \( -name '*.py' -o -name '*.md' -o -name '*.yml' -o -name '*.yaml' \
       -o -name '*.sh' -o -name '*.toml' -o -name '*.cfg' -o -name '*.json' \) \
    2>/dev/null | grep -v __pycache__ | grep -v 'check-no-private-identifiers' || true)
  CONTEXT="full tree"
fi

if [ -z "$TARGETS" ]; then
  exit 0
fi

# Two-tier check to balance precision:
# - tier 1: unambiguous compound names (literal grep, no false positives)
# - tier 2: short bare names that need word boundaries (extended regex)
TIER1='{{REDACTED-PRIVATE-WORDLIST-T1}}'
TIER2='{{REDACTED-PRIVATE-WORDLIST-T2}}'

HITS_FILE=$(mktemp)
trap 'rm -f "$HITS_FILE"' EXIT

echo "$TARGETS" | tr '\n' '\0' | xargs -0 -I{} grep -InE "$TIER1" {} 2>/dev/null >> "$HITS_FILE" || true
echo "$TARGETS" | tr '\n' '\0' | xargs -0 -I{} grep -InE "$TIER2" {} 2>/dev/null >> "$HITS_FILE" || true

if [ -s "$HITS_FILE" ]; then
  echo "ERROR: private business identifiers found in $CONTEXT files." >&2
  echo "Replace with generic placeholders before committing. See CONTRIBUTING.md." >&2
  echo "" >&2
  cat "$HITS_FILE" >&2
  exit 1
fi

exit 0
