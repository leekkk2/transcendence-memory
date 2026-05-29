# Command Reference

Detailed HTTP / curl / script invocations for every built-in command exposed by
the `transcendence-memory` skill. The main `SKILL.md` lists each command in the
**Built-in Commands** table and links here for the full implementation.

Variables `$ENDPOINT`, `$API_KEY`, `$CONTAINER` are read from
`~/.transcendence-memory/config.toml` (see `setup.md`). Always send
`User-Agent: transcendence-memory-skill/0.4` when calling endpoints fronted by
Cloudflare — the default `python-urllib` / `node-fetch` UA is WAF-blocked
(`troubleshooting.md` → "403 Forbidden").

---

## `connect`

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

---

## `status`

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

---

## `search`

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

### v0.11.0+：默认 union 双轨召回

如果 server 端 `profiles.yaml` 设了 `union_search_default: true`，单 container 查询会**自动同时查 sibling `_openai` 镜像**（gemini-3072 + openai-1024 双轨召回），结果按 `(taskId, chunkId)` 去重后合并。响应里多了两个字段：

- `union_applied: true` — 自动 union 触发
- `degraded: true` — 至少一个目标容器超时 / 失败（默认 per-container 3s timeout）
- `per_container_status: {<X>: 'ok', <X>_openai: 'ok' | 'timeout' | 'not_initialized'}`

强制单容器查询（即使 server 启用了默认 union）：

```bash
curl -sS -X POST "${ENDPOINT}/search" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container\":\"${CONTAINER}\",\"query\":\"${QUERY}\",\"topk\":5,\"union\":false}"
```

强制 union（即使 server 默认关闭，且 sibling `_openai` 必须已存在）：

```bash
curl -sS -X POST "${ENDPOINT}/search" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container\":\"${CONTAINER}\",\"query\":\"${QUERY}\",\"topk\":5,\"union\":true}"
```

> 自定义 per-container timeout（v0.11.1+ 默认 12.0s，范围 0.5–30）：加 `\"per_container_timeout_s\":5.0`。生产端 subprocess cold-start 实测 5-10s（py + lancedb + lightrag import + table load + embed call），v0.12 in-process 化后可降回 3s。
> 显式 `containers` / `container_pattern` 参数会跳过自动 union（用户已掌控全部目标）。

### Response schema (实测速查)

`/search` 顶层返回的命中数组字段名是 **`results`**（不是 `hits`），每条命中的字段如下：

```json
{
  "status": "ok",
  "results": [
    {
      "score": 0.56,
      "container": "my-container",
      "taskId": "<source-task>",
      "chunkId": "<taskId>#client-ingest#<idx>",
      "docType": "client_ingest",
      "sourcePath": "tasks/rag/containers/<container>/memory_objects.jsonl",
      "section": "client_ingest",
      "title": "",
      "source": "",
      "text": "...",
      "tags": [],
      "metadata": {}
    }
  ]
}
```

**关键解析约定**：

