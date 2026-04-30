---
name: transcendence-memory
description: Use when connecting to a self-hosted memory backend, searching, storing, or managing memories, importing connection tokens, or troubleshooting retrieval issues. Use this skill whenever the user mentions memory search, RAG retrieval, embedding, memory storage, multimodal document upload, knowledge queries, or wants to connect to a memory service, even if they do not explicitly say "transcendence-memory".
allowed-tools: Bash, Read, Write, Grep, Glob
argument-hint: "[command] [args...]"
---

## What This Skill Does

Provides self-hosted long-term memory for AI agents by connecting to the [transcendence-memory-server](https://github.com/leekkk2/transcendence-memory-server) backend.

Core capabilities:
- **Connect**: complete authentication in one step with a connection token or manual configuration
- **Text memory**: manage structured memories through lightweight CRUD endpoints
- **Multimodal RAG**: upload documents (PDF, image, or Markdown) or raw text into the RAG-Anything pipeline, then ask natural-language questions and get LLM-generated answers
- **Container management**: list and delete containers
- **Troubleshooting**: diagnose connection and retrieval issues

## Install

```bash
npx skills add https://github.com/leekkk2/transcendence-memory --skill transcendence-memory
```

Or inside a Claude Code session:

```text
/plugin marketplace add leekkk2/transcendence-memory
/plugin install transcendence-memory
/reload-plugins
```

After `/reload-plugins`, the four lifecycle hooks (SessionStart / UserPromptSubmit / PostToolUse / Stop) and the `/tm` slash commands are immediately available — no session restart required.

## Principles

- **Keep builtin memory**: server-side memory augments the agent's builtin memory instead of replacing it
- **Zero dependency**: no extra package installation is required; the agent can do everything with native tools such as curl, file I/O, and the Python standard library
- **Progressive loading**: read `references/setup.md` during first-time setup, then this file is enough for day-to-day use
- **Two paths, no auto-bridge**: `/ingest-memory/objects` writes to LanceDB (served by `/search`); `/documents/text` and `/documents/upload` write to the RAG-Anything knowledge graph (served by `/query`). Data ingested through one path is **not** auto-promoted to the other. When you need both `/search` snippets and `/query` synthesis, you must dual-write. See `references/best-practices.md`.

## Built-in Commands

These commands can be invoked through `/transcendence-memory <command>` or the short form `/tm <command>`:

| Command | Purpose | Example |
|------|------|------|
| `connect <token>` | Import a connection token and write local config | `/tm connect eyJlbmRw...` |
| `connect --manual` | Enter endpoint, api_key, and container manually | `/tm connect --manual` |
| `status` | Check connection status and server health | `/tm status` |
| `search <query>` | Run semantic search over memories | `/tm search architecture decision from the last deployment` |
| `search --match <pattern> <query>` | Search across all containers whose name fuzzy-matches `<pattern>` | `/tm search --match yzjx docker compose` |
| `search --all <query>` | Search across **every** container at once | `/tm search --all release notes` |
| `remember <text>` | Store one memory quickly | `/tm remember Port conflicts caused the deployment failure` |
| `update <id> <text>` | Update an existing memory's text in the current container | `/tm update mem-001 New corrected content` |
| `embed` | Rebuild the index for the current container | `/tm embed` |
| `query <question>` | Run a multimodal RAG query and get an LLM-generated answer | `/tm query What is the overall project architecture?` |
| `upload <file>` | Upload a file into the knowledge graph | `/tm upload ./design.pdf` |
| `containers [pattern]` | List containers, optionally filtered by a fuzzy pattern | `/tm containers yzjx` |
| `batch <file.jsonl>` | Bulk import memories | `/tm batch memories.jsonl` |
| `auto on` | Enable automatic memory on git commits | `/tm auto on` |
| `auto off` | Disable automatic memory | `/tm auto off` |
| `auto status` | Show auto-memory configuration | `/tm auto status` |
| `upgrade` | Pull latest skill scripts from the upstream repo | `/tm upgrade` |

### Command: `connect`

Import a connection token or configure the connection manually.

**Token mode** (recommended):
```bash
# Automatically run by the agent after it receives a token:
TOKEN="$1"  # base64 token provided by the user
DECODED=$(echo "$TOKEN" | base64 -d)
ENDPOINT=$(echo "$DECODED" | python3 -c "import sys,json; print(json.load(sys.stdin)['endpoint'])")
API_KEY=$(echo "$DECODED" | python3 -c "import sys,json; print(json.load(sys.stdin)['api_key'])")
CONTAINER=$(echo "$DECODED" | python3 -c "import sys,json; print(json.load(sys.stdin)['container'])")

mkdir -p ~/.transcendence-memory && chmod 700 ~/.transcendence-memory
cat > ~/.transcendence-memory/config.toml << EOF
[connection]
endpoint = "$ENDPOINT"
container = "$CONTAINER"

[auth]
mode = "api_key"
api_key = "$API_KEY"
EOF
chmod 600 ~/.transcendence-memory/config.toml

# Verify the connection
curl -sS "$ENDPOINT/health"
```

**Manual mode**: ask the user for `endpoint`, `api_key`, and `container`, then write `config.toml`.

### Command: `status`

Check connection and server status:
```bash
# Read local config
CONFIG="$HOME/.transcendence-memory/config.toml"
ENDPOINT=$(grep '^endpoint' "$CONFIG" | sed 's/.*= *"//' | sed 's/".*//')
API_KEY=$(grep '^api_key' "$CONFIG" | sed 's/.*= *"//' | sed 's/".*//')
CONTAINER=$(grep '^container' "$CONFIG" | sed 's/.*= *"//' | sed 's/".*//')

# Health check
curl -sS "$ENDPOINT/health" | python3 -m json.tool

# Authentication test
curl -sS -X POST "$ENDPOINT/search" \
  -H "X-API-KEY: $API_KEY" -H "Content-Type: application/json" \
  -d "{\"container\":\"$CONTAINER\",\"query\":\"test\",\"topk\":1}"
```

### Command: `search`

Single-container (default):
```bash
curl -sS -X POST "${ENDPOINT}/search" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container\":\"${CONTAINER}\",\"query\":\"$ARGUMENTS\",\"topk\":5}"
```

Fuzzy multi-container — `--match <pattern> <query>`:
```bash
PATTERN="$1"; shift; QUERY="$*"
curl -sS -X POST "${ENDPOINT}/search" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container_pattern\":\"${PATTERN}\",\"query\":\"${QUERY}\",\"topk\":5}"
```

All containers — `--all <query>`:
```bash
QUERY="$*"
curl -sS -X POST "${ENDPOINT}/search" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container_pattern\":\"\",\"query\":\"${QUERY}\",\"topk\":10}"
```

> 跨容器响应里每条 hit 会带 `container` 字段，并附 `containers` / `per_container_status` 用于诊断。`topk` 是合并后的全局上限，不是每容器独立。

### Command: `remember`

Quickly store one memory with an auto-generated ID and automatic embedding:
```bash
MEM_ID="mem-$(date +%s)"
curl -sS -X POST "${ENDPOINT}/ingest-memory/objects" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container\":\"${CONTAINER}\",\"objects\":[{\"id\":\"${MEM_ID}\",\"text\":\"$ARGUMENTS\",\"tags\":[]}],\"auto_embed\":true}"
```

### Command: `update`

更新当前容器内某条记忆的文本（最常用的字段）。更新后必须执行 `/tm embed` 刷新索引。

```bash
MEM_ID="$1"; shift; NEW_TEXT="$*"
curl -sS -X PUT "${ENDPOINT}/containers/${CONTAINER}/memories/${MEM_ID}" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "$(python3 -c 'import json,sys; print(json.dumps({"text": sys.argv[1]}))' "${NEW_TEXT}")"
echo "提示：执行 /tm embed 以刷新索引。"
```

> 需要同时更新 `title` / `tags` / `metadata` 时，直接走 Quick Reference 中的 PUT 调用即可。

### Command: `containers`

列出当前 endpoint 下的容器，可选模糊过滤：

```bash
PATTERN="${1:-}"
URL="${ENDPOINT}/containers"
[ -n "$PATTERN" ] && URL="${URL}?pattern=${PATTERN}"
curl -sS "$URL" -H "X-API-KEY: ${API_KEY}"
```

示例：
- `/tm containers` — 列出全部
- `/tm containers yzjx` — 列出名字里包含 `yzjx` 的容器（大小写不敏感）

### Command: `query`

Run a multimodal RAG query with knowledge graph retrieval plus LLM answer generation:
```bash
curl -sS -X POST "${ENDPOINT}/query" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"query\":\"$ARGUMENTS\",\"container\":\"${CONTAINER}\",\"mode\":\"hybrid\",\"top_k\":60}"
```

> **Prerequisite**: `/query` only sees content ingested through `/documents/text` or `/documents/upload`. If you only used `/ingest-memory/objects` / `/tm remember`, the answer will be empty. To make memory objects queryable, also dual-write through `/documents/text`. See `references/best-practices.md` §1.2.
>
> **Latency**: After `/documents/text` returns 200, the knowledge graph still needs **20–60 seconds** to build (entity extraction + relation inference + LLM indexing). Querying immediately after ingestion will return "no information" — wait 30s and retry.

### Command: `upload`

Upload a file into the knowledge graph:
```bash
curl -sS -X POST "${ENDPOINT}/documents/upload" \
  -H "X-API-KEY: ${API_KEY}" \
  -F "file=@$1" \
  -F "container=${CONTAINER}"
```

### Command: `batch`

Bulk ingest memories with the bundled script:
```bash
python3 <skill-path>/scripts/batch-ingest.py \
  "${ENDPOINT}" "${API_KEY}" "${CONTAINER}" "$1" [options]
```

Supported options:

| Option | Default | Purpose |
|--------|---------|---------|
| `--max-bytes N` | 512000 | 单批最大字节数 |
| `--batch-size N` | 50 | 单批最大条数 |
| `--redact` | off | 入库前对常见敏感信息脱敏（API key、token、私钥等） |
| `--probe` | off | 入库前先探测 `/ingest-memory/contract` 确认接口 schema |
| `--resume` | off | 基于进度文件跳过已成功的行（断点续传） |
| `--failed-log F` | `<input>.failed.jsonl` | 失败对象写入指定文件 |
| `--test-waf` | — | 自检模式（不入库），对比默认 UA 与 WAF 兼容 UA 的响应，确认 endpoint 是否被 Cloudflare 拦截 |

The script uses WAF-compatible request headers, auto-splits batches on HTTP 413, and logs failed objects for retry.

> **写自定义客户端时一定要带 User-Agent**：Cloudflare 部署的 endpoint 会把 Python urllib / Go net/http / Node fetch 的默认 UA 直接 1010 拦截（与 payload 大小无关）。任何绕过 `batch-ingest.py` 直接 `urllib.request` / `requests` / `fetch` 的脚本，都需要显式 `User-Agent: transcendence-memory-batch/0.2`（或任意非默认值）。详见 `references/troubleshooting.md` → "403 Forbidden（Cloudflare / WAF 拦截）"。

## Quick Reference (for configured users)

### Text Memories (lightweight path)

```bash
# Search memories
curl -sS -X POST "${ENDPOINT}/search" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","query":"what you want to search for","topk":5}'

# Store a memory
curl -sS -X POST "${ENDPOINT}/ingest-memory/objects" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","objects":[{"id":"mem-001","text":"content to store","tags":["tag1"]}]}'

# Rebuild the index after storing a new memory
curl -sS -X POST "${ENDPOINT}/embed" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","background":false,"wait":true}'

# Update a memory
curl -sS -X PUT "${ENDPOINT}/containers/${CONTAINER}/memories/mem-001" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"text":"updated content","tags":["new-tag"]}'

# Delete a memory
curl -sS -X DELETE "${ENDPOINT}/containers/${CONTAINER}/memories/mem-001" \
  -H "X-API-KEY: ${API_KEY}"
```

> After updating or deleting a memory, run `/embed` to refresh the index.

### Multimodal RAG (RAG-Anything pipeline)

```bash
# Ingest raw text into the knowledge graph
curl -sS -X POST "${ENDPOINT}/documents/text" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","text":"long text to ingest...","description":"optional description"}'

# Upload a file (PDF, image, or Markdown)
curl -sS -X POST "${ENDPOINT}/documents/upload" \
  -H "X-API-KEY: ${API_KEY}" \
  -F "file=@/path/to/document.pdf" \
  -F "container=${CONTAINER}"

# Multimodal RAG query that returns an LLM-generated answer
curl -sS -X POST "${ENDPOINT}/query" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"query":"your question","container":"${CONTAINER}","mode":"hybrid","top_k":60}'
```

### Container Management

```bash
# List all containers
curl -sS "${ENDPOINT}/containers" -H "X-API-KEY: ${API_KEY}"

# Fuzzy filter by name (case-insensitive substring; mode also supports prefix / glob)
curl -sS "${ENDPOINT}/containers?pattern=yzjx" -H "X-API-KEY: ${API_KEY}"

# Delete a container
curl -sS -X DELETE "${ENDPOINT}/containers/${CONTAINER}" \
  -H "X-API-KEY: ${API_KEY}"

# Health check
curl -sS "${ENDPOINT}/health"
```

Variables are read from the local config file `~/.transcendence-memory/config.toml`.

## First-Time Setup

On first use, read `references/setup.md` to complete configuration.

The core flow has only two steps:
1. Get a **connection token** from the server (through the `/export-connection-token` endpoint or from an administrator)
2. Run `/tm connect <token>` to finish setup automatically

Or run `/tm connect --manual` and enter the values step by step.

> After configuration is complete, `references/setup.md` no longer needs to be loaded into context.

## API Reference

See `references/api-reference.md` for full request and response formats.

### Lightweight Path (text memory CRUD)

| Endpoint | Method | Purpose | Auth |
|------|------|------|------|
| `/health` | GET | Health check | Not required |
| `/search` | POST | Search memories | Required |
| `/embed` | POST | Rebuild index | Required |
| `/ingest-memory/objects` | POST | Write typed objects | Required |
| `/ingest-memory/contract` | GET | Inspect ingest semantic boundaries | Not required |
| `/ingest-structured` | POST | Ingest structured JSON | Required |
| `/containers/{container}/memories/{id}` | PUT | Update a memory | Required |
| `/containers/{container}/memories/{id}` | DELETE | Delete a memory | Required |

### Multimodal Path (RAG-Anything pipeline)

| Endpoint | Method | Purpose | Auth |
|------|------|------|------|
| `/documents/text` | POST | Ingest text into the knowledge graph | Required |
| `/documents/upload` | POST | Upload PDF, image, or Markdown documents | Required |
| `/query` | POST | Run a multimodal RAG query | Required |

### Administrative Endpoints

| Endpoint | Method | Purpose | Auth |
|------|------|------|------|
| `/containers` | GET | List containers | Required |
| `/containers/{name}` | DELETE | Delete a container | Required |
| `/export-connection-token` | GET | Export a connection token | Required |
| `/jobs/{pid}` | GET | Async job status | Required |

Authentication methods: `X-API-KEY: <api-key>` or `Authorization: Bearer <api-key>`

## Architecture Overview

See `references/ARCHITECTURE.md`.

```text
Agent --HTTPS + API Key--> transcendence-memory-server
                            |-- FastAPI HTTP layer
                            |-- Container isolation
                            |-- Lightweight path: /search + /ingest + /embed
                            |   `-- Embedding -> LanceDB vector store
                            `-- Multimodal path: /documents + /query
                                `-- RAG-Anything -> knowledge graph -> LLM answer
```

## Troubleshooting

See `references/troubleshooting.md`.

Common quick checks:
- **Cannot connect**: run `/tm status` or `curl -sS "${ENDPOINT}/health"`
- **401/403**: verify that the API key is correct
- **Search returns empty**: run `/tm embed` first to rebuild the index
- **Search returns 200 but body contains error / empty after `/tm remember`**: upstream embedding may be rate-limited (server v0.5.2+ auto-retries with backoff); check `/jobs/{pid}` then see `references/troubleshooting.md`
- **Document upload fails**: verify file type and size (PDF, image, Markdown)
- **Query returns empty**: make sure content was ingested via `/documents/text` or `/documents/upload`
- **Updates or deletes not visible**: run `/tm embed` to refresh

## Batch and Async Operations

### Bulk Ingest (large memory sets)

When you need to ingest dozens to thousands of memories:

```bash
# 基本用法
/tm batch memories.jsonl

# 大规模入库推荐：探测 contract + 脱敏 + 断点续传
python3 <skill-path>/scripts/batch-ingest.py \
  "${ENDPOINT}" "${API_KEY}" "${CONTAINER}" memories.jsonl \
  --probe --redact --resume --max-bytes 500000
```

The script batches by both count and byte size, uses WAF-compatible headers, auto-splits on 413, supports secrets redaction, contract probing, resume, and failed-object logging. Zero external dependencies.

### Async Tasks

`/embed` and `/documents/upload` support async mode:

```bash
# Submit an index rebuild asynchronously
curl -sS -X POST "${ENDPOINT}/embed" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","background":true}'

# Check async task status
curl -sS "${ENDPOINT}/jobs/${PID}" -H "X-API-KEY: ${API_KEY}"
```

### Choosing an Operation Mode

| Scenario | Recommended approach |
|------|---------|
| Health checks, single searches, or a few memory writes | Built-in `/tm` commands |
| Bulk ingest of dozens to thousands of memories | `/tm batch file.jsonl --probe --redact` |
| Large-scale ingest with sensitive content | Add `--redact --resume --failed-log` |
| Rebuilding a large container index | `/tm embed` or async mode |
| Adding documents to the knowledge graph | `/tm upload file.pdf` or `/documents/text` |
| Asking for an LLM-synthesized answer | `/tm query your question` |

### Command: `upgrade`

Pull the latest skill from upstream. Auto-detects install location (Claude Code plugin cache / `~/.claude/skills/` / Cursor / direct git clone) and `git pull`s it. If the skill was installed by `npx skills add` (non-git tarball), prints the re-install command instead.

```bash
ROOT=""
for cand in \
  "${CLAUDE_PLUGIN_ROOT:-}" \
  "$HOME/.claude/plugins/cache"/*/transcendence-memory \
  "$HOME/.claude/plugins/cache"/transcendence-memory*/transcendence-memory \
  "$HOME/.claude/skills/transcendence-memory" \
  "$HOME/.cursor/skills/transcendence-memory"; do
  [ -n "$cand" ] && [ -d "$cand/.git" ] && { ROOT="$cand"; break; }
done

if [ -n "$ROOT" ]; then
  cd "$ROOT" && git fetch origin && git pull --ff-only origin main
  echo "Upgraded to $(git rev-parse --short HEAD) at $ROOT"
  echo "→ Restart your AI CLI (Claude Code / Cursor / etc.) to reload SKILL.md."
else
  echo "Skill not installed via git clone. Re-install one of:"
  echo "  • Claude Code plugin:  /plugin update transcendence-memory"
  echo "  • npx skills:          npx skills add https://github.com/leekkk2/transcendence-memory --skill transcendence-memory --force"
fi
```

> 升级会同步刷新 `SKILL.md` / `references/` / `scripts/batch-ingest.py` / 仓库自带的全部 plugin hooks（SessionStart + UserPromptSubmit + PostToolUse + Stop）。升级后重启 AI CLI 即可生效。

### Command: `auto`

Enable, disable, or check automatic memory management.

**Enable** — creates a marker file so hooks auto-store commit summaries:
```bash
mkdir -p ~/.transcendence-memory
touch ~/.transcendence-memory/auto-memory.enabled
echo "Automatic memory enabled. Git commit summaries will be stored automatically."
```

**Disable** — removes the marker file:
```bash
rm -f ~/.transcendence-memory/auto-memory.enabled
echo "Automatic memory disabled."
```

**Status** — check current state:
```bash
if [ -f ~/.transcendence-memory/auto-memory.enabled ]; then
  echo "Automatic memory: ENABLED"
else
  echo "Automatic memory: DISABLED"
fi
if [ -f ~/.transcendence-memory/config.toml ]; then
  ENDPOINT=$(grep '^endpoint' ~/.transcendence-memory/config.toml | sed 's/.*= *"//' | sed 's/".*//')
  CONTAINER=$(grep '^container' ~/.transcendence-memory/config.toml | sed 's/.*= *"//' | sed 's/".*//')
  echo "Endpoint: ${ENDPOINT}"
  echo "Container: ${CONTAINER}"
else
  echo "Not connected. Run /tm connect first."
fi
```

## Automatic Memory

transcendence-memory uses four lifecycle hooks for a fully automatic memory experience. Writing memories requires `auto-memory.enabled`; reading and injecting memories requires only `config.toml` (read-write separation).

### How it works

| Hook | Event | Requires auto-memory | What it does |
|------|-------|---------------------|--------------|
| `session-start` | SessionStart | No (read-only) | Health check + recall relevant memories from previous sessions and inject into context |
| `prompt-inject` | UserPromptSubmit | Keyword: No / Long prompt: Yes | Trigger on recall keywords or long prompts; inject relevant memories before agent responds |
| `post-commit-memory` | PostToolUse (Bash) | Yes | After git commit/merge/rebase, instruct agent to store a commit summary memory |
| `session-stop` | Stop | Yes | Extract last 3 assistant messages from transcript and store as session-summary memory (5-minute throttle) |

All four hooks are installed automatically via `/plugin install transcendence-memory`.

### Enable / disable

```text
/tm auto on       # enable auto-memory (writing: PostToolUse + Stop hooks)
/tm auto off      # disable auto-memory
/tm auto status   # check current configuration
```

Memory recall via SessionStart and UserPromptSubmit (keyword mode) works independently of `auto-memory` — they only need a configured `config.toml`.

### What gets stored

**Auto-commit memory** (PostToolUse):
```
[commit abc1234] fix: resolve port conflict in docker-compose | files: M docker-compose.yml, M .env.example
```
Tagged `auto-commit` for easy filtering: `/tm search auto-commit`

**Session summary memory** (Stop):
```
[session-summary] project:my-project | 2026-04-30T12:00:00Z | <last 3 assistant messages>
```
Tagged `auto-session` + `summary` for filtering: `/tm search session-summary`

## Platform Support

The hooks system is designed to work across multiple AI coding CLIs. The plugin ships pre-built hook configs for supported platforms.

### Claude Code (primary)

Hooks are registered in `hooks/hooks.json` and activated automatically when the plugin is installed via `/plugin install`.

### Cursor

Uses `hooks/hooks-cursor.json` with camelCase event names (`sessionStart`, `postToolUse`).

### Other platforms

The multi-platform adapter (`hooks/adapter.py`) normalizes hook input from:

| Platform | Event format | Detection |
|----------|-------------|-----------|
| Claude Code | `hook_event_name` + `tool_name` | `CLAUDE_PLUGIN_ROOT` env |
| Cursor | Same JSON schema | `CURSOR_PLUGIN_ROOT` env |
| Gemini CLI | `AfterTool` + `matcher` | `matcher` field in JSON |
| Windsurf | `post-tool-use` + `tool` + `arguments` | `arguments` field in JSON |
| Vibe CLI | `post-tool-call` + `tool` + `input` | `input` field in JSON |
| Cline / Roo Code | `tool_name` or `tool` + JSON stdin/stdout | JSON structure detection |
| Copilot CLI | Claude Code compatible | `COPILOT_CLI` env |
| Augment Code | Claude Code compatible | Fallback to Claude format |

For platforms without native hook support, add transcendence-memory instructions to the platform's rules file (e.g., `.cursorrules`, `AGENTS.md`, `.clinerules/`).

## Files in This Skill

| File | Purpose | When to load |
|------|------|---------|
| `references/setup.md` | First-time setup guide | First use only |
| `references/api-reference.md` | Complete API reference | When API details are needed |
| `references/ARCHITECTURE.md` | Architecture and data flow | When understanding the system |
| `references/OPERATIONS.md` | Operational verification and acceptance | During deployment verification |
| `references/troubleshooting.md` | Troubleshooting guide | When something goes wrong |
| `references/best-practices.md` | Dual-path model, dedicated containers, async timing, real-world lessons | Before designing memory layout for a new project, or when `/query` returns empty despite successful ingestion |
| `references/best-practices.zh-CN.md` | Chinese translation of `best-practices.md` | Same as above, when Chinese is preferred |
| `references/templates/config.toml.template` | Config file template | During first-time setup |
| `scripts/batch-ingest.py` | Bulk ingest script | For large memory imports |
| `hooks/common.sh` | Shared bash library for all hooks (config loading, API calls, JSON escaping) | Auto-loaded by hooks |
| `hooks/session-start` | SessionStart hook: health check + memory recall injection | Auto-registered |
| `hooks/prompt-inject` | UserPromptSubmit hook: recall-keyword / long-prompt triggered memory injection | Auto-registered |
| `hooks/post-commit-memory` | PostToolUse hook: instruct agent to store git commit summary | Auto-registered |
| `hooks/session-stop` | Stop hook: auto-store session summary memory | Auto-registered |

## When NOT to Use

- Deploying the backend service -> use the `transcendence-memory-server` repository
- Managing Docker, systemd, or Nginx -> use the `transcendence-memory-server` repository
- Troubleshooting server-side problems such as 5xx errors, storage issues, or logs -> use the `transcendence-memory-server` repository
- Configuring Embedding, LLM, or VLM models -> this is a server-side concern and does not need to be handled by the skill
