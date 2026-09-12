#!/usr/bin/env bash
# tm-search.sh — hardened, config-driven retrieval wrapper for the
# transcendence-memory self-hosted RAG backend.
#
# Why this script exists (vs hand-typing curl per SKILL.md fallback):
#   1. zsh-safe: callers often run under zsh where inline JSON `{...}` / `[...]`
#      triggers `zsh: no matches found` (glob expansion). We force bash + build
#      every JSON body with `jq -n` (never bare braces) so the body can never be
#      glob-expanded by ANY caller shell.
#   2. proxy-aware (two-path, self-healing): self-hosted endpoints are usually
#      fronted by Cloudflare. On a GFW-region host, DIRECT connections to the
#      Cloudflare edge are flaky (12s connect-timeout, both edge IPs fail) while
#      the machine's localhost proxy reaches the edge reliably (~1-1.4s). So we
#      RESPECT the ambient *_PROXY env by default (do NOT blindly --noproxy), and
#      on a connection-class failure we automatically retry once with --noproxy '*'
#      (covers the inverse: proxy set-but-broken, direct reachable). See the
#      proxy-routing section in load_config + http_post_json for the full rationale.
#   3. cold-start-safe: a cold server returns HTTP 200 with a *degraded body*
#      (per_container_status timeout/not_initialized). curl --retry can't see
#      that — only inspecting the body can. We re-send on degraded bodies.
#
# Read-only by design: only status / search / query / containers / jobs. No
# write endpoints, so we never use --retry-all-errors (which would unsafely
# retry non-idempotent writes). Writes live in tm-remember.sh.
#
# Pure config-driven: NO hardcoded endpoint / api_key / container / private host.

# set -e: stop on first error. set -u: undefined var is an error (catches typos
# in a security-relevant tool). set -o pipefail: a failing stage in a pipe fails
# the whole pipe (so `curl | jq` can't mask a curl failure).
# Running under `#!/usr/bin/env bash` detaches us from the caller's zsh entirely.
set -euo pipefail

# ---------------------------------------------------------------------------
# Constants (reasons inline — no voodoo numbers)
# ---------------------------------------------------------------------------

# Non-default UA: Cloudflare WAF in front of the self-hosted domain 403s some
# default tool UAs (curl/*). A stable named UA is allowlisted. Bump the version
# suffix if the WAF policy ever needs to distinguish skill versions.
readonly USER_AGENT="transcendence-memory-skill/0.5"

# Source dynamic project/node route hook before evaluating CONFIG_FILE
ROUTE_HOOK="${TM_ROUTE_SCRIPT:-$HOME/.transcendence-memory/project-route.sh}"
if [[ -f "$ROUTE_HOOK" ]]; then
  # shellcheck source=/dev/null
  source "$ROUTE_HOOK" 2>/dev/null || true
fi

# Config location. Overridable via env only for testing; defaults to the path
# every other skill command reads.
readonly CONFIG_FILE="${TM_CONFIG_FILE:-$HOME/.transcendence-memory/config.toml}"


# Idempotent-read curl resilience flags. Rationale per flag:
#   --connect-timeout 5 : TCP/TLS connect must complete in 5s; behind a dead
#                         proxy a connect can otherwise hang for minutes.
#   --retry 3           : retry transient transport failures (DNS, reset) up to 3x.
#   --retry-delay 2     : fixed 2s between retries — long enough to ride out a
#                         brief upstream blip, short enough not to stall the turn.
#   --retry-connrefused : also retry on ECONNREFUSED (server mid-restart).
#   --fail-with-body    : non-2xx -> exit non-zero BUT keep the server error JSON
#                         on stdout so we can classify transient/config/auth.
# NOTE: deliberately NO --retry-all-errors — that would retry on HTTP errors too,
# which is unsafe for writes; this script is read-only but we keep the discipline.
readonly CURL_RESILIENCE=(--connect-timeout 5 --retry 0 --fail-with-body)

# Per-operation --max-time ceilings (overall wall-clock budget per request):
#   health : tiny JSON, must be a fast liveness probe.
#   search : LanceDB direct query; cold subprocess spawn can take 5-10s, plus
#            our own re-send loop has its own outer budget, so 120s is generous.
#   query  : LightRAG hybrid + LLM answer synthesis — can legitimately take
#            over a minute, so 180s per the spec.
readonly HEALTH_CONNECT_TIMEOUT=3   # status probe must fail fast if down
readonly HEALTH_MAX_TIME=5
readonly SEARCH_MAX_TIME=120
readonly QUERY_MAX_TIME=180
readonly ADMIN_MAX_TIME=30          # /containers + /jobs/{id}: tiny metadata reads

# Cold-start lazy-absorption tuning (search only). A cold server answers 200 with
# a degraded body; we re-send the SAME query until per_container goes all-ok.
#   COLD_RETRY_MAX=4   : at most 4 application-level cold-start attempts
#                        (~16s+ request time) comfortably covers the warm-up.
#   COLD_RETRY_DELAY_S=2: short gap — re-send quickly once the prior attempt returns.
# Both overridable via env for tuning without editing the script.
readonly COLD_RETRY_MAX="${TM_COLD_RETRY_MAX:-4}"
readonly COLD_RETRY_DELAY_S="${TM_COLD_RETRY_DELAY_S:-2}"