- 每条命中**没有顶级 `id` 字段**。`/ingest-memory/objects` 时给的 `id` 字段不会原样回流到 `results[].id`；下游需要按 `taskId + chunkId` 或 `text` 内容自行匹配
- 同一条 ingest 的长文本**会被切成多个 chunks**（`chunkId` 末尾 `#<idx>` 是切片序号）；search 可能返回多条同 `taskId` 的不同 chunk
- `title` 字段在多数情况下为空 `""`，即使 ingest 时显式给了；以 `text` 头几行为准
- 详细字段定义见 [`api-reference.md` §POST /search](./api-reference.md#post-search)

---

## `remember`

Quickly store one memory with an auto-generated ID and automatic embedding:

```bash
MEM_ID="mem-$(date +%s)"
curl -sS -X POST "${ENDPOINT}/ingest-memory/objects" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container\":\"${CONTAINER}\",\"objects\":[{\"id\":\"${MEM_ID}\",\"text\":\"$ARGUMENTS\",\"tags\":[]}],\"auto_embed\":true}"
```

---

## `update`

更新当前容器内某条记忆的文本（最常用的字段）。更新后必须执行 `/tm embed` 刷新索引。

```bash
MEM_ID="$1"; shift; NEW_TEXT="$*"
curl -sS -X PUT "${ENDPOINT}/containers/${CONTAINER}/memories/${MEM_ID}" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "$(python3 -c 'import json,sys; print(json.dumps({"text": sys.argv[1]}))' "${NEW_TEXT}")"
echo "提示：执行 /tm embed 以刷新索引。"
```

> 需要同时更新 `title` / `tags` / `metadata` 时，直接走下方 Quick Reference 中的 PUT 调用即可。

---

## `embed`

Rebuild the index for the current container. Server v0.5.10+ enqueues this into
a persistent queue and returns immediately with a `job_id` (legacy `pid`
field). The single background worker drains jobs at a stable host-friendly
pace; duplicate `/embed` calls for the same container coalesce into one
pending job.

```bash
curl -sS -X POST "${ENDPOINT}/embed" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}"}'
```

---

## `containers`

列出当前 endpoint 下的容器，可选模糊过滤：

```bash
PATTERN="${1:-}"
URL="${ENDPOINT}/containers"
[ -n "$PATTERN" ] && URL="${URL}?pattern=${PATTERN}"
curl -sS "$URL" -H "X-API-KEY: ${API_KEY}"
```

示例：

- `/tm containers` — 列出全部
- `/tm containers my-project` — 列出名字里包含 `my-project` 的容器（大小写不敏感）

Container deletion:

```bash
curl -sS -X DELETE "${ENDPOINT}/containers/${CONTAINER}" \
  -H "X-API-KEY: ${API_KEY}"
```

---

## `query`

Run a multimodal RAG query with knowledge graph retrieval plus LLM answer generation:

```bash
curl -sS -X POST "${ENDPOINT}/query" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"query\":\"$ARGUMENTS\",\"container\":\"${CONTAINER}\",\"mode\":\"hybrid\",\"top_k\":60}"
```

> **Prerequisite**: `/query` only sees content ingested through `/documents/text` or `/documents/upload` (LanceDB-only memories via `/tm remember` won't synthesize). Dual-write: see `best-practices.md` §1.2. **Async semantics**: do not poll — see the main SKILL.md `## AI Behavior — async ingestion silent-mode` block.

---

## `upload`

Upload a file into the knowledge graph (async — record one ledger entry, no polling).

```bash
RESP=$(curl -sS -X POST "${ENDPOINT}/documents/upload" \
  -H "X-API-KEY: ${API_KEY}" -H "User-Agent: transcendence-memory-skill/0.4" \
  -F "file=@$1" -F "container=${CONTAINER}")
echo "$RESP"
# Record the job id (skipped automatically if an old sync server returns no id):
echo "$RESP" | python3 "<skill-path>/scripts/job-ledger.py" add \
  --endpoint "${ENDPOINT}" --container "${CONTAINER}" --kind upload --source "/tm upload"
```

---

## `batch`

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

> **写自定义客户端时一定要带 User-Agent**：Cloudflare 部署的 endpoint 会把 Python urllib / Go net/http / Node fetch 的默认 UA 直接 1010 拦截（与 payload 大小无关）。任何绕过 `batch-ingest.py` 直接 `urllib.request` / `requests` / `fetch` 的脚本，都需要显式 `User-Agent: transcendence-memory-batch/0.2`（或任意非默认值）。详见 `troubleshooting.md` → "403 Forbidden（Cloudflare / WAF 拦截）"。

---

## `jobs`

List background knowledge-graph build jobs from the local ledger.
`/documents/text` / `/documents/upload` are async (server v0.15.0+); this reads
`~/.transcendence-memory/pending-jobs.jsonl` and re-checks `/jobs/{id}` per
entry.

```bash
python3 "<skill-path>/scripts/job-ledger.py" list
```

Shows in-progress / failed (with reason — retryable) / recently-done. You
rarely need this: successes are silent, failures are surfaced by the
SessionStart hook.

---

## `upgrade`

Pull the latest skill from upstream. Auto-detects install location (Claude Code
plugin cache / `~/.claude/skills/` / Cursor / direct git clone) and `git
pull`s it. If the skill was installed by `npx skills add` (non-git tarball),
prints the re-install command instead.

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

> **若升级失败（`fatal: Not possible to fast-forward`）**: 本地有 cherry-pick 副本 / divergence。处理：`git tag backup/pre-upgrade-$(date +%Y%m%d) HEAD && git reset --hard origin/main`。完全可回退 (`git reset --hard backup/pre-upgrade-<date>`)。

---

## `auto`

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

---

## Quick Reference (consolidated curl matrix)

For users / scripts that need a single-page summary of every endpoint.

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

# Rebuild the index after storing a new memory.
curl -sS -X POST "${ENDPOINT}/embed" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}"}'

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
# Ingest raw text into the knowledge graph. Async (server v0.15.0+) — record
# the returned job_id with scripts/job-ledger.py add. Do not poll.
curl -sS -X POST "${ENDPOINT}/documents/text" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -H "User-Agent: transcendence-memory-skill/0.4" \
  -d '{"container":"${CONTAINER}","text":"long text to ingest...","description":"optional description"}'

# Upload a file (PDF, image, or Markdown) — async, same job-id semantics as /documents/text.
curl -sS -X POST "${ENDPOINT}/documents/upload" \
  -H "X-API-KEY: ${API_KEY}" \
  -H "User-Agent: transcendence-memory-skill/0.4" \
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
curl -sS "${ENDPOINT}/containers?pattern=my-project" -H "X-API-KEY: ${API_KEY}"

# Delete a container
curl -sS -X DELETE "${ENDPOINT}/containers/${CONTAINER}" \
  -H "X-API-KEY: ${API_KEY}"

# Health check
curl -sS "${ENDPOINT}/health"
```

Variables are read from the local config file `~/.transcendence-memory/config.toml`.

Auth methods: `X-API-KEY: <api-key>` or `Authorization: Bearer <api-key>`.
