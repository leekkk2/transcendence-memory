#!/usr/bin/env bash
# 共享库：由所有 hook 通过 source 加载，不可直接执行
# Usage: source "$(dirname "$0")/common.sh"

TM_CONFIG_DIR="$HOME/.transcendence-memory"
TM_CONFIG_FILE="$TM_CONFIG_DIR/config.toml"
TM_AUTO_MARKER="$TM_CONFIG_DIR/auto-memory.enabled"

load_config() {
    TM_ENDPOINT=$(grep '^endpoint' "$TM_CONFIG_FILE" 2>/dev/null | sed 's/.*= *"//' | sed 's/".*//' || echo "")
    TM_API_KEY=$(grep '^api_key' "$TM_CONFIG_FILE" 2>/dev/null | sed 's/.*= *"//' | sed 's/".*//' || echo "")
    TM_CONTAINER=$(grep '^container' "$TM_CONFIG_FILE" 2>/dev/null | sed 's/.*= *"//' | sed 's/".*//' || echo "")
}

is_auto_memory_enabled() { [ -f "$TM_AUTO_MARKER" ]; }

escape_for_json() {
    local s="$1"
    s="${s//\\/\\\\}"; s="${s//\"/\\\"}"; s="${s//$'\n'/\\n}"
    s="${s//$'\r'/\\r}"; s="${s//$'\t'/\\t}"
    printf '%s' "$s"
}

# $1: event_name (e.g. "SessionStart"), $2: context text
emit_context() {
    local escaped
    escaped=$(escape_for_json "$2")
    if [ -n "${CURSOR_PLUGIN_ROOT:-}" ]; then
        printf '{\n  "additional_context": "%s"\n}\n' "$escaped"
    elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -z "${COPILOT_CLI:-}" ]; then
        printf '{\n  "hookSpecificOutput": {\n    "hookEventName": "%s",\n    "additionalContext": "%s"\n  }\n}\n' "$1" "$escaped"
    else
        printf '{\n  "additionalContext": "%s"\n}\n' "$escaped"
    fi
}

# tm_search: $1=query, $2=topk(default 5). Returns raw JSON or empty string on failure.
# timeout: connect 3s / total 5s（UserPromptSubmit 不能阻塞用户输入）
tm_search() {
    local escaped_query
    escaped_query=$(escape_for_json "$1")
    curl -sS --connect-timeout 3 --max-time 5 \
        -X POST "${TM_ENDPOINT}/search" \
        -H "X-API-KEY: ${TM_API_KEY}" \
        -H "Content-Type: application/json" \
        -d "{\"container\":\"${TM_CONTAINER}\",\"query\":\"${escaped_query}\",\"topk\":${2:-5}}" \
        2>/dev/null || echo ""
}

# tm_store: $1=text, $2=id, $3=tags_json. 静默失败，不影响 hook 正常退出。
tm_store() {
    local escaped_text
    escaped_text=$(escape_for_json "$1")
    curl -sS --connect-timeout 5 --max-time 15 \
        -X POST "${TM_ENDPOINT}/ingest-memory/objects" \
        -H "X-API-KEY: ${TM_API_KEY}" \
        -H "Content-Type: application/json" \
        -d "{\"container\":\"${TM_CONTAINER}\",\"objects\":[{\"id\":\"${2}\",\"text\":\"${escaped_text}\",\"tags\":${3:-[]}}],\"auto_embed\":true}" \
        2>/dev/null >/dev/null || true
}

# redact_secrets: 在写入 memory / 传递给 LLM 前，对常见 secret 模式做最小占位替换。
# 用法: echo "$text" | redact_secrets       (stdin)
#       redact_secrets "$text"              (单参数)
# 覆盖的模式: OpenAI/Anthropic sk-*, Stripe pk_live_/sk_live_, Slack xoxb-/xoxp-,
#            GitHub ghp_/gho_, AWS AKIA, Bearer token, URL-embedded password,
#            PRIVATE KEY block, JWT-like triple-segment token。
# 设计取舍: 仅 sed/正则、零依赖、行内替换；不做语义识别，宁可漏判也不破坏正常文本。
redact_secrets() {
    local input
    if [ "$#" -ge 1 ]; then
        input="$1"
    else
        input=$(cat)
    fi
    printf '%s' "$input" | sed -E \
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