# Direct-fallback connect-timeout (the second, --noproxy '*' attempt). DELIBERATELY
# wider than CURL_RESILIENCE's 5s: when we fall back to direct, we are most often
# on a GFW-region host hitting a Cloudflare edge, where the TCP/TLS handshake can
# legitimately take 9-12s before it either succeeds or the edge IP is reset. A 5s
# budget would pre-empt a slow-but-valid direct connect; 15s gives it a fair shot
# without stalling the turn indefinitely. Overridable for tuning.
readonly DIRECT_FALLBACK_CONNECT_TIMEOUT="${TM_DIRECT_CONNECT_TIMEOUT:-15}"

# Default topk: larger than the server default (5) because retrieval consumers
# generally want broad recall and we return full bodies untruncated. Overridable.
readonly DEFAULT_TOPK="${TM_TOPK:-10}"

# Default /query top_k candidate pool (server default is 60; keep parity).
readonly DEFAULT_QUERY_TOPK="${TM_QUERY_TOPK:-60}"

# Exit codes — let callers/agents branch on cause:
readonly EX_OK=0
readonly EX_USAGE=64        # bad CLI args
readonly EX_CONFIG=78       # config missing/unparseable (EX_CONFIG from sysexits.h)
readonly EX_AUTH=77         # 401/403 — auth/permission (EX_NOPERM from sysexits.h)
readonly EX_TRANSIENT=75    # 5xx/timeout/cold-never-ready (EX_TEMPFAIL from sysexits.h)
readonly EX_UNAVAILABLE=69  # endpoint unreachable / generic failure

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

err() { printf '%s\n' "tm-search: $*" >&2; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    err "required command not found: $1"
    exit "$EX_CONFIG"
  }
}

# Parse one value from config.toml. TOML here is flat-ish (`key = "value"`); we
# tolerate the [connection]/[auth] sections by grepping the key anywhere. We take
# the FIRST match and strip the surrounding quotes. Done in a way that never
# prints the value (callers capture it into a variable).
toml_get() {
  # $1 = key name (endpoint|api_key|container|mode)
  local key="$1"
  grep -E "^[[:space:]]*${key}[[:space:]]*=" "$CONFIG_FILE" 2>/dev/null \
    | head -1 \
    | sed -E 's/^[^=]*=[[:space:]]*//; s/^"//; s/"[[:space:]]*$//; s/[[:space:]]*$//'
}

parse_endpoints() {
  local raw=""
  if [[ -n "${TM_ENDPOINTS:-}" ]]; then
    raw="$TM_ENDPOINTS"
  elif [[ -n "${TM_ENDPOINT:-}" ]]; then
    raw="$TM_ENDPOINT"
  else
    local arr_line
    arr_line="$(grep -E "^[[:space:]]*endpoints[[:space:]]*=" "$CONFIG_FILE" 2>/dev/null | head -1 || true)"
    if [[ -n "$arr_line" ]]; then
      raw="$(printf '%s' "$arr_line" | sed -E 's/^[^=]*=[[:space:]]*//; s/^[[:space:]]*\[//; s/\][[:space:]]*$//' | tr -d '"'\''')"
    else
      raw="$(toml_get endpoint)"
    fi
  fi

  ENDPOINTS=()
  local IFS=', '
  for ep in $raw; do
    ep="$(printf '%s' "$ep" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    [[ -n "$ep" ]] && ENDPOINTS+=("${ep%/}")
  done

  if [[ ${#ENDPOINTS[@]} -eq 0 ]]; then
    err "missing 'endpoint' in $CONFIG_FILE — re-run /tm connect."
    exit "$EX_CONFIG"
  fi
  ENDPOINT="${ENDPOINTS[0]}"
}

configure_endpoint_routing() {
  local target_ep="$1"
  ENDPOINT="${target_ep%/}"
  local no_scheme="${ENDPOINT#*://}"
  no_scheme="${no_scheme%%/*}"
  ENDPOINT_HOST="${no_scheme%%:*}"

  TRANSPORT_MODE="${TM_TRANSPORT_MODE:-$(toml_get transport_mode || :)}"
  TRANSPORT_MODE="${TRANSPORT_MODE:-auto}"
  case "$TRANSPORT_MODE" in auto|direct|proxy) ;; *) err "invalid transport_mode"; exit "$EX_CONFIG" ;; esac
  FORCE_DIRECT=0
  [[ "$TRANSPORT_MODE" == "direct" ]] && FORCE_DIRECT=1
  [[ -z "${TM_TRANSPORT_MODE:-}" && "${TM_NO_PROXY:-0}" == "1" ]] && FORCE_DIRECT=1
  PROXY_ARGS=()
  if [[ "$TRANSPORT_MODE" == "proxy" && "$FORCE_DIRECT" == "0" ]]; then
    [[ -n "${https_proxy:-${HTTPS_PROXY:-${http_proxy:-${HTTP_PROXY:-${ALL_PROXY:-${all_proxy:-}}}}}}" ]] || { err "proxy mode requires a proxy environment variable"; exit "$EX_CONFIG"; }
    PROXY_ARGS=(--noproxy "")
  fi
  if [[ -n "${ENDPOINT_HOST:-}" ]]; then
    DIRECT_ARGS=(--noproxy "$ENDPOINT_HOST")
  else
    DIRECT_ARGS=(--noproxy "*")
  fi
}

load_config() {
  [[ -f "$CONFIG_FILE" ]] || {
    err "config not found: $CONFIG_FILE"
    err "run '/tm connect <token>' or '/tm connect --manual' to create it."
    exit "$EX_CONFIG"
  }

  parse_endpoints
  API_KEY="$(toml_get api_key)"
  CONTAINER="$(toml_get container)"

  if [[ -z "$API_KEY" ]]; then
    err "missing 'api_key' in $CONFIG_FILE — re-run /tm connect."
    exit "$EX_CONFIG"
  fi
  if [[ -z "$CONTAINER" ]]; then
    err "warning: no 'container' in config; falling back to server default 'home'."
    CONTAINER="home"
  fi

  configure_endpoint_routing "$ENDPOINT"
}


# Map a curl exit / HTTP status to one of our exit codes, and print a next-step
# hint. $1 = curl_rc, $2 = http_status (may be empty), $3 = response body.
classify_and_exit() {
  local curl_rc="$1" http="$2" body="$3"

  # curl transport failures (couldn't even get an HTTP status).
  if [[ "$curl_rc" -ne 0 && ( -z "$http" || "$http" == "000" ) ]]; then
    case "$curl_rc" in
      6|7)  err "endpoint unreachable (DNS/connect failed) on BOTH proxied and direct paths. Check the server is up and that either your *_PROXY or a direct route can reach it."
            exit "$EX_UNAVAILABLE" ;;
      28)   err "request timed out on BOTH proxied and direct paths. Server may be cold/overloaded, or neither route reaches the Cloudflare edge; retry shortly."
            exit "$EX_TRANSIENT" ;;
      *)    err "curl failed (exit $curl_rc) with no HTTP status. Likely network/TLS."
            exit "$EX_UNAVAILABLE" ;;
    esac
  fi

  # We have an HTTP status — branch on it.
  case "$http" in
    401|403)
      err "auth/permission denied (HTTP $http). Check api_key in $CONFIG_FILE (re-run /tm connect to refresh)."
      [[ -n "$body" ]] && printf '%s\n' "$body" >&2
      exit "$EX_AUTH" ;;
    5*)
      err "server error (HTTP $http) — transient. Retry shortly; if persistent, check server health with: $0 status"
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

