#!/usr/bin/env bash
# tm-remember.sh — hardened, config-driven quick-memory wrapper for the
# transcendence-memory self-hosted RAG backend (POST /ingest-memory/objects).
#
# Why this script exists (vs hand-typing curl per SKILL.md fallback):
#   1. The single biggest source of ingest failures in practice is hand-written
#      JSON: unescaped quotes / newlines / CJK punctuation inside `text` produce
#      malformed bodies or 422s. We build EVERY body with `jq -n --arg` so the
#      payload is correct-by-construction — no manual escaping, ever.
#   2. zsh-safe: inline `{...}` braces trigger zsh glob expansion; jq + stdin
#      piping means nothing JSON-shaped ever reaches the caller's shell.
#   3. Secrets must never land in long-term memory. The plugin's lifecycle hooks
#      redact automatically, but a bare-skill install has no hooks — so this
#      script carries its own self-contained redaction pass (same pattern set as
#      hooks/common.sh redact_secrets, duplicated on purpose: scripts/ must not
#      depend on hooks/ which is absent in a bare install).
#   4. Same proxy-first + direct-fallback transport model as tm-search.sh
#      (Cloudflare-fronted endpoints: on some hosts the env proxy is the only
#      reliable path, on others it's broken while direct works).
#
# Write-path discipline: NO curl --retry. A timed-out write may have already
# reached the server; blind retries can double-store. The only automatic
# re-send is the direct fallback after a CONNECTION-class failure (curl 6/7 —
# nothing was ever sent), which is safe. The client-supplied `id` makes an
# accidental replay near-idempotent anyway, but we don't lean on that.
#
# Pure config-driven: NO hardcoded endpoint / api_key / container / private host.

set -euo pipefail

# ---------------------------------------------------------------------------
# Constants (reasons inline — no voodoo numbers)
# ---------------------------------------------------------------------------

# Non-default UA: Cloudflare WAF in front of the self-hosted domain 403s some
# default tool UAs (curl/*). A stable named UA is allowlisted.
readonly USER_AGENT="transcendence-memory-skill/0.7"

# Config location. Overridable via env only for testing; defaults to the path
# every other skill command reads.
readonly CONFIG_FILE="${TM_CONFIG_FILE:-$HOME/.transcendence-memory/config.toml}"

# Per-request budgets:
#   connect 5s  : behind a dead proxy a connect can otherwise hang for minutes.
#   max-time 60s: ingest writes the object + enqueues an embed job; normally
#                 sub-second, 60s absorbs a cold server without stalling forever.
readonly CONNECT_TIMEOUT=5
readonly INGEST_MAX_TIME=60

# Direct-fallback connect-timeout — deliberately wider than the proxied 5s:
# a direct TCP/TLS handshake to a Cloudflare edge from a GFW-region host can
# legitimately take 9-12s before succeeding. (Same rationale as tm-search.sh.)
readonly DIRECT_FALLBACK_CONNECT_TIMEOUT="${TM_DIRECT_CONNECT_TIMEOUT:-15}"

# Exit codes — same vocabulary as tm-search.sh so callers can branch uniformly:
readonly EX_OK=0
readonly EX_USAGE=64        # bad CLI args
readonly EX_CONFIG=78       # config missing/unparseable
readonly EX_AUTH=77         # 401/403
readonly EX_TRANSIENT=75    # 5xx/timeout
readonly EX_UNAVAILABLE=69  # endpoint unreachable / generic failure

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

err() { printf '%s\n' "tm-remember: $*" >&2; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    err "required command not found: $1"
    exit "$EX_CONFIG"
  }
}

# Parse one value from config.toml — identical mechanics to tm-search.sh so the
# two scripts can never disagree about what the config means.
toml_get() {
  local key="$1"
  grep -E "^[[:space:]]*${key}[[:space:]]*=" "$CONFIG_FILE" 2>/dev/null \
    | head -1 \
    | sed -E 's/^[^=]*=[[:space:]]*//; s/^"//; s/"[[:space:]]*$//; s/[[:space:]]*$//'
}

