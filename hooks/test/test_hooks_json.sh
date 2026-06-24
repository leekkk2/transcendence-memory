#!/usr/bin/env bash
# Regression test for plugin hook compatibility.
#
# Codex currently warns and skips async lifecycle hooks from hooks/hooks.json,
# so the published plugin must not ship any `"async": true` entries.
#
# Run:
#   bash hooks/test/test_hooks_json.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
HOOKS_JSON="${REPO_DIR}/hooks/hooks.json"

echo "hooks.json compatibility tests"
echo "------------------------------"

jq -e '.hooks.Stop[0].hooks[0].command | strings | length > 0' "$HOOKS_JSON" >/dev/null
echo "  ok   stop hook command present"

if jq -e '
  [
    .. | objects | select(has("async")) | .async
  ] | any(. == true)
' "$HOOKS_JSON" >/dev/null; then
    echo '  FAIL async:true found in hooks/hooks.json'
    exit 1
fi

echo "  ok   no async:true entries"
echo "------------------------------"
echo "pass=2 fail=0"
