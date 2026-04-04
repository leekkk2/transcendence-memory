# API Reference

认证：所有业务端点需要 `X-API-KEY: <key>` 或 `Authorization: Bearer <key>`。

---

## 轻量路径（文本记忆 CRUD）

### GET /health

健康检查，无需认证。

```bash
curl -sS "${ENDPOINT}/health"
```

响应示例：
```json
{
  "architecture": "lancedb-only",
  "auth_configured": true,
  "embedding_configured": true,
  "runtime_ready": true,
  "available_containers": ["imac"]
}
```

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
| `topk` | int | 否 | 返回数量（默认 5） |
| `container` | string | 是 | 目标容器 |
| `timeout_s` | int | 否 | 超时秒数（默认 120） |

**注意**：HTTP 200 不代表成功，需检查 body 是否包含错误。

### POST /embed

触发索引重建。存入新记忆、更新或删除记忆后需调用此端点刷新索引。

```bash
curl -sS -X POST "${ENDPOINT}/embed" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","background":false,"wait":true}'
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `container` | string | 是 | 目标容器 |
| `background` | bool | 否 | 后台执行 |
| `wait` | bool | 否 | 等待完成 |
| `timeout_s` | int | 否 | 超时秒数（默认 600，大容器可设更高） |

> **注意**：默认 timeout 为 600 秒。50+ 条记忆的容器 embed 可能需要数分钟。如仍超时，增大 `timeout_s` 或使用 `background: true` 异步模式。
| `timeout_s` | int | 否 | 超时秒数 |

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

默认自动在后台触发 embed（`auto_embed: true`）。批量入库时建议设 `auto_embed: false`，最后手动调一次 `/embed`。

响应示例：
```json
{
  "container": "imac",
  "accepted": 1,
  "stored_path": "...",
  "index_hint": "Run /embed for this container to refresh LanceDB after storing new objects."
}
```

### GET /ingest-memory/contract

查看当前 ingest 语义边界。无需认证。

```bash
curl -sS "${ENDPOINT}/ingest-memory/contract"
```

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
{"status": "updated", "id": "mem-001", "container": "imac"}
```

### DELETE /containers/{container}/memories/{id}

删除指定记忆。删除后需调用 `/embed` 刷新索引。

```bash
curl -sS -X DELETE "${ENDPOINT}/containers/${CONTAINER}/memories/mem-001" \
  -H "X-API-KEY: ${API_KEY}"
```

响应示例：
```json
{"status": "deleted", "id": "mem-001", "container": "imac"}
```

---

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
{"status": "accepted", "container": "imac", "message": "Text document ingested"}
```

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
{"status": "accepted", "container": "imac", "filename": "document.pdf", "pid": 12345}
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

列出所有可用容器。

```bash
curl -sS "${ENDPOINT}/containers" -H "X-API-KEY: ${API_KEY}"
```

响应示例：
```json
{"containers": ["imac", "work", "lab"]}
```

### DELETE /containers/{name}

删除指定容器及其所有数据。**此操作不可逆。**

```bash
curl -sS -X DELETE "${ENDPOINT}/containers/${CONTAINER}" \
  -H "X-API-KEY: ${API_KEY}"
```

响应示例：
```json
{"status": "deleted", "container": "imac"}
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

### GET /jobs/{pid}

查询异步任务状态（如文档上传处理进度）。

```bash
curl -sS "${ENDPOINT}/jobs/12345" -H "X-API-KEY: ${API_KEY}"
```

响应示例：
```json
{"pid": 12345, "status": "running", "progress": "Processing page 3/10"}
```

状态值：`running` | `completed` | `failed`

---

## 读取配置的辅助方法

agent 可从本地配置文件读取连接信息：

```bash
ENDPOINT=$(grep 'endpoint' ~/.transcendence-memory/config.toml | head -1 | cut -d'"' -f2)
API_KEY=$(grep 'api_key' ~/.transcendence-memory/config.toml | head -1 | cut -d'"' -f2)
CONTAINER=$(grep 'container' ~/.transcendence-memory/config.toml | head -1 | cut -d'"' -f2)
```