load_config() {
  [[ -f "$CONFIG_FILE" ]] || {
    err "config not found: $CONFIG_FILE"
    err "run '/tm connect <token>' or '/tm connect --manual' to create it."
    exit "$EX_CONFIG"
  }

  ENDPOINT="$(toml_get endpoint)"
  API_KEY="$(toml_get api_key)"
  CONTAINER_CFG="$(toml_get container)"

  if [[ -z "$ENDPOINT" ]]; then
    err "missing 'endpoint' in $CONFIG_FILE — re-run /tm connect."
    exit "$EX_CONFIG"
  fi
  if [[ -z "$API_KEY" ]]; then
    err "missing 'api_key' in $CONFIG_FILE — re-run /tm connect."
    exit "$EX_CONFIG"
  fi

  # Strip a trailing slash so "$ENDPOINT/ingest-memory/objects" never doubles up.
  ENDPOINT="${ENDPOINT%/}"

  # Derive host for --noproxy from the endpoint URL (pure bash, no subprocess —
  # never leaks the key).
  local no_scheme="${ENDPOINT#*://}"
  no_scheme="${no_scheme%%/*}"
  ENDPOINT_HOST="${no_scheme%%:*}"

  # Proxy routing: same two-path model as tm-search.sh (see its load_config for
  # the full rationale). TM_NO_PROXY=1 forces direct-only.
  FORCE_DIRECT=0
  [[ "${TM_NO_PROXY:-0}" == "1" ]] && FORCE_DIRECT=1
  if [[ -n "${ENDPOINT_HOST:-}" ]]; then
    DIRECT_ARGS=(--noproxy "$ENDPOINT_HOST")
  else
    DIRECT_ARGS=(--noproxy "*")
  fi
}

# Self-contained secret redaction (mirror of hooks/common.sh redact_secrets —
# duplicated because a bare skill install ships scripts/ without hooks/).
# Covers: OpenAI/Anthropic sk-*, Stripe pk_live_/sk_live_, Slack xoxb-/xoxp-,
# GitHub ghp_/gho_, AWS AKIA, Bearer token, URL-embedded password,
# PRIVATE KEY block, JWT-like triple-segment token.
# Trade-off: pure sed, no semantic detection — prefer a miss over mangling text.
redact_secrets() {
  sed -E \
    -e 's/sk-[A-Za-z0-9_-]{20,}/sk-***REDACTED***/g' \
    -e 's/pk_live_[A-Za-z0-9]{20,}/pk_live_***REDACTED***/g' \
    -e 's/sk_live_[A-Za-z0-9]{20,}/sk_live_***REDACTED***/g' \
    -e 's/xoxb-[A-Za-z0-9-]{20,}/xoxb-***REDACTED***/g' \
    -e 's/xoxp-[A-Za-z0-9-]{20,}/xoxp-***REDACTED***/g' \
    -e 's/ghp_[A-Za-z0-9]{30,}/ghp_***REDACTED***/g' \
    -e 's/gho_[A-Za-z0-9]{30,}/gho_***REDACTED***/g' \
    -e 's/AKIA[A-Z0-9]{16}/AKIA***REDACTED***/g' \
    -e 's/([Aa]uthorization:[[:space:]]*[Bb]earer[[:space:]]+)[A-Za-z0-9._-]+/\1***REDACTED***/g' \
    -e 's#(https?://[^/[:space:]]*:)[^@[:space:]]+(@)#\1***REDACTED***\2#g' \
    -e 's#([a-z][a-z0-9+.-]*://[^/[:space:]]*:)[^@[:space:]]+(@)#\1***REDACTED***\2#g' \
    -e 's/-----BEGIN [A-Z ]*PRIVATE KEY-----[^-]*-----END [A-Z ]*PRIVATE KEY-----/***PRIVATE_KEY_REDACTED***/g' \
    -e 's/[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}/***JWT_REDACTED***/g'
}

# POST helper — same shape as tm-search.sh's http_post_json minus --retry (see
# write-path discipline in the header). Direct fallback fires ONLY on curl 6/7
# (connection never established → replay is safe); a 28 timeout is NOT replayed
# because the request may have reached the server.
http_post_json() {
  local url="$1" max_time="$2"
  local payload out rc
  payload="$(cat)"

  _post_once() {  # $1 = connect-timeout override (empty = default); $@ rest = noproxy args
    local ct="$1"; shift
    local extra=()
    [[ -n "$ct" ]] && extra+=(--connect-timeout "$ct")
    set +e
    # bash-3.2-safe empty-array expansion under set -u.
    out="$(
      printf '%s' "$payload" | curl -sS -X POST "$url" \
        --connect-timeout "$CONNECT_TIMEOUT" \
        --max-time "$max_time" \
        --fail-with-body \
        ${extra[@]+"${extra[@]}"} \
        "$@" \
        -A "$USER_AGENT" \
        -H "X-API-KEY: $API_KEY" \
        -H "Content-Type: application/json" \
        -w $'\n%{http_code}' \
        --data @-
    )"
    rc=$?
    set -e
  }

  if [[ "${FORCE_DIRECT:-0}" == "1" ]]; then
    _post_once "$DIRECT_FALLBACK_CONNECT_TIMEOUT" "${DIRECT_ARGS[@]}"
  else
    _post_once ""
    local http_probe="${out##*$'\n'}"
    if [[ ( "$rc" -eq 6 || "$rc" -eq 7 ) && ( -z "$http_probe" || "$http_probe" == "000" ) ]]; then
      err "note: proxied request failed (curl exit $rc); retrying direct (--noproxy)."
      _post_once "$DIRECT_FALLBACK_CONNECT_TIMEOUT" "${DIRECT_ARGS[@]}"
    fi
  fi

  LAST_HTTP="${out##*$'\n'}"
  LAST_BODY="${out%$'\n'*}"
  if [[ "$LAST_BODY" == "$LAST_HTTP" ]]; then LAST_BODY=""; fi
  LAST_CURL_RC="$rc"
}

