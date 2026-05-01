# API Reference

认证：所有业务端点需要 `X-API-KEY: <key>` 或 `Authorization: Bearer <key>`。

---

## 轻量路径（文本记忆 CRUD）

### GET /health

健康检查，无需认证。

```bash
curl -sS "${ENDPOINT}/health"
```

响应包含（v0.5.10+ 新字段）：
```json
{
  "architecture": "lancedb-only",
  "auth_configured": true,
  "embedding_configured": true,
  "runtime_ready": true,
  "available_containers": ["home"],
  "system": {"mem_available_mb": 1800, "load_per_cpu": 1.2, "swap_used_pct": 12.5},
  "accepting_ingest": true,
  "queue_stats": {"pending": 3, "running": 1, "done": 42, "failed": 0, "cancelled": 0},
  "worker_running": true
}
```

`accepting_ingest=false` 表示宿主机当前在 GATE 设置的内存/load/swap 阈值之外，新 ingest 请求会拒绝；客户端应停止发送并退避。`queue_stats` 反映持久化队列里各状态的任务数。

### POST /search

检索记忆。

```bash
curl -sS -X POST "${ENDPOINT}/search" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","query":"搜索内容","topk":5}'
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `query` | string | 是 | 搜索文本 |
| `topk` | int | 否 | 全局返回数量（默认 5），跨容器场景下也是合并后总数 |
| `container` | string | 否 | 单容器搜索，向后兼容字段（默认 `home`） |
| `containers` | string[] | 否 | 显式列出多个容器，优先级最高 |
| `container_pattern` | string | 否 | 模糊匹配容器名（大小写不敏感），优先级高于 `container` |
| `pattern_mode` | string | 否 | `substring`（默认）/ `prefix` / `glob` |
| `timeout_s` | int | 否 | 超时秒数（默认 600） |

跨容器示例：

```bash
# 模糊匹配 my-project* 的所有容器
curl -sS -X POST "${ENDPOINT}/search" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"query":"docker compose","container_pattern":"my-project","topk":5}'

# 显式列出多个容器
curl -sS -X POST "${ENDPOINT}/search" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"query":"deploy","containers":["my-project","my-project_codex"],"topk":10}'
```

跨容器响应新增字段：

```json
{
  "status": "ok",
  "container": "my-project",
  "containers": ["my-project", "my-project_claude", "my-project_codex"],
  "per_container_status": {
    "my-project": "ok",
    "my-project_claude": "ok",
    "my-project_codex": "not_initialized"
  },
  "results": [
    {"container": "my-project", "score": 0.12, "text": "..."},
    {"container": "my-project_claude", "score": 0.18, "text": "..."}
  ]
}
```

**注意**：HTTP 200 不代表成功，需检查 body 是否包含错误；跨容器场景下检查 `per_container_status` 来定位部分失败的容器。

### POST /embed

触发索引重建。存入新记忆、更新或删除记忆后需调用此端点刷新索引。

**v0.5.10+ 起改为持久化队列模式**：默认（`wait=false`）请求会立即返回 `job_id`，由后台单线程 worker 慢速消费，避免大批量入库时把宿主机 IO/embedding API 打爆。重复对同一 container 调用 `/embed` 会自动合并为同一个 pending job。

```bash
# 推荐：立即入队，立即返回，后台慢速索引
curl -sS -X POST "${ENDPOINT}/embed" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}"}'
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `container` | string | 是 | 目标容器 |
| `background` | bool | 否 | 旧字段，保留兼容；语义已并入 `wait` |
| `wait` | bool | 否 | `false`（默认）= 入队立返；`true` = 入队后阻塞轮询直到完成或 `timeout_s` 到期 |
| `timeout_s` | int | 否 | `wait=true` 时的轮询超时（默认 600） |

入队响应（`wait=false`）：
```json
{"command":["embed","my-project"],"code":0,"background":true,"wait":false,"pid":42,"status":"enqueued","note":"Job enqueued (id=42); the background worker will drain it."}
```

> `pid` 字段现在是 **queue job_id**（不再是 OS PID）。用 `GET /jobs/42` 查询进度。

完成响应（`wait=true` 或 worker 已处理完）：
```json
{"command":["embed","my-project"],"code":0,"status":"done","pid":42,"note":"job_id=42 | attempts=1/5"}
```

队列内置指数退避（30→60→120→300→900s，最多 5 次），SIGABRT 等瞬态错误会自动重试，无需客户端再做 retry。

### POST /ingest-memory/objects

写入结构化记忆对象。

```bash
curl -sS -X POST "${ENDPOINT}/ingest-memory/objects" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{
    "container": "${CONTAINER}",
    "objects": [
      {
        "id": "mem-001",
        "text": "要存储的记忆内容",
        "title": "可选标题",
        "source": "来源标识",
        "tags": ["tag1", "tag2"],
        "metadata": {"key": "value"}
      }
    ]
  }'
```

