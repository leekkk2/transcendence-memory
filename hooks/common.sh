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
