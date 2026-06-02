# API Reference

认证：所有业务端点需要 `X-API-KEY: <key>` 或 `Authorization: Bearer <key>`。

> **v0.7.0+ multi-embedding 提示**：所有 `/embed` / `/ingest-*` / `/search` / `/query` 端点都接受**可选**字段 `embedding_model: str | None`（per-request 强制指定 embedding profile，覆盖默认路由）和 `rerank: bool | None` / `reranker_model: str | None`（v0.8.0+ 控制重排）。**不指定时按 container 名自动路由**，与 v0.6.x 行为完全兼容。详见末尾「Multi-Model 端点（v0.7.0+）」段。

## 目录 (Table of Contents)

- [响应字段别名对照表（坑 D）](#响应字段别名对照表坑-d) — `/search` 与 `/query` 字段名差异、`text`↔`content`/`chunk`、`score`↔`vectorScore`/`rerankScore`、**如何取全文不截断**
- [轻量路径（文本记忆 CRUD）](#轻量路径文本记忆-crud)
  - [GET /health](#get-health)
  - [POST /search](#post-search)
  - [POST /embed](#post-embed)
  - [POST /ingest-memory/objects](#post-ingest-memoryobjects)
  - [GET /ingest-memory/contract](#get-ingest-memorycontract)
  - [POST /ingest-structured](#post-ingest-structured)
  - [PUT /containers/{container}/memories/{id}](#put-containerscontainermemoriesid)
  - [DELETE /containers/{container}/memories/{id}](#delete-containerscontainermemoriesid)
- [多模态路径（RAG-Anything pipeline）](#多模态路径rag-anything-pipeline)
  - [POST /documents/text](#post-documentstext)
  - [POST /documents/upload](#post-documentsupload)
  - [POST /query](#post-query)
- [管理端点](#管理端点)
  - [GET /containers](#get-containers)
  - [DELETE /containers/{name}](#delete-containersname)
  - [GET /export-connection-token](#get-export-connection-token)
  - [GET /jobs/{job_id}](#get-jobsjob_id)
  - [GET /jobs](#get-jobs)
  - [DELETE /jobs/{job_id}](#delete-jobsjob_id)
  - [GET /admin/system-health](#get-adminsystem-health)
- [Multi-Model 端点（v0.7.0+）](#multi-model-端点v070)
- [读取配置的辅助方法](#读取配置的辅助方法)

> 每条命令的最小 curl / 选项速查见 [`commands.md`](./commands.md)；排障见 [`troubleshooting.md`](./troubleshooting.md)。

---

## 响应字段别名对照表（坑 D）

> [!IMPORTANT]
> **症状**：解析检索结果时按 `hit['content']` / `result['vectorScore']` 取值拿到 `KeyError`/`None`，或正文被截断只回到中间一段。**根因**：`/search` 与 `/query` 是两条不同管线，字段名不同；rerank 开启后又可能多出分数字段；长文本被切成多 chunk 后单条命中只含其中一段。本表是字段名与取全文的唯一对照源。

### 1. 两条管线，命中数组与字段名都不同

| 维度 | `POST /search`（LanceDB 轻量路径） | `POST /query`（RAG-Anything + LLM） |
|---|---|---|
| 命中数组字段名 | **`results`**（不是 `hits`） | **`sources`**（不是 `results`/`hits`） |
| 正文字段 | `results[].text` | `sources[].text` |
| 分数字段 | `results[].score` | `sources[].score`（开 rerank 后语义变，见下） |
| 主键线索 | `taskId` + `chunkId`（**无顶级 `id`**） | `chunk_id`（注意是 `chunk_id` 蛇形，非 `chunkId`） |
| 是否含 LLM 综合答案 | 否（只回原文 chunk） | 是（顶级 `answer`） |

> 实测：`/search` 每条命中**没有顶级 `id`**；`/ingest-memory/objects` 写入时给的 `id` **不会**回流到 `results[].id`。下游按 `taskId + chunkId` 或 `text` 内容自行匹配。

### 2. 正文字段别名：`text` 是规范名，可能见到的别名

| 你可能在代码/旧文档/上游库里看到的名字 | 实际在本服务的对应 | 说明 |
|---|---|---|
| **`text`** | ✅ 规范字段 | `/search` `results[].text`、`/query` `sources[].text` 都用它，**优先读 `text`** |
| `content` | 等价别名 | LightRAG / 部分上游把 chunk 正文叫 `content`；本服务回 `text`。自写解析器建议 `hit.get("text") or hit.get("content")` 兜底 |
| `chunk` / `chunk_text` / `snippet` | 等价别名 | 同上，均指"命中片段正文"。本服务规范名仍是 `text` |
| `page_content` | 等价别名 | LangChain 风格命名，本服务不用，做兼容时按 `text` 映射 |

> **取值兜底写法**（防上游/版本字段名漂移）：
> ```python
> body = hit.get("text") or hit.get("content") or hit.get("chunk") or ""
> ```

### 3. 分数字段别名：`score` 与 rerank 后可能出现的 `vectorScore` / `rerankScore`

| 字段 | 何时出现 | 含义 / 区间 |
|---|---|---|
| **`score`** | 始终 | 命中的相关性分。`/search` = LanceDB 余弦距离派生分；`/query` 未开 rerank 时 = 向量召回分 |
| `vectorScore` / `vector_score` | 开 reranker 后可能并列出现 | **重排前**的向量召回原始分，保留用于对比/调试 |
| `rerankScore` / `rerank_score` | 开 reranker 后可能并列出现 | reranker（cross-encoder 或 pseudo-rerank）给出的**重排后**分，区间随 reranker 而异（如 0–1） |

**判定与排序约定**：
- 未开 rerank（默认）：只有 `score`，直接用它排序。
- 开 rerank（`/query` 带 `rerank:true` 或 route 配了 reranker）：若响应同时给出 `score` + `rerankScore`，**以 `rerankScore` 为最终排序依据**；`vectorScore` 仅供观察召回质量。不同部署可能直接把 `score` 覆盖成 rerank 后分而不另给 `rerankScore` —— 取值兜底：
  ```python
  rank = hit.get("rerankScore") or hit.get("rerank_score") or hit.get("score") or 0.0
  ```
- 重要：reranker **只作用于 `/query`**。`/search` 是 LanceDB 直查（cosine + topk），**永远不会**出现 `rerankScore`；如果你在 `/search` 结果里找 rerank 分，那是路径选错了。详见 [per-request 控制 reranker](#per-request-控制-rerankerv080)。

### 4. 如何取全文 / 避免被截断

长文本在 ingest 时会被**切成多个 chunk**（`chunkId` 末尾 `#<idx>` 是切片序号），单条命中只含其中一段；`topk` 又限制返回条数。要拿到完整内容：

1. **调大 `topk`**：默认 5 容易只回到中间几段。取全文时把 `topk` 调到能覆盖该来源所有 chunk 的量（如 30–60），再在客户端按 `taskId` 聚合：
   ```bash
   curl -sS -X POST "${ENDPOINT}/search" \
     -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
     -d '{"container":"${CONTAINER}","query":"<关键词>","topk":50}'
   ```
2. **取 `text` 全字段，别只截前 N 字**：`results[].text` 即该 chunk 的**完整**正文，没有服务端长度截断；任何"只显示一段"的现象都是 **chunk 切分 + topk 限制**，不是字段被截。客户端务必读完整 `text`，不要 `text[:200]`。
3. **同来源多 chunk 聚合**：同一条 ingest 的多个 chunk 共享同一 `taskId`，`chunkId` 仅末尾 `#<idx>` 不同。按 `taskId` 分组、按 `#<idx>` 升序拼接即得原文：
   ```python
   from collections import defaultdict
   groups = defaultdict(list)
   for h in resp["results"]:
       groups[h["taskId"]].append(h)
   for tid, chunks in groups.items():
       chunks.sort(key=lambda c: int(c["chunkId"].rsplit("#", 1)[-1]) if "#" in c["chunkId"] else 0)
       full = "\n".join(c["text"] for c in chunks)
   ```
4. **要"综合答案"而非"原文片段"** → 用 `/query`（返回顶级 `answer`），它对召回的 chunk 做 LLM 综合，不受单 chunk 截断影响；但 `/query` 仅见 `/documents/*` 入图的内容（见 [POST /query](#post-query)）。

> 速查：哪条命令回哪种字段，见 [`commands.md` POST /search 响应 schema](./commands.md#post-search-响应-schema) 与 [`commands.md` /tm query](./commands.md#tm-query--post-query)。

---

## 轻量路径（文本记忆 CRUD）

### GET /health

LB-style 公开健康检查，**无需认证**。日常用这个判断"服务还在不在 / 我能不能发请求"。

```bash
curl -sS "${ENDPOINT}/health"
```

响应（公开字段集，刻意不含具体数值/路径/容器名/env key 名）：
```json
{
  "status": "ok",
  "service": "transcendence-memory-server",
  "architecture": "lancedb-only",
  "build_flavor": "lite",
  "multimodal_capable": false,
  "degraded_reasons": [],
  "runtime_ready": {"search": true, "embed": true, "ingest_memory": true, "query": false, "documents_text": false},
  "accepting_ingest": true,
  "worker_running": true,
  "uptime_seconds": 12345,
  "system_status": {"memory": "ok", "load": "ok", "swap": "ok"},
  "warnings": []
}
```

客户端通常只看：

| 字段 | 含义 | 用法 |
|---|---|---|
| `status == "ok"` | 服务进程活着 | LB 探活 |
| `accepting_ingest` | 准入门是否开放 | `false` 时立即退避，不要继续发送 ingest |
| `runtime_ready.search` / `runtime_ready.query` | 该能力是否就绪 | 客户端选择走哪条 API |
| `system_status` | 各维度压力标签 `ok` / `pressure` | 显示给用户"系统在压力中"，**不给精确数值** |
| `warnings` | 已脱敏的可用性提示 | 日志展示用，例如 `"memory pressure"` 而非 `"available=747MB < 800MB"` |

**安全设计**：`/health` 故意不暴露容器列表 / 阈值数值 / 配置 key 名 / 队列计数 / 绝对路径等。日常运行**不要**依赖这些字段，需要时调下面的 `/admin/system-health`（需鉴权）。

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
| `timeout_s` | int | 否 | subprocess 整体超时秒数（默认 600） |
| `union` | bool | 否 | **v0.11.0+**：单 container 入参时是否自动追加 sibling `_openai` 镜像。`null`（默认）= 走 `profiles.yaml` 的 `union_search_default`；`true/false` 显式覆盖。`containers` / `container_pattern` 模式下被忽略 |
| `per_container_timeout_s` | float | 否 | **v0.11.0+**：单容器子查询超时（0.5–30s，**默认 12.0**，v0.11.1+；v0.11.0 默认 3.0 但 subprocess cold-start 实测不够稳）。仅多容器场景启用；超时容器在 `per_container_status` 标记 `timeout`，不影响其余 |

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
  ],
  "degraded": false,
  "union_applied": false
}
```

**v0.11.0+ 新增字段**：
- `degraded` (bool)：至少一个目标容器 `timeout` / `error` / `not_initialized` → `true`；结果不完整但已尽力合并
- `union_applied` (bool)：单 container 查询自动追加 sibling `_openai` 镜像时为 `true`；客户端可借此区分主动 union 与显式 multi-container 调用
- `per_container_status` 新增 `"timeout"` 取值（per-container 3s 超时）

**自动 union 触发条件**（v0.11.0+）：
- `union_search_default: true`（profiles.yaml 顶层）或单请求 `"union": true`
- 入参只给 `container`（不给 `containers` / `container_pattern`）
- 主容器名不以 `_openai` 结尾（避免镜像查镜像）
- sibling `<container>_openai` 在 server 文件系统上已存在

**注意**：HTTP 200 不代表成功，需检查 body；跨容器场景下检查 `per_container_status` 定位部分失败的容器，检查 `degraded` 判断结果完整性。`per_container_status` 命中 `timeout`/`not_initialized` 或 `degraded:true` 多半是冷启动/未初始化 sibling，见 [`troubleshooting.md` 冷启动段](./troubleshooting.md#冷启动服务端索引未热起http-200-但-body-未就绪)。

> **字段名与取全文**：`results` 数组、`text`/`score` 字段、以及它们与 `/query` 的 `sources`、rerank 后 `vectorScore`/`rerankScore` 的区别，统一见 [响应字段别名对照表（坑 D）](#响应字段别名对照表坑-d)。结果被切成多 chunk / 看似截断时如何取全文也在该段。

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

响应示例（server v0.15.0+，异步入队）：
```json
{"status": "enqueued", "container": "home", "pid": 12345, "job_id": 12345}
```

| 响应字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | `enqueued`（已入队）；旧版 server 同步建图时为 `ok` |
| `pid` | int | 后台建图任务 job_id（客户端优先读此字段） |
| `job_id` | int | 同 `pid` 的别名（部分版本同时返回；客户端两者都接受） |

> **异步入队（server v0.15.0+）**：本端点把建图任务**入队后立即返回**,响应体携带 job 标识（整数 `pid`,部分版本同时给 `job_id`）。知识图谱（实体抽取 + 关系推断 + LLM 索引）由后台单 worker 异步构建,耗时**数十秒至数分钟**。`/query` 在建图完成前召回不到属正常——这是设计如此。用 `GET /jobs/{pid}` 查询进度,skill 侧用 `/tm jobs`。
>
> **旧版 server（< v0.15.0）**：同步建图,响应为 `{"status": "ok", ...}` 无 job 标识,且大文档可能因建图耗时触发 504 / 524 超时。skill 客户端对两种响应都兼容（无 job 标识 → 视为已完成,不记账本）。
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

响应示例（server v0.15.0+，异步入队）：
```json
{"status": "enqueued", "container": "home", "filename": "document.pdf", "pid": 12345, "job_id": 12345}
```

> **异步入队（server v0.15.0+）**：与 `/documents/text` 一致——入队即返回 job 标识（`pid`，部分版本同时给 `job_id`），文件解析 + 知识图谱构建由后台 worker 异步完成。用 `GET /jobs/{pid}` 或 `/tm jobs` 查进度。旧版 server 可能返回 `{"status": "accepted", ...}` 无 job 标识，客户端兼容。
>
> **`POST /documents/file`** 是 `POST /documents/upload` 的 alias，参数与行为完全一致。

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

> **字段名注意**：`/query` 的来源数组叫 **`sources`**（不是 `/search` 的 `results`），主键是蛇形 `chunk_id`（不是 `chunkId`）。开 reranker 后 `score` 语义变为重排后分，可能并列出现 `vectorScore`/`rerankScore` —— 字段别名与排序约定见 [响应字段别名对照表（坑 D）](#响应字段别名对照表坑-d)。

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

查询单个队列任务的状态。`job_id` 是 `/embed`、`/ingest-memory`、`/ingest-structured`、`/documents/text`、`/documents/upload` 入队时返回的 `pid` 字段（v0.5.10+ 起 pid 字段承载 job_id 而非 OS PID）。

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

运维诊断端点（**需鉴权**）。返回公开 `/health` 全部字段 + 全部敏感诊断信息：

- `available_containers` — 容器/租户名清单
- `configuration_guide` — 已配置 / 缺失 / 可选的 env key 名（如 `RAG_API_KEY`、`EMBEDDING_API_KEY`）
- `modules.*.required_keys` / `missing_keys` — 各模块依赖明细
- `scripts_present` / `workspace` / `containers_root` — 内部文件存在性、绝对路径
- `system` — 完整资源快照（`cgroup_mem_limit_mb` / `cgroup_mem_available_mb` / `load_per_cpu` / `swap_used_pct`）
- `thresholds`（与兼容字段 `gate_config` 同值）— 当前生效的 GATE 阈值
- `queue_stats` — 队列各状态计数（`pending` / `running` / `done` / `failed` / `cancelled`）
- `background_jobs` — 活跃后台进程明细（PID / container / label）
- `admit_ok` / `admit_reason` — 准入门状态与原始原因
- `warnings` — 完整原文（含触发阈值的精确数值，例如 `"available=747MB < threshold 800MB"`）

```bash
curl -sS "${ENDPOINT}/admin/system-health" -H "X-API-KEY: ${API_KEY}" | jq
```

**调用时机**：

- 日常运行 → 用公开 `/health`
- 排查 503 / `accepting_ingest=false` 时 → 用本端点拿数值与原因
- 验证 env override 是否生效（`TM_MIN_AVAILABLE_MEM_MB` 等）→ 用本端点读 `thresholds`
- 容器/租户清查 → 用本端点的 `available_containers`，不要去公开 `/health` 找

## Multi-Model 端点（v0.7.0+）

服务端 v0.7.0 起支持多 embedding profile + reranker profile，**插件式可配置**，不绑定特定 model。Profile 通过 server 端 `config/profiles.yaml` 声明，按 container 名自动路由。

### GET /admin/profiles

列出所有已配置的 embedding / reranker profile + route 表（**需鉴权**）。secret 自动 redact（`api_key_configured: bool`，不返回原值）。

```bash
curl -sS "${ENDPOINT}/admin/profiles" -H "X-API-KEY: ${API_KEY}" | jq
```

响应示例：
```json
{
  "embeddings": [
    {"name": "gemini-3072", "provider": "openai_compatible", "model": "gemini-embedding-001", "dim": 3072, "base_url": "https://...", "api_key_configured": true, "max_token_size": 8192, "request_dim": null, "timeout_s": 60.0, "max_retries": 3},
    {"name": "openai-small-1024", "provider": "openai_compatible", "model": "text-embedding-3-small", "dim": 1024, "base_url": "https://...", "api_key_configured": true, ...}
  ],
  "rerankers": [
    {"name": "selfhosted-bge", "provider": "cohere_compatible", "model": "text-reranker", "base_url": "https://...", "api_key_configured": true, "timeout_s": 30.0, "min_score": 0.0}
  ],
  "routes": [
    {"match": {"glob": "*_openai"}, "embedding": "openai-small-1024", "embedding_fallbacks": [], "reranker": null, "rerank_enabled": false, "chunk_top_k": 30, "top_k": 8}
  ],
  "default_route": {"embedding": "gemini-3072", "embedding_fallbacks": [], "reranker": "selfhosted-bge", "rerank_enabled": false, ...}
}
```

### POST /admin/probe-embedding?profile=&lt;name&gt;

对单条 profile 做一次实际探活（**需鉴权**），返回 latency 与实测 dim：

```bash
curl -sS -X POST "${ENDPOINT}/admin/probe-embedding?profile=gemini-3072" \
  -H "X-API-KEY: ${API_KEY}" | jq
```

成功响应：
```json
{"ok": true, "profile": "gemini-3072", "latency_ms": 717, "dim": 3072}
```

失败响应：
```json
{"ok": false, "profile": "openai-small-1024", "latency_ms": 4992, "error": "embedding upstream 503"}
```

用途：部署新 profile 后立即验证；排查为什么 ingest 失败；监控上游可用性。

### per-request 选择 embedding profile

所有 ingest / search / query 端点都接受可选字段 `embedding_model`：

```bash
# 强制指定 openai-small-1024（无视 container 名 → 路由表的默认匹配）
curl -sS -X POST "${ENDPOINT}/embed" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"my-project_openai","embedding_model":"openai-small-1024"}'
```

⚠ **dim 协议**：同一个 container 的 vec_index 维度在第一次写入时锁死。后续 override 必须指向**同 dim** 的 profile，否则 LanceDB schema mismatch 报错。最佳实践：为不同 dim 用不同 container 名（如 `myapp` 走 3072、`myapp_openai` 走 1024）。

### per-request 控制 reranker（v0.8.0+）

```bash
# 临时开启 reranker（即使 route 默认 disabled）
curl -sS -X POST "${ENDPOINT}/query" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"my-project","query":"...","rerank":true}'

# 临时换用 cohere（即使 route 配的是 selfhosted-bge）
curl -sS -X POST "${ENDPOINT}/query" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"my-project","query":"...","reranker_model":"cohere-v3","rerank":true}'
```

> ⚠ **字段名必须是 `rerank`，不是 `enable_rerank`**。Pydantic 严格模式会**静默丢弃**未知字段 — 错的字段名不会报错也不会生效，reranker 仍然不会被调用。

> ⚠ **Reranker 仅作用于 `/query` 路径**。`/search` 是 LanceDB 直查（cosine + topk），不经过任何 rerank。如果客户端全用 `/search`，rerank 配置再完美也永远不会触发。
>
> 数据可来自任一路径：`/query` 在 LightRAG hybrid 模式下，对**LanceDB-only container**（仅 `/ingest-memory/objects` / `/tm remember` 写入）会自动 fallback 用向量检索，reranker 仍正常作用于这些 chunk。要获得更好的 answer 质量（实体抽取 + 关系图），可额外通过 `/documents/text` / `/documents/upload` 入知识图谱。详见 [`best-practices.md`](best-practices.md)。

### 何时用 multi-model 字段

| 场景 | 推荐做法 |
|------|------|
| 日常调用 | **不传** embedding_model / rerank — 走 server 配置的 route 默认 |
| A/B 测试两个 model | 客户端按 user_id hash 切，用 `embedding_model` 强制 |
| 临时切到备 model 应急 | `embedding_model: "<backup-name>"` 配套新 container 名（避免维度冲突）|
| 单次需要高质量重排 | `rerank: true` |
| 单次跨语言查询用 Cohere | `reranker_model: "cohere-v3", rerank: true` |

详细 server 配置见 server 仓 `docs/MULTI_MODEL_GUIDE.md`。

---

## 读取配置的辅助方法

agent 可从本地配置文件读取连接信息：

```bash
ENDPOINT=$(grep 'endpoint' ~/.transcendence-memory/config.toml | head -1 | cut -d'"' -f2)
API_KEY=$(grep 'api_key' ~/.transcendence-memory/config.toml | head -1 | cut -d'"' -f2)
CONTAINER=$(grep 'container' ~/.transcendence-memory/config.toml | head -1 | cut -d'"' -f2)
```