默认 `auto_embed: true`：服务端把 embed 任务入队（同 container 自动合并），后台 worker 稳定消费。批量入库可放心保留 `true`——不会因为批次多而触发任务雪崩。

响应示例：
```json
{
  "container": "home",
  "accepted": 1,
  "stored_path": "...",
  "index_hint": "Embed job queued; the background worker will index this container shortly."
}
```

### GET /ingest-memory/contract

查看当前 ingest 语义边界（接受的字段、类型约束）。无需认证。**建议在大规模批量导入前先调用此端点确认 schema。**

```bash
curl -sS "${ENDPOINT}/ingest-memory/contract"
```

> **最佳实践**：批量导入前先探测 contract 确认字段约束，避免 422。使用 `batch-ingest.py --probe` 可自动完成。

### POST /ingest-structured

结构化 JSON 数据 ingest。

```bash
curl -sS -X POST "${ENDPOINT}/ingest-structured" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{
    "container": "${CONTAINER}",
    "input_path": "/path/to/data.json",
    "doc_type": "structured_json",
    "doc_id": "data-001"
  }'
```

### PUT /containers/{container}/memories/{id}

更新指定记忆。更新后需调用 `/embed` 刷新索引。

```bash
curl -sS -X PUT "${ENDPOINT}/containers/${CONTAINER}/memories/mem-001" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"text":"更新后的内容","tags":["updated"],"metadata":{"version":2}}'
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `text` | string | 否 | 新的记忆文本 |
| `tags` | string[] | 否 | 新的标签列表 |
| `metadata` | object | 否 | 新的元数据 |

响应示例：
```json
{"status": "updated", "id": "mem-001", "container": "home"}
```

### DELETE /containers/{container}/memories/{id}

删除指定记忆。删除后需调用 `/embed` 刷新索引。

```bash
curl -sS -X DELETE "${ENDPOINT}/containers/${CONTAINER}/memories/mem-001" \
  -H "X-API-KEY: ${API_KEY}"
```

响应示例：
```json
{"status": "deleted", "id": "mem-001", "container": "home"}
```

## 多模态路径（RAG-Anything pipeline）

### POST /documents/text

将文本内容入知识图谱。经 RAG-Anything pipeline 处理后可通过 `/query` 检索。

```bash
curl -sS -X POST "${ENDPOINT}/documents/text" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","text":"要入库的长文本内容...","description":"可选描述"}'
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `container` | string | 是 | 目标容器 |
| `text` | string | 是 | 要入库的文本内容 |
| `description` | string | 否 | 文档描述 |

响应示例：
```json
{"status": "ok", "container": "home", "answer": "Text ingested into container home knowledge graph.", "mode": "insert"}
```

> **重要异步行为**：HTTP 200 仅代表"已接收",真正的知识图谱构建（实体抽取 + 关系推断 + LLM 索引）在后台执行,通常需要 **20–60 秒**才能被 `/query` 召回。短文档（< 5KB）多数 30 秒内可用,长文档可能需要数分钟。如刚 ingest 后 `/query` 返回"无信息",**先等再重试**,不要怀疑数据未写入。
>
> **与 `/ingest-memory/objects` 的区别**：本端点写入 RAG-Anything 知识图谱,服务于 `/query`;`/ingest-memory/objects` 写入 LanceDB 向量索引,服务于 `/search`。**两条路径互不相通**——同一份内容如果想被两个端点都召回,需要分别入库。详见 `references/best-practices.md`。

### POST /documents/upload

上传文件入知识图谱。支持 PDF、图片（PNG/JPG）、Markdown。文件经 RAG-Anything 自动解析入库。

```bash
curl -sS -X POST "${ENDPOINT}/documents/upload" \
  -H "X-API-KEY: ${API_KEY}" \
  -F "file=@/path/to/document.pdf" \
  -F "container=${CONTAINER}"
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `file` | file | 是 | 上传的文件（multipart/form-data） |
| `container` | string | 是 | 目标容器 |

响应示例：
```json
{"status": "accepted", "container": "home", "filename": "document.pdf", "pid": 12345}
```

> 大文件上传可能异步处理，通过返回的 `pid` 查询进度。

### POST /query

多模态 RAG 查询。从知识图谱中检索相关内容，由 LLM 生成综合答案。

```bash
curl -sS -X POST "${ENDPOINT}/query" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"query":"你的问题","container":"${CONTAINER}","mode":"hybrid","top_k":60}'
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `query` | string | 是 | 查询文本 |
| `container` | string | 是 | 目标容器 |
| `mode` | string | 否 | 检索模式（默认 `hybrid`） |
| `top_k` | int | 否 | 检索候选数量（默认 60） |

响应示例：
```json
{
  "answer": "根据知识库内容，...",
  "sources": [{"chunk_id": "...", "score": 0.85, "text": "..."}]
}
```

---

## 管理端点

### GET /containers

列出所有可用容器，支持模糊过滤。