# True when the last curl attempt failed with a connection-class error that
# warrants a direct-connect fallback: couldn't establish a connection (6/7) or
# timed out (28), AND we never got a real HTTP status (000/empty). A genuine HTTP
# error (4xx/5xx) means the request DID reach the server — no point re-routing.
is_connection_failure() {
  local rc="$1" http="$2"
  [[ "${TRANSPORT_MODE:-auto}" == "proxy" ]] && return 1
  [[ "$rc" -eq 6 || "$rc" -eq 7 || "$rc" -eq 28 || "$rc" -eq 35 ]] \
    && [[ -z "$http" || "$http" == "000" ]]
}

# Core POST helper: writes status code + body so the caller can inspect BOTH.
# Stdout: response body. We stash the HTTP status in the global LAST_HTTP and the
# curl exit code in LAST_CURL_RC. JSON body is piped in on stdin (--data @-) so
# nothing JSON-shaped ever reaches the shell as an argument (zsh-glob-safe).
#
# Proxy routing (see load_config): attempt #1 honors the ambient *_PROXY (the
# reliable path for a Cloudflare-fronted endpoint on a GFW-region host). On a
# connection-class failure we automatically retry ONCE direct (--noproxy '*',
# wider connect-timeout) — covers the inverse "proxy set but broken, direct OK".
# TM_NO_PROXY=1 skips straight to the direct attempt (FORCE_DIRECT=1).
# POST helper with auto-failover across service nodes.
http_post_json() {
  local target_path="$1" max_time="$2"
  local payload
  payload="$(cat)"

  if [[ "$target_path" =~ ^https?:// ]]; then
    local no_proto="${target_path#*://}"
    target_path="/${no_proto#*/}"
  fi

  _post_to_endpoint() {
    local target_url="$1"
    local out rc
    _post_once() {  # $1 = extra connect-timeout (empty = use CURL_RESILIENCE's 5s); $@ rest = noproxy args
      local ct="$1"; shift
      local extra=()
      [[ -n "$ct" ]] && extra+=(--connect-timeout "$ct")
      set +e
      out="$(
        printf '%s' "$payload" | curl -sS -X POST "$target_url" \
          "${CURL_RESILIENCE[@]}" \
          --max-time "$max_time" \
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
      _post_once "" ${PROXY_ARGS[@]+"${PROXY_ARGS[@]}"}
      if [[ "$target_url" != */query ]] && is_connection_failure "$rc" "${out##*$'\n'}"; then
        err "note: proxied request failed (curl exit $rc); retrying direct (--noproxy)."
        _post_once "$DIRECT_FALLBACK_CONNECT_TIMEOUT" "${DIRECT_ARGS[@]}"
      fi
    fi

    LAST_HTTP="${out##*$'\n'}"
    LAST_BODY="${out%$'\n'*}"
    if [[ "$LAST_BODY" == "$LAST_HTTP" ]]; then LAST_BODY=""; fi
    LAST_CURL_RC="$rc"
  }

  local ep_count=${#ENDPOINTS[@]}
  local idx=0
  while [[ $idx -lt $ep_count ]]; do
    local current_ep="${ENDPOINTS[$idx]}"
    configure_endpoint_routing "$current_ep"
    local full_url="${ENDPOINT%/}${target_path}"

    _post_to_endpoint "$full_url"

    if [[ "$LAST_CURL_RC" -eq 0 && "$LAST_HTTP" =~ ^[234] ]]; then
      return 0
    fi

    if [[ $((idx + 1)) -lt $ep_count ]]; then
      err "note: service node '$current_ep' unreachable or error (curl exit $LAST_CURL_RC, HTTP ${LAST_HTTP:-none}); failing over to next node '${ENDPOINTS[$((idx + 1))]}'."
      idx=$((idx + 1))
      continue
    fi
    break
  done
}

# GET helper for /health with auto-failover across service nodes.
http_get() {
  local target_path="$1" connect_to="$2" max_time="$3"
  local explicit_endpoint=""

  if [[ "$target_path" =~ ^https?:// ]]; then
    explicit_endpoint="${target_path%/health}"
    explicit_endpoint="${explicit_endpoint%/}"
    local no_proto="${target_path#*://}"
    target_path="/${no_proto#*/}"
  fi

  _get_from_endpoint() {
    local target_url="$1"
    local out rc
    _get_once() {  # $1 = connect-timeout; $@ rest = noproxy args
      local ct="$1"; shift
      set +e
      out="$(
        curl -sS "$target_url" \
          --connect-timeout "$ct" \
          --max-time "$max_time" \
          --fail-with-body \
          "$@" \
          -A "$USER_AGENT" \
          -w $'\n%{http_code}'
      )"
      rc=$?
      set -e
    }

    if [[ "${FORCE_DIRECT:-0}" == "1" ]]; then
      _get_once "$DIRECT_FALLBACK_CONNECT_TIMEOUT" "${DIRECT_ARGS[@]}"
    else
      _get_once "$connect_to"
      if is_connection_failure "$rc" "${out##*$'\n'}"; then
        err "note: proxied /health failed (curl exit $rc); retrying direct (--noproxy)."
        _get_once "$DIRECT_FALLBACK_CONNECT_TIMEOUT" "${DIRECT_ARGS[@]}"
      fi
    fi

    LAST_HTTP="${out##*$'\n'}"
    LAST_BODY="${out%$'\n'*}"
    if [[ "$LAST_BODY" == "$LAST_HTTP" ]]; then LAST_BODY=""; fi
    LAST_CURL_RC="$rc"
  }

  if [[ -n "$explicit_endpoint" ]]; then
    configure_endpoint_routing "$explicit_endpoint"
    _get_from_endpoint "${explicit_endpoint}${target_path}"
    return 0
  fi

  local ep_count=${#ENDPOINTS[@]}
  local idx=0
  while [[ $idx -lt $ep_count ]]; do
    local current_ep="${ENDPOINTS[$idx]}"
    configure_endpoint_routing "$current_ep"
    local full_url="${ENDPOINT%/}${target_path}"

    _get_from_endpoint "$full_url"

    if [[ "$LAST_CURL_RC" -eq 0 && "$LAST_HTTP" =~ ^[234] ]]; then
      return 0
    fi

    if [[ $((idx + 1)) -lt $ep_count ]]; then
      err "note: service node '$current_ep' unreachable (curl exit $LAST_CURL_RC, HTTP ${LAST_HTTP:-none}); failing over to next node '${ENDPOINTS[$((idx + 1))]}'."
      idx=$((idx + 1))
      continue
    fi
    break
  done
}


# Authenticated GET helper with auto-failover across service nodes.
http_get_auth() {
  local target_path="$1" max_time="$2"

  if [[ "$target_path" =~ ^https?:// ]]; then
    local no_proto="${target_path#*://}"
    target_path="/${no_proto#*/}"
  fi

  _get_auth_from_endpoint() {
    local target_url="$1"
    local out rc
    _get_auth_once() {  # $1 = extra connect-timeout; $@ rest = noproxy args
      local ct="$1"; shift
      local extra=()
      [[ -n "$ct" ]] && extra+=(--connect-timeout "$ct")
      set +e
      out="$(
        curl -sS "$target_url" \
          "${CURL_RESILIENCE[@]}" \
          --max-time "$max_time" \
          ${extra[@]+"${extra[@]}"} \
          "$@" \
          -A "$USER_AGENT" \
          -H "X-API-KEY: $API_KEY" \
          -w $'\n%{http_code}'
      )"
      rc=$?
      set -e
    }

    if [[ "${FORCE_DIRECT:-0}" == "1" ]]; then
      _get_auth_once "$DIRECT_FALLBACK_CONNECT_TIMEOUT" "${DIRECT_ARGS[@]}"
    else
      _get_auth_once "" ${PROXY_ARGS[@]+"${PROXY_ARGS[@]}"}
      if is_connection_failure "$rc" "${out##*$'\n'}"; then
        err "note: proxied request failed (curl exit $rc); retrying direct (--noproxy)."
        _get_auth_once "$DIRECT_FALLBACK_CONNECT_TIMEOUT" "${DIRECT_ARGS[@]}"
      fi
    fi

    LAST_HTTP="${out##*$'\n'}"
    LAST_BODY="${out%$'\n'*}"
    if [[ "$LAST_BODY" == "$LAST_HTTP" ]]; then LAST_BODY=""; fi
    LAST_CURL_RC="$rc"
  }

  local ep_count=${#ENDPOINTS[@]}
  local idx=0
  while [[ $idx -lt $ep_count ]]; do
    local current_ep="${ENDPOINTS[$idx]}"
    configure_endpoint_routing "$current_ep"
    local full_url="${ENDPOINT%/}${target_path}"

    _get_auth_from_endpoint "$full_url"

    if [[ "$LAST_CURL_RC" -eq 0 && "$LAST_HTTP" =~ ^[234] ]]; then
      return 0
    fi

    if [[ $((idx + 1)) -lt $ep_count ]]; then
      err "note: service node '$current_ep' unreachable (curl exit $LAST_CURL_RC, HTTP ${LAST_HTTP:-none}); failing over to next node '${ENDPOINTS[$((idx + 1))]}'."
      idx=$((idx + 1))
      continue
    fi
    break
  done
}


# Detect a cold/degraded search body. Returns 0 (true) if we should re-send.
# A cold server answers HTTP 200 but the BODY signals not-ready:
#   - per_container_status has any value matching timeout|not_initialized
#   - top-level initialized == false
#   - degraded == true AND results is empty (degraded with partial results is
#     acceptable — we don't loop forever on a permanently-down sibling)
is_cold_body() {
  local body="$1"
  jq -e '
    (
      ([ .per_container_status // {} | to_entries[].value ]
        | any(. == "timeout" or . == "not_initialized"))
    )
    or (.initialized == false)
    or ((.degraded == true) and ((.results // []) | length) == 0)
  ' <<<"$body" >/dev/null 2>&1
}

# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

cmd_status() {
  load_config

  _probe_node() {
    local target_ep="$1"

    configure_endpoint_routing "$target_ep"
    http_get "$ENDPOINT/health" "$HEALTH_CONNECT_TIMEOUT" "$HEALTH_MAX_TIME"

    if [[ "$LAST_CURL_RC" -ne 0 || ! "$LAST_HTTP" =~ ^2 ]]; then
      printf 'node: %s -> HTTP %s (curl %d)\n' "$ENDPOINT" "${LAST_HTTP:-none}" "$LAST_CURL_RC"
      return 1
    fi

    local summary
    summary="$(jq -r '
      "health: \(.status // "?")"
      + " | flavor: \(.build_flavor // "?")"
      + " | accepting_ingest: \(.accepting_ingest // "?")"
      + " | runtime_ready: search=\(.runtime_ready.search // "?") query=\(.runtime_ready.query // "?") embed=\(.runtime_ready.embed // "?")"
      + (if ((.degraded_reasons // []) | length) > 0 then " | degraded_reasons: \(.degraded_reasons | join(","))" else "" end)
      + (if ((.warnings // []) | length) > 0 then " | warnings: \(.warnings | join(","))" else "" end)
    ' <<<"$LAST_BODY" 2>/dev/null || echo "unparseable response")"

    if [[ ${#ENDPOINTS[@]} -gt 1 ]]; then
      printf 'node [%s]: %s\n' "$ENDPOINT" "$summary"
    else
      printf '%s\n' "$summary"
    fi
  }

  local failed=0
  local last_rc=0 last_http="" last_body=""
  for ep in "${ENDPOINTS[@]}"; do
    _probe_node "$ep" || {
      failed=$((failed + 1))
      last_rc="${LAST_CURL_RC:-1}"
      last_http="${LAST_HTTP:-}"
      last_body="${LAST_BODY:-}"
    }
  done

  if [[ $failed -eq ${#ENDPOINTS[@]} ]]; then
    classify_and_exit "$last_rc" "$last_http" "$last_body"
  fi

}

cmd_node() {
  load_config
  local node_name="${TM_NODE_NAME:-$(hostname -s 2>/dev/null || hostname 2>/dev/null || echo "unknown")}"
  local os_name="$(uname -s 2>/dev/null || echo "unknown")"
  local arch_name="$(uname -m 2>/dev/null || echo "unknown")"
  local active_ep="$ENDPOINT"
  local total_eps=${#ENDPOINTS[@]}

  printf 'Node: %s (%s/%s)\n' "$node_name" "$os_name" "$arch_name"
  printf 'Container: %s\n' "$CONTAINER"
  printf 'Active Service Node: %s\n' "$active_ep"
  if [[ "$total_eps" -gt 1 ]]; then
    local eps_joined
    eps_joined="$(IFS=', '; echo "${ENDPOINTS[*]}")"
    printf 'All Service Nodes (%d): %s\n' "$total_eps" "$eps_joined"
    printf 'Service Mode: Multi-service-node (with auto-failover)\n'
  else
    printf 'Service Mode: Single-service-node\n'
  fi
  printf 'Config File: %s\n' "$CONFIG_FILE"
}

cmd_search() {
  local json_out=0 rerank=null max_distance=null container_override="" union_opt=null
  # Parse flags then take the rest as the query.
  local args=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --json) json_out=1; shift ;;
      --rerank) rerank=true; shift ;;
      --no-rerank) rerank=false; shift ;;
      --max-distance) [[ $# -ge 2 ]] || { err "--max-distance needs a number"; exit "$EX_USAGE"; }; max_distance="$2"; shift 2 ;;
      -c|--container) [[ $# -ge 2 ]] || { err "--container needs a container name"; exit "$EX_USAGE"; }; container_override="$2"; shift 2 ;;
      --union) union_opt=true; shift ;;
      --no-union) union_opt=false; shift ;;
      --)     shift; while [[ $# -gt 0 ]]; do args+=("$1"); shift; done ;;
      *)      args+=("$1"); shift ;;
    esac
  done
  if [[ ${#args[@]} -eq 0 ]]; then
    err "usage: $0 search [--json] [--container <name>] [--union] <query>"
    exit "$EX_USAGE"
  fi
  local query="${args[*]}"

  load_config

  local target_container="${container_override:-${TM_CONTAINER:-$CONTAINER}}"
  local use_union=false
  if [[ "$union_opt" == "true" || ( -z "$union_opt" && "${TM_UNION:-0}" == "1" ) ]]; then
    use_union=true
  fi

  # Build the request body with jq -n (NEVER bare braces — zsh-glob-safe).
  local body
  body="$(jq -n \
    --arg c "$target_container" \
    --arg q "$query" \
    --argjson k "$DEFAULT_TOPK" \
    --argjson u "$use_union" \
    --argjson rerank "$rerank" --argjson distance "$max_distance" \
    '{container: $c, query: $q, topk: $k, union: $u}
     + (if $rerank != null then {rerank: $rerank} else {} end)
     + (if $distance != null then {score_threshold: $distance} else {} end)')"


  # Lazy cold-start absorption: send, inspect body, re-send the SAME query on a
  # cold/degraded body. Steady state (first response already ok) = single call,
  # zero extra overhead, no /health probe.
  local attempt=1 cold_triggered=0
  while :; do
    http_post_json "$ENDPOINT/search" "$SEARCH_MAX_TIME" <<<"$body"

    # Transport/HTTP failure → classify & exit (cold-start is a 200, so this is
    # a genuine error, not a warm-up).
    if [[ "$LAST_CURL_RC" -ne 0 || ! "$LAST_HTTP" =~ ^2 ]]; then
      classify_and_exit "$LAST_CURL_RC" "$LAST_HTTP" "$LAST_BODY"
    fi

    if is_cold_body "$LAST_BODY"; then
      cold_triggered=1
      if [[ "$attempt" -ge "$COLD_RETRY_MAX" ]]; then
        err "server still cold/degraded after $COLD_RETRY_MAX attempts (per_container not all ok). Returning last (possibly partial) result; retry shortly."
        # Don't hard-fail: return what we have so the caller isn't empty-handed,
        # but signal transient so scripts can decide to retry the whole op.
        SEARCH_DEGRADED_EXIT="$EX_TRANSIENT"
        break
      fi
      attempt=$((attempt + 1))
      sleep "$COLD_RETRY_DELAY_S"
      continue
    fi
    break
  done

  if [[ "$json_out" -eq 1 ]]; then
    # Raw passthrough for machine consumers.
    printf '%s\n' "$LAST_BODY"
  else
    # Distilled, full-text (NOT truncated) output: hit count + per-hit
    # score/title/full body. taskId/container shown for provenance.
    # v0.19.0: also renders per-hit lineStart–lineEnd (when the chunk carries
    # source line numbers) + a blocked_low_score warning (score-gate, not empty DB).
    jq -r '
      "hits: \((.results // []) | length)"
      + " | union_applied: \(.union_applied // false)"
      + " | degraded: \(.is_degraded // .degraded // false)"
      + " | rerank_applied: \(.rerank_applied // false)"
      + (if (.per_container_status // {}) | length > 0
           then " | per_container_status: " + ((.per_container_status | to_entries | map("\(.key)=\(.value)") | join(",")))
           else "" end)
      + (if ((.blocked_low_score // 0) > 0)
           then " | ⚠ blocked_low_score: \(.blocked_low_score) (score-gate 拦截·非库空)"
           else "" end),
      "",
      ( (.results // [])
        | to_entries[]
        | "── #\(.key + 1)  vector_distance↓=\(.value.vector_distance // .value.vectorScore // .value.score // "?")  rerank_relevance↑=\(.value.rerank_score // .value.rerankScore // "not_available")"
          + (if (.value.container // "") != "" then "  [\(.value.container)]" else "" end)
          + (if (.value.lineStart // null) != null then "  L\(.value.lineStart)–\(.value.lineEnd // "?")" else "" end)
          + (if (.value.title // "") != "" then "  title: \(.value.title)" else "" end)
          + "\n" + ((.value.text // .value.content // "(no text field)"))
      )
    ' <<<"$LAST_BODY" 2>/dev/null || {
      err "search returned non-JSON or unexpected shape:"
      printf '%s\n' "$LAST_BODY" >&2
      exit "$EX_TRANSIENT"
    }
  fi

  # If we exhausted cold retries, exit transient AFTER printing partial results.
  if [[ -n "${SEARCH_DEGRADED_EXIT:-}" ]]; then
    exit "$SEARCH_DEGRADED_EXIT"
  fi
  # Note whether the lazy re-send loop fired (useful for self-check evidence).
  if [[ "$cold_triggered" -eq 1 ]]; then
    err "note: lazy cold-start re-send was triggered (took $attempt attempts)."
  fi
}

cmd_query() {
  local json_out=0
  local args=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --json) json_out=1; shift ;;
      --)     shift; while [[ $# -gt 0 ]]; do args+=("$1"); shift; done ;;
      *)      args+=("$1"); shift ;;
    esac
  done
  if [[ ${#args[@]} -eq 0 ]]; then
    err "usage: $0 query [--json] <question>"
    exit "$EX_USAGE"
  fi
  local question="${args[*]}"

  load_config

  # mode hybrid + top_k candidate pool. Body via jq -n (zsh-glob-safe).
  local body
  body="$(jq -n \
    --arg c "$CONTAINER" \
    --arg q "$question" \
    --argjson k "$DEFAULT_QUERY_TOPK" \
    '{container: $c, query: $q, mode: "hybrid", top_k: $k}')"

  http_post_json "$ENDPOINT/query" "$QUERY_MAX_TIME" <<<"$body"

  if [[ "$LAST_CURL_RC" -ne 0 || ! "$LAST_HTTP" =~ ^2 ]]; then
    classify_and_exit "$LAST_CURL_RC" "$LAST_HTTP" "$LAST_BODY"
  fi

  if [[ "$json_out" -eq 1 ]]; then
    printf '%s\n' "$LAST_BODY"
  else
    jq -r '
      "answer:",
      (.answer // "(no answer)"),
      "",
      "citations: \((.citations // .sources // []) | length)",
      ( (.citations // .sources // [])
        | to_entries[]
        | "── #\(.key + 1)  vector_distance↓=\(.value.vector_distance // .value.vectorScore // .value.score // "?")"
          + "  source=\(.value.sourcePath // .value.chunkId // .value.chunk_id // "unknown")"
          + (if (.value.text // .value.content) != null then "\n" + (.value.text // .value.content) else "" end)
      )
    ' <<<"$LAST_BODY" 2>/dev/null || {
      err "query returned non-JSON or unexpected shape:"
      printf '%s\n' "$LAST_BODY" >&2
      exit "$EX_TRANSIENT"
    }
  fi
}

cmd_containers() {
  local json_out=0 pattern=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --json) json_out=1; shift ;;
      *)      pattern="$1"; shift ;;
    esac
  done

  load_config

  local url="$ENDPOINT/containers"
  # @uri-encode the pattern so spaces/CJK/globs survive the query string.
  [[ -n "$pattern" ]] && url="$url?pattern=$(jq -rn --arg p "$pattern" '$p|@uri')"

  http_get_auth "$url" "$ADMIN_MAX_TIME"

  if [[ "$LAST_CURL_RC" -ne 0 || ! "$LAST_HTTP" =~ ^2 ]]; then
    classify_and_exit "$LAST_CURL_RC" "$LAST_HTTP" "$LAST_BODY"
  fi

  if [[ "$json_out" -eq 1 ]]; then
    printf '%s\n' "$LAST_BODY"
  else
    # Tab-separated table: name / objects / index state. The server returns a
    # boolean `indexed` today; prefer a richer `index_state` string if a future
    # server version ships one (don't hardcode the old shape).
    jq -r '
      "containers: \(.count // ((.containers // []) | length))",
      "NAME\tOBJECTS\tINDEX_STATE",
      ( (.containers // [])[]
        | "\(.name)\t\(.objects // "?")\t\(
            .index_state
            // (if .indexed == true then "indexed"
                elif .indexed == false then "not_indexed"
                else "?" end))"
      )
    ' <<<"$LAST_BODY" 2>/dev/null || {
      err "containers returned non-JSON or unexpected shape:"
      printf '%s\n' "$LAST_BODY" >&2
      exit "$EX_TRANSIENT"
    }
  fi
}

cmd_jobs() {
  local json_out=0 job_id=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --json) json_out=1; shift ;;
      *)      job_id="$1"; shift ;;
    esac
  done
  if [[ -z "$job_id" || ! "$job_id" =~ ^[0-9]+$ ]]; then
    err "usage: $0 jobs [--json] <numeric-job-id>   (the 'pid' returned by /embed and /documents/*)"
    exit "$EX_USAGE"
  fi

  load_config
  http_get_auth "$ENDPOINT/jobs/$job_id" "$ADMIN_MAX_TIME"

  if [[ "$LAST_CURL_RC" -ne 0 || ! "$LAST_HTTP" =~ ^2 ]]; then
    classify_and_exit "$LAST_CURL_RC" "$LAST_HTTP" "$LAST_BODY"
  fi

  if [[ "$json_out" -eq 1 ]]; then
    printf '%s\n' "$LAST_BODY"
  else
    # No top-level `status` field exists — the truth is running/exit_code
    # (done=0, failed=non-0, pending/running=null). Render that as plain words.
    jq -r '
      "job \(.pid // "?"): "
      + (if .running == true then "running"
         elif .exit_code == 0 then "done (exit_code=0)"
         elif (.exit_code != null) then "FAILED (exit_code=\(.exit_code))"
         else "queued (not running yet)" end)
      + (if (.message // "") != "" then " — \(.message)" else "" end)
    ' <<<"$LAST_BODY" 2>/dev/null || {
      err "jobs returned non-JSON or unexpected shape:"
      printf '%s\n' "$LAST_BODY" >&2
      exit "$EX_TRANSIENT"
    }
  fi
}

cmd_errors() {
  local window="24h" category="other" json_out=0
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --json) json_out=1; shift ;;
      --window) window="${2:-}"; shift 2 ;;
      --category) category="${2:-}"; shift 2 ;;
      *) err "unknown errors argument: $1"; exit "$EX_USAGE" ;;
    esac
  done
  [[ "$window" =~ ^(1h|24h|7d|30d)$ ]] || { err "invalid window"; exit "$EX_USAGE"; }
  [[ "$category" =~ ^(all|other|authenticated|unauthenticated_404)$ ]] || { err "invalid category"; exit "$EX_USAGE"; }
  load_config
  http_get_auth "$ENDPOINT/admin/usage/errors?window=$window&category=$category&limit=50" "$ADMIN_MAX_TIME"
  if [[ "$LAST_CURL_RC" -ne 0 || ! "$LAST_HTTP" =~ ^2 ]]; then
    classify_and_exit "$LAST_CURL_RC" "$LAST_HTTP" "$LAST_BODY"
  fi
  if [[ "$json_out" -eq 1 ]]; then printf '%s\n' "$LAST_BODY"; else
    jq -r '"errors: \(.total) | window: \(.window) | category: \(.category)", (.rows[] | "\(.status) \(.method) \(.path) [\(.container // "-")] request=\(.request_id // "historical")\n  \(.error_detail // "Historical response body not recorded")")' <<<"$LAST_BODY"
  fi
}

usage() {
  cat >&2 <<EOF
tm-search.sh — hardened, config-driven retrieval for transcendence-memory,
supporting single-service and multi-service nodes with auto-failover.

Usage:
  $0 status                       Health probe across all configured service nodes.
  $0 node                         Display current client node & service node topology.
  $0 search [options] <query>     Semantic search (LanceDB). Lazy cold-start absorb.
  $0 query  [--json] <question>   Multimodal RAG query (LightRAG + LLM answer).
  $0 containers [--json] [pat]    List containers (name/objects/index state).
  $0 errors [--json] [--window 24h] [--category other]  Redacted error details.
  $0 jobs [--json] <id>           One job's state (running / exit_code, plain words).

Search Options:
  --container, -c <name>          Override default container for this search.
  --union                         Enable cross-container union search.
  --no-union                      Disable union search (query target container only).
  --rerank                        Force reranking on.
  --no-rerank                     Force reranking off.
  --max-distance <float>          Filter hits by LanceDB L2 distance threshold.
  --json                          Emit raw server JSON instead of distilled text.

Env overrides:
  TM_CONFIG_FILE   config path (default ~/.transcendence-memory/config.toml)
  TM_ENDPOINTS     failover service nodes list (comma-separated, e.g. "https://ep1,https://ep2")
  TM_CONTAINER     override default container
  TM_UNION=1       enable union search by default
  TM_NODE_NAME     override auto-detected client node name
  TM_NO_PROXY=1    force direct-only (--noproxy); default = proxy-first + auto
                   direct fallback (proxy is usually the reliable path to a
                   Cloudflare-fronted endpoint; direct is the fallback)
  TM_DIRECT_CONNECT_TIMEOUT   direct-fallback connect-timeout s (default $DIRECT_FALLBACK_CONNECT_TIMEOUT)
  TM_TOPK          search topk (default $DEFAULT_TOPK)
  TM_QUERY_TOPK    query top_k pool (default $DEFAULT_QUERY_TOPK)
  TM_COLD_RETRY_MAX / TM_COLD_RETRY_DELAY_S   cold-start re-send tuning

Exit codes: 0 ok | 64 usage | 77 auth | 75 transient | 78 config | 69 unavailable
EOF
}

# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

main() {
  require_cmd curl
  require_cmd jq

  local sub="${1:-}"
  [[ $# -gt 0 ]] && shift || true

  case "$sub" in
    status)        cmd_status "$@" ;;
    node|nodes|info) cmd_node "$@" ;;
    search)        cmd_search "$@" ;;
    query)         cmd_query "$@" ;;
    containers)    cmd_containers "$@" ;;
    jobs)          cmd_jobs "$@" ;;
    errors)        cmd_errors "$@" ;;
    -h|--help|help|"") usage; [[ -z "$sub" ]] && exit "$EX_USAGE" || exit "$EX_OK" ;;
    *)             err "unknown subcommand: $sub"; usage; exit "$EX_USAGE" ;;
  esac
}

main "$@"

