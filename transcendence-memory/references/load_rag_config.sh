#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="${RAG_CONFIG_FILE:-$HOME/.openclaw/workspace/tools/rag-config.json}"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Missing RAG config: $CONFIG_FILE" >&2
  exit 1
fi

export RAG_ENDPOINT="$(jq -r '.endpoint' "$CONFIG_FILE")"
export RAG_AUTH_HEADER="$(jq -r '.auth.name' "$CONFIG_FILE")"
export RAG_API_KEY="$(jq -r '.auth.value' "$CONFIG_FILE")"
export RAG_DEFAULT_CONTAINER="$(jq -r '.defaultContainer' "$CONFIG_FILE")"
