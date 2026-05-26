#!/usr/bin/env bash
# Unit tests for redact_secrets() in hooks/common.sh.
#
# Test inputs use the `example-` placeholder prefix so the repo's secret-scan
# pre-commit hook does not flag them as real credentials. Real secrets must
# never live in this file.
#
# Run:
#   bash hooks/test/test_redact.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# shellcheck source=../common.sh
source "${REPO_DIR}/hooks/common.sh"

PASS=0
FAIL=0

assert_contains() {
    local label="$1"
    local actual="$2"
    local needle="$3"
    if printf '%s' "$actual" | grep -qF -- "$needle"; then
        printf '  ok   %s\n' "$label"
        PASS=$((PASS + 1))
    else
        printf '  FAIL %s\n    expected to contain: %s\n    got:                %s\n' \
            "$label" "$needle" "$actual"
        FAIL=$((FAIL + 1))
    fi
}

assert_not_contains() {
    local label="$1"
    local actual="$2"
    local needle="$3"
    if printf '%s' "$actual" | grep -qF -- "$needle"; then
        printf '  FAIL %s\n    must NOT contain: %s\n    got:              %s\n' \
            "$label" "$needle" "$actual"
        FAIL=$((FAIL + 1))
    else
        printf '  ok   %s\n' "$label"
        PASS=$((PASS + 1))
    fi
}

echo "redact_secrets() unit tests"
echo "---------------------------"

# 1. OpenAI / Anthropic style sk-* key
INPUT='My key is sk-example-abc123def456ghi789jkl0mnop'
OUT=$(printf '%s' "$INPUT" | redact_secrets)
assert_contains       'sk-* key replaced'        "$OUT" 'sk-***REDACTED***'
assert_not_contains   'sk-* original gone'       "$OUT" 'example-abc123def456ghi789jkl0mnop'

# 2. Authorization: Bearer header
INPUT='Authorization: Bearer example-eyJabcDEFghiJKLmnoPQRstuVWXyz123456'
OUT=$(printf '%s' "$INPUT" | redact_secrets)
assert_contains       'bearer token replaced'    "$OUT" 'Authorization: Bearer ***REDACTED***'
assert_not_contains   'bearer original gone'     "$OUT" 'example-eyJabcDEF'

# 3. URL-embedded user:password
INPUT='postgres://user:example-secret-pw@host:5432/db'
OUT=$(printf '%s' "$INPUT" | redact_secrets)
assert_contains       'URL password replaced'    "$OUT" 'postgres://user:***REDACTED***@host'
assert_not_contains   'URL password gone'        "$OUT" 'example-secret-pw'

# 4. JWT-like triple-segment token
INPUT='JWT example-eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example-payloadAAAAAAAAAAAA.example-signatureBBBBBBBBBB'
OUT=$(printf '%s' "$INPUT" | redact_secrets)
assert_contains       'JWT replaced'             "$OUT" '***JWT_REDACTED***'
assert_not_contains   'JWT original gone'        "$OUT" 'example-eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'

echo "---------------------------"
printf 'pass=%d fail=%d\n' "$PASS" "$FAIL"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