```bash
# 全部容器
curl -sS "${ENDPOINT}/containers" -H "X-API-KEY: ${API_KEY}"

# 模糊匹配（大小写不敏感子串）
curl -sS "${ENDPOINT}/containers?pattern=my-project" -H "X-API-KEY: ${API_KEY}"

# 前缀匹配
curl -sS "${ENDPOINT}/containers?pattern=my-project&mode=prefix" -H "X-API-KEY: ${API_KEY}"

# glob 模式
curl -sS "${ENDPOINT}/containers?pattern=my-project_*&mode=glob" -H "X-API-KEY: ${API_KEY}"
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `pattern` | string | 否 | 匹配字符串（最长 64，禁止 `/` 与控制字符） |
| `mode` | string | 否 | `substring`（默认）/ `prefix` / `glob` |

响应示例：
```json
{
  "containers": [
    {"name": "my-project", "objects": 3237, "indexed": true, "last_modified": "2026-04-09T10:00:00Z"},
    {"name": "my-project_claude", "objects": 69, "indexed": true, "last_modified": "2026-04-10T08:30:00Z"},
    {"name": "my-project_codex", "objects": 1, "indexed": false, "last_modified": "2026-04-11T12:00:00Z"}
  ],
  "count": 3
}
```

### DELETE /containers/{name}

删除指定容器及其所有数据。**此操作不可逆。**

```bash
curl -sS -X DELETE "${ENDPOINT}/containers/${CONTAINER}" \
  -H "X-API-KEY: ${API_KEY}"
```

响应示例：
```json
{"status": "deleted", "container": "home"}
```

### GET /export-connection-token

导出连接令牌，用于分享给其他 agent。

```bash
curl -sS "${ENDPOINT}/export-connection-token?container=${CONTAINER}" \
  -H "X-API-KEY: ${API_KEY}"
```

响应示例：
```json
{"token": "eyJlbmRwb2ludCI6Imh0dHBz..."}
```

### GET /jobs/{job_id}

查询单个队列任务的状态。`job_id` 是 `/embed`、`/ingest-memory`、`/ingest-structured` 入队时返回的 `pid` 字段（v0.5.10+ 起 pid 字段承载 job_id 而非 OS PID）。

```bash
curl -sS "${ENDPOINT}/jobs/12345" -H "X-API-KEY: ${API_KEY}"
```

响应示例（pending/running）：
```json
{"pid": 12345, "running": true, "exit_code": null, "message": "status=running attempts=1/5"}
```

响应示例（已完成）：
```json
{"pid": 12345, "running": false, "exit_code": 0, "message": "status=done attempts=1/5"}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `pid` | int | Queue job_id（不是 OS PID） |
| `running` | bool | `pending` 或 `running` 状态时为 true |
| `exit_code` | int \| null | `done` 时为 0；其他状态为 null |
| `message` | string | `status=<status> attempts=<n>/<max>`，失败时附 last_error |

```bash
# 推荐轮询示例（每 5 秒一次）
until ! curl -sS "${ENDPOINT}/jobs/${JOB_ID}" -H "X-API-KEY: ${API_KEY}" | python3 -c "import json,sys; sys.exit(0 if json.load(sys.stdin).get('running') else 1)"; do
  sleep 5
done
```

### GET /jobs

列出队列内容，可按 `status` 和 `container` 过滤。用于排障"为什么我的索引还没好"。

```bash
curl -sS "${ENDPOINT}/jobs?status=pending&limit=20" -H "X-API-KEY: ${API_KEY}"
```

| 查询参数 | 说明 |
|------|------|
| `status` | `pending` / `running` / `done` / `failed` / `cancelled` |
| `container` | 精确匹配容器名 |
| `limit` | 1–500，默认 50 |

响应包含 `jobs`（任务列表）、`stats`（按状态计数）、`worker_running`（worker 是否在跑）。

### DELETE /jobs/{job_id}

取消一个 `pending` 任务。`running`/`done` 等其他状态会返回 409。

```bash
curl -sS -X DELETE "${ENDPOINT}/jobs/12345" -H "X-API-KEY: ${API_KEY}"
```

### GET /admin/system-health

运维诊断端点：返回宿主机内存/load 快照、当前 GATE 配置、所有活跃后台进程明细。用于回答"为什么 ingest 被拒"或"系统是否在压力下"。

```bash
curl -sS "${ENDPOINT}/admin/system-health" -H "X-API-KEY: ${API_KEY}" | jq
```

## 读取配置的辅助方法

agent 可从本地配置文件读取连接信息：

```bash
ENDPOINT=$(grep 'endpoint' ~/.transcendence-memory/config.toml | head -1 | cut -d'"' -f2)
API_KEY=$(grep 'api_key' ~/.transcendence-memory/config.toml | head -1 | cut -d'"' -f2)
CONTAINER=$(grep 'container' ~/.transcendence-memory/config.toml | head -1 | cut -d'"' -f2)
```