# Map curl exit / HTTP status to an exit code with a next-step hint.
classify_and_exit() {
  local curl_rc="$1" http="$2" body="$3"

  if [[ "$curl_rc" -ne 0 && ( -z "$http" || "$http" == "000" ) ]]; then
    case "$curl_rc" in
      6|7)  err "endpoint unreachable (DNS/connect failed) on BOTH proxied and direct paths. Check the server is up and that either your *_PROXY or a direct route can reach it."
            exit "$EX_UNAVAILABLE" ;;
      28)   err "request timed out — the memory MAY or MAY NOT have been stored. Verify with: tm-search.sh search \"<a phrase from the text>\" before re-sending (blind re-send can double-store)."
            exit "$EX_TRANSIENT" ;;
      *)    err "curl failed (exit $curl_rc) with no HTTP status. Likely network/TLS."
            exit "$EX_UNAVAILABLE" ;;
    esac
  fi

  case "$http" in
    401|403)
      err "auth/permission denied (HTTP $http). Check api_key in $CONFIG_FILE (re-run /tm connect to refresh)."
      [[ -n "$body" ]] && printf '%s\n' "$body" >&2
      exit "$EX_AUTH" ;;
    422)
      # The dominant historical failure class for this endpoint. Surface the
      # server's validation detail AND the usual root causes in plain words.
      err "validation rejected (HTTP 422). Common causes: unsupported metadata value type (only plain strings/numbers/bools — drop nested objects/arrays), empty 'text', or a malformed field. Server detail below; schema probe: GET \$ENDPOINT/ingest-memory/contract"
      [[ -n "$body" ]] && printf '%s\n' "$body" >&2
      exit "$EX_USAGE" ;;
    5*)
      err "server error (HTTP $http) — transient. Retry shortly; if persistent, check health with: tm-search.sh status"
      [[ -n "$body" ]] && printf '%s\n' "$body" >&2
      exit "$EX_TRANSIENT" ;;
    4*)
      err "request rejected (HTTP $http). Likely a bad parameter — see server error below."
      [[ -n "$body" ]] && printf '%s\n' "$body" >&2
      exit "$EX_USAGE" ;;
    *)
      err "unexpected HTTP status '$http' (curl exit $curl_rc)."
      [[ -n "$body" ]] && printf '%s\n' "$body" >&2
      exit "$EX_UNAVAILABLE" ;;
  esac
}

usage() {
  cat >&2 <<EOF
tm-remember.sh — quick memory store (POST /ingest-memory/objects) with jq-built
JSON (no hand-escaping 422s), built-in secret redaction, and proxy auto-fallback.

Usage:
  $0 "memory text" [options]

Options:
  --title <t>        Optional title (also redacted).
  --tags a,b,c       Comma-separated tags.
  --container <c>    Override the config.toml container.
  --id <mem-x>       Client memory id (default: mem-<epoch>-<rand>).
  --no-embed         Skip auto_embed (you must POST /embed later yourself).
  --json             Emit the raw server JSON instead of the one-line summary.

Env overrides:
  TM_CONFIG_FILE     config path (default ~/.transcendence-memory/config.toml)
  TM_NO_PROXY=1      force direct-only (--noproxy); default = proxy-first +
                     auto direct fallback on connection failure
  TM_DIRECT_CONNECT_TIMEOUT   direct-fallback connect-timeout s (default $DIRECT_FALLBACK_CONNECT_TIMEOUT)

Exit codes: 0 ok | 64 usage/422 | 77 auth | 75 transient | 78 config | 69 unavailable
EOF
}

# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

