#!/usr/bin/env bash
# Pre-commit guard preventing accidental commit of words/identifiers
# specific to the operator's deployment (internal hostnames, vendor scope
# codes, project codenames, sprint codes, device names, etc.).
#
# The dictionary is **operator-local** and intentionally NOT stored in this
# repository. Each operator configures their own wordlist via git config or
# an external file. If no dictionary is configured, this hook is a silent
# no-op — open-source contributors do not need to set anything.
#
# Operator setup (one of):
#
#   git config --local hooks.privateIdentifiersTier1 '<extended-regex>'
#   git config --local hooks.privateIdentifiersTier2 '<extended-regex>'
#
# or via an external file (one assignment per line, `tier1=<regex>` /
# `tier2=<regex>`):
#
#   git config --local hooks.privateIdentifiersFile ~/.config/tm-guard/words.txt
#
# Tier 1 is intended for unambiguous compound names that can be grepped
# literally (low false-positive risk). Tier 2 is for short bare names that
# need word boundaries — supply your own \b...\b wrapping.
#
# Wire as a pre-commit hook:
#   git config core.hooksPath .githooks
#
# See CONTRIBUTING.md.

set -euo pipefail

TIER1=$(git config --local hooks.privateIdentifiersTier1 2>/dev/null || true)
TIER2=$(git config --local hooks.privateIdentifiersTier2 2>/dev/null || true)

# Optional: external file. Format: lines `tier1=<regex>` and `tier2=<regex>`.
DICT_FILE=$(git config --local hooks.privateIdentifiersFile 2>/dev/null || true)
if [ -n "$DICT_FILE" ] && [ -f "$DICT_FILE" ]; then
  T1_FROM_FILE=$(grep -E '^tier1=' "$DICT_FILE" | head -1 | cut -d= -f2-)
  T2_FROM_FILE=$(grep -E '^tier2=' "$DICT_FILE" | head -1 | cut -d= -f2-)
  [ -n "$T1_FROM_FILE" ] && TIER1="$T1_FROM_FILE"
  [ -n "$T2_FROM_FILE" ] && TIER2="$T2_FROM_FILE"
fi

# No dictionary configured → silent no-op (open-source-contributor friendly).
if [ -z "$TIER1" ] && [ -z "$TIER2" ]; then
  exit 0
fi

# Pick targets. When run as a git hook, GIT_INDEX_FILE is set or there are
# staged changes; otherwise scan the full tracked tree (manual / CI use).
if git diff --cached --name-only --diff-filter=ACMR | grep -q .; then
  TARGETS=$(git diff --cached --name-only --diff-filter=ACMR \
    | grep -v 'check-no-private-identifiers' || true)
  CONTEXT="staged"
else
  TARGETS=$(git ls-files \
    | grep -v 'check-no-private-identifiers' || true)
  CONTEXT="full tree"
fi

[ -z "$TARGETS" ] && exit 0

FAIL=0
HITS_FILE=$(mktemp)
trap 'rm -f "$HITS_FILE"' EXIT

while IFS= read -r f; do
  [ -z "$f" ] && continue
  [ -f "$f" ] || continue
  # Skip binary files (avoid corrupting grep output and false positives).
  if file --mime "$f" 2>/dev/null | grep -q "charset=binary"; then
    continue
  fi
  if [ -n "$TIER1" ]; then
    if grep -EnH -- "$TIER1" "$f" 2>/dev/null >>"$HITS_FILE"; then
      FAIL=1
    fi
  fi
  if [ -n "$TIER2" ]; then
    if grep -EnH -- "$TIER2" "$f" 2>/dev/null >>"$HITS_FILE"; then
      FAIL=1
    fi
  fi
done <<< "$TARGETS"

if [ $FAIL -ne 0 ]; then
  echo "" >&2
  echo "ERROR: private business identifiers found in $CONTEXT files." >&2
  echo "Replace with generic placeholders before committing. See CONTRIBUTING.md." >&2
  echo "" >&2
  cat "$HITS_FILE" >&2
  exit 1
fi

exit 0
