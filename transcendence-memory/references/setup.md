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

curl -sS -i -X POST "$RAG_ENDPOINT/search"   -H "$RAG_AUTH_HEADER: $RAG_API_KEY"   -H 'Content-Type: application/json'   --data '{"container":"'$RAG_DEFAULT_CONTAINER'","query":"RAG memory test","topk":3}'

curl -sS -i -X POST "$RAG_ENDPOINT/embed"   -H "$RAG_AUTH_HEADER: $RAG_API_KEY"   -H 'Content-Type: application/json'   --data '{"container":"'$RAG_DEFAULT_CONTAINER'","background":true}'
```

Expected:
- `/health` -> 200
- `/search` -> 200 + real results
- `/embed` -> 200 + `status=started` or equivalent success

Important:
- `/search` returning HTTP 200 is **not enough** if the body still reports an error
- for a brand-new container, successful `/embed` may be required before `/search` becomes valid
- if `/search` or `/embed` returns 5xx, do **not** report rollout complete

---

## Part B — Backend setup (service hosts)

### 1) Required dependencies

Install or confirm at least:
- fastapi
- uvicorn
- requests
- numpy
- PostgreSQL + pgvector

### 2) Canonical backend surfaces

Repository-owned surfaces:
- `transcendence-memory backend deploy`
- `transcendence-memory backend health`
- `compose.yaml`
- `deploy/systemd/transcendence-memory-backend.service`

### 3) Service expectations

- backend exposes `/health`, `/search`, `/embed`
- `/health` may be anonymous
- business routes require configured auth
- operators should prefer documented deploy/env files over ad hoc shell edits

### 4) Backend acceptance

From the server side, confirm:
- service is running and stable
- `GET /health` -> 200
- `POST /embed` -> accepted/started
- persistence layer is healthy
- `POST /search` -> 200 with real results

### 5) Repair checklist

If the public endpoint fails, check in order:
1. service/container status
2. reverse proxy or advertised URL wiring
3. API key / auth header consistency
4. provider and database dependencies
5. backend logs for search/embed failures

---

## Operating rule

Keep builtin memory enabled; this skill augments retrieval and deployment workflows rather than replacing builtin memory.