main() {
  require_cmd curl
  require_cmd jq

  local text="" title="" tags_csv="" container_override="" mem_id="" auto_embed=true json_out=0

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --title)     [[ $# -ge 2 ]] || { err "--title needs a value"; exit "$EX_USAGE"; }
                   title="$2"; shift 2 ;;
      --tags)      [[ $# -ge 2 ]] || { err "--tags needs a value"; exit "$EX_USAGE"; }
                   tags_csv="$2"; shift 2 ;;
      --container) [[ $# -ge 2 ]] || { err "--container needs a value"; exit "$EX_USAGE"; }
                   container_override="$2"; shift 2 ;;
      --id)        [[ $# -ge 2 ]] || { err "--id needs a value"; exit "$EX_USAGE"; }
                   mem_id="$2"; shift 2 ;;
      --no-embed)  auto_embed=false; shift ;;
      --json)      json_out=1; shift ;;
      -h|--help)   usage; exit "$EX_OK" ;;
      --)          shift
                   while [[ $# -gt 0 ]]; do
                     [[ -n "$text" ]] && text="$text $1" || text="$1"
                     shift
                   done ;;
      -*)          err "unknown option: $1"; usage; exit "$EX_USAGE" ;;
      *)           # Bare args concatenate into the memory text, so unquoted
                   # multi-word invocations still do the right thing.
                   [[ -n "$text" ]] && text="$text $1" || text="$1"
                   shift ;;
    esac
  done

  if [[ -z "$text" ]]; then
    err "no memory text given."
    usage
    exit "$EX_USAGE"
  fi

  load_config

  local container="${container_override:-$CONTAINER_CFG}"
  if [[ -z "$container" ]]; then
    err "warning: no 'container' in config; falling back to server default 'home'."
    container="home"
  fi

derive_semantic_id() {
  local t="$1" tags="$2" txt="$3"
  python3 - <<'PY' "$t" "$tags" "$txt"
import sys, re, datetime, random

title, tags, text = sys.argv[1:4]
slug_parts = []

def clean_tokens(s):
    # Extract alphanumeric words, skip common English stop words
    stop = {'the', 'and', 'for', 'with', 'from', 'this', 'that', 'what', 'when', 'how', 'about', 'into', 'over', 'after'}
    return [w.lower() for w in re.findall(r'[a-zA-Z0-9]+', s) if len(w) >= 2 and w.lower() not in stop]

if title:
    tokens = clean_tokens(title)
    if tokens:
        slug_parts.extend(tokens[:4])

if len(slug_parts) < 2 and tags:
    for tag in tags.split(','):
        t_tokens = clean_tokens(tag)
        if t_tokens:
            slug_parts.extend(t_tokens[:2])
        if len(slug_parts) >= 3:
            break

if not slug_parts and text:
    tokens = clean_tokens(text)
    if tokens:
        slug_parts.extend(tokens[:3])

date_str = datetime.date.today().strftime('%Y%m%d')
rand_suffix = f"{random.randint(100, 999)}"

if slug_parts:
    base_slug = "-".join(slug_parts)[:40].strip('-')
    print(f"{base_slug}-{date_str}-{rand_suffix}")
else:
    print(f"mem-{date_str}-{random.randint(1000, 9999)}")
PY
}

  # Generate semantic slug id if not explicitly provided (replaces opaque timestamp id)
  if [[ -z "$mem_id" ]]; then
    mem_id="$(derive_semantic_id "$title" "$tags_csv" "$text")"
  fi

  # Redact BEFORE the payload exists anywhere — secrets never reach the wire.
  text="$(printf '%s' "$text" | redact_secrets)"
  [[ -n "$title" ]] && title="$(printf '%s' "$title" | redact_secrets)"

  # jq -n correct-by-construction body; optional fields only when provided
  # (the server treats absent and empty differently for title).
  local body
  body="$(jq -n \
    --arg c "$container" \
    --arg id "$mem_id" \
    --arg text "$text" \
    --arg title "$title" \
    --arg tags "$tags_csv" \
    --argjson embed "$auto_embed" \
    '{
      container: $c,
      objects: [
        ({id: $id, text: $text}
         + (if $title != "" then {title: $title} else {} end)
         + (if $tags  != "" then {tags: ($tags | split(",") | map(gsub("^\\s+|\\s+$"; "")) | map(select(. != "")))} else {} end))
      ],
      auto_embed: $embed
    }')"

  http_post_json "$ENDPOINT/ingest-memory/objects" "$INGEST_MAX_TIME" <<<"$body"

  if [[ "$LAST_CURL_RC" -ne 0 || ! "$LAST_HTTP" =~ ^2 ]]; then
    classify_and_exit "$LAST_CURL_RC" "$LAST_HTTP" "$LAST_BODY"
  fi

  if [[ "$json_out" -eq 1 ]]; then
    printf '%s\n' "$LAST_BODY"
  else
    local embed_state="skipped"
    [[ "$auto_embed" == "true" ]] && embed_state="queued"
    printf 'stored id=%s container=%s embed=%s\n' "$mem_id" "$container" "$embed_state"
  fi
}

main "$@"
