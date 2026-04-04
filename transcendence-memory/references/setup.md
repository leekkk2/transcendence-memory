# Setup — Transcendence Memory

> Goal: enable a **public-safe self-hosted memory operator pack** while **keeping builtin memory**.

This skill has **two parts**:
- **Frontend / client** — for OpenClaw hosts that talk to a deployed memory service
- **Backend / service** — for the machine that deploys and operates the memory backend

---

## Identity first / 先确认身份

初始化后，当前机器必须生成本地身份文档：

- `operator-identity.md`

该文档用于明确当前机器是：
- `frontend`
- `backend`
- `both`

如果缺少该文档（第一次使用、未正确初始化、意外退出、或状态损坏）：
- 先停止假设当前身份
- 要求用户补录身份
- 重新执行 `transcendence-memory init <role> --dry-run`
- 确认后执行 `transcendence-memory init <role> --yes`

身份确认后，阅读文档和执行命令的优先级必须跟随身份切换。

---

## Runtime alignment / 与真实 backend 对齐

当前 public-safe operator 仓库对接的真实 backend runtime 是 `transcendence-memory-server/`。

因此本 skill 的 setup 文档需要遵守以下边界：
- skill / CLI 文档负责指导 operator 如何部署、连接、验证和排障
- backend runtime 真相以 `transcendence-memory-server/README.md` 与其脚本入口为准
- 当前服务端主链是 **LanceDB-only**
- 当前默认私有 runtime 端口是 `8711`
- 如果 operator 文档与 backend runtime 现实冲突，应先修正文档，而不是强行解释旧口径

---

## Part A — Frontend setup (client hosts)

### 1) Prepare config

Config file shape:
`~/.openclaw/workspace/tools/rag-config.json`

```json
{
  "endpoint": "https://your-memory-endpoint.example.com",
  "auth": {
    "type": "header",
    "name": "X-API-KEY",
    "value": "<RAG_API_KEY>"
  },
  "defaultContainer": "client-a"
}
```

`defaultContainer` should identify the current host or workspace namespace.
Examples:
- `client-a`
- `client-b`
- `lab`

### 2) Ensure env auto-load

Add to your local env file:

```bash
RAG_CONFIG_FILE=$HOME/.openclaw/workspace/tools/rag-config.json
```

### 3) Provide a load script

Create or reuse a local script that exports:
- `RAG_ENDPOINT`
- `RAG_AUTH_HEADER`
- `RAG_API_KEY`
- `RAG_DEFAULT_CONTAINER`

A sanitized example is provided in `load_rag_config.sh`.

### 4) Frontend acceptance

```bash
source ./load_rag_config.sh

curl -sS -i "$RAG_ENDPOINT/health"

curl -sS -i -X POST "$RAG_ENDPOINT/search" \
  -H "$RAG_AUTH_HEADER: $RAG_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{"container":"'$RAG_DEFAULT_CONTAINER'","query":"RAG memory test","topk":3}'

curl -sS -i -X POST "$RAG_ENDPOINT/embed" \
  -H "$RAG_AUTH_HEADER: $RAG_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{"container":"'$RAG_DEFAULT_CONTAINER'","background":true}'
```

If the target flow depends on typed ingest, also verify:

```bash
curl -sS -i -X POST "$RAG_ENDPOINT/ingest-memory/objects" \
  -H "$RAG_AUTH_HEADER: $RAG_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{"container":"'$RAG_DEFAULT_CONTAINER'","objects":[]}'
```

Expected:
- `/health` -> 200
- `/search` -> 200 + real results
- `/embed` -> 200 + success payload
- if typed ingest is in scope, `/ingest-memory/objects` -> accepted/success according to contract

Important:
- `/search` returning HTTP 200 is **not enough** if the body still reports an error
- for a brand-new container, successful `/embed` may be required before `/search` becomes valid
- if `/search` or `/embed` returns 5xx, do **not** report rollout complete

---

## Part B — Backend setup (service hosts)

### 1) Required dependencies

当前 operator 视角只要求 backend host 能稳定运行 `transcendence-memory-server` 所需依赖；不要把早期实现细节误写成当前 canonical 主链。

至少确认：
- Python / venv 可用
- canonical backend runtime 所需依赖可用
- LanceDB runtime 依赖可用
- embedding provider / auth / runtime 目录准备完成

### 2) Canonical backend surfaces

Repository-owned operator surfaces:
- `transcendence-memory backend deploy`
- `transcendence-memory backend health`
- `transcendence-memory backend export-connection`

Current runtime truth surfaces:
- `transcendence-memory-server/README.md`
- `transcendence-memory-server/scripts/run_task_rag_server.sh`
- `transcendence-memory-server/scripts/load_rag_config.sh`

### 3) Service expectations

- backend exposes `/health`, `/search`, `/embed`
- typed ingest path should be available when the target rollout depends on operator-side object ingestion
- `/health` may be anonymous
- business routes require configured auth
- operators should prefer documented deploy/env files over ad hoc shell edits

### 4) Backend acceptance

From the server side, confirm:
- service is running and stable
- `GET /health` -> 200
- `POST /embed` -> accepted/success
- runtime storage/indexing layer is healthy
- `POST /search` -> 200 with real results
- when needed, `POST /ingest-memory/objects` -> accepted/success

### 5) Repair checklist

If the public endpoint fails, check in order:
1. service/container status
2. reverse proxy or advertised URL wiring
3. API key / auth header consistency
4. provider and runtime dependencies
5. backend logs for search/embed/ingest failures
6. whether the operator docs drifted away from the current backend runtime truth

---

## Operating rule

Keep builtin memory enabled; this skill augments retrieval and deployment workflows rather than replacing builtin memory.
