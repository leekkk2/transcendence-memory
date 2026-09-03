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
  - [GET /index-status · GET /containers/{name}/index-status（v0.18）](#get-index-status--get-containersnameindex-statusv018)
  - [POST /embed-multimodal（v0.18）](#post-embed-multimodalv018)
  - [容器 alias 路由（v0.18）](#容器-alias-路由v018)
  - [GET /admin/usage/*（v0.18）](#get-adminusagev018)
  - [GET /admin/ui/*（v0.18）](#get-adminuiv018)
- [治理与梦境端点（v0.20）](#治理与梦境端点v020)
- [Multi-Model 端点（v0.7.0+）](#multi-model-端点v070)
- [读取配置的辅助方法](#读取配置的辅助方法)

> 每条命令的最小 curl / 选项速查见 [`commands.md`](./commands.md)；排障见 [`troubleshooting.md`](./troubleshooting.md)。
> 治理 / 梦境 / 编排 Agent 子系统的总览与安全模型见 [`governance.md`](./governance.md)。

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
| `per_container_timeout_s` | float | 否 | **v0.11.0+**：单容器子查询超时（0.5–30s，**默认 12.0**，v0.11.1+；v0.11.0 默认 3.0 但 subprocess cold-start 实测不够稳；v0.19.0 起 server 默认放宽到 30.0）。仅多容器场景启用；超时容器在 `per_container_status` 标记 `timeout`，不影响其余 |
| `score_threshold` | float\|null | 否 | **v0.19.0**：请求级 score-gate（L2 距离上界，越小越相关）。`null`=随 `profiles.yaml` 的 `similarity_threshold`（默认 None=关）；`≤0`=显式关；请求级优先于全局配置。被拦命中数计入响应 `blocked_low_score` |

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

**v0.19.0 新增字段**（全部 opt-in / 向后兼容；旧客户端收到"关闭"语义默认值，逐字节不破坏现有逻辑）：
- `is_degraded` (bool) = `degraded` 的 Agent 友好别名（**同值双写**）；`fallback_source` (str|null)：部分容器成功时 = `"partial_containers"`，否则 `null`
- `citations` (array)：命中的结构化溯源，每项 `{chunkId, sourcePath, section, score, container, lineStart, lineEnd}`。`/search` 默认**开**（`citation_enabled=true`，可经 Dashboard 热重载）
- `results[].lineStart` / `lineEnd` (int|null) + `citations[].lineStart`/`lineEnd`：命中 chunk 的源文件 **1-based 起止行号**。**P4（行号溯源）前 ingest 的老 chunk 恒 `null`**——行号存于 chunk `metadata` JSON，**无 LanceDB schema 迁移、无需 re-embed**；新 chunk ingest 后自动带值，客户端 ingest **无需传任何新字段**（server 端自动算）
- `blocked_low_score` (int)：被 score-gate 拦掉的命中数，**默认 0**（score-gate 默认关）。请求级 `score_threshold` 或服务端 `similarity_threshold` 开启后才可能 `>0`
- `fallback_rendered` (str|null)：**默认 `null`**。仅当服务端配了 `fallback_template` 且发生 score-gate 全拦 / 全容器降级时渲染结构化兜底串——**非高置信检索结果**，客户端默认无感
- `rerank_applied` (bool)：本次是否经 reranker 重排（`/search` 恒 `false`，rerank 仅作用于 `/query`）

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

**v0.19.0 新增字段**（向后兼容；与 `/search` 同名字段语义一致）：
- `top_score` (float|null)：score-gate 命中时透出的 top1 chunk L2 距离；**默认关时恒 `null`**
- `citations` (array)：答案级结构化溯源。**`/query` 默认关**（`query_citation_enabled=false`）→ 恒为 `[]`；运维侧开启后才回填。注意与 `/search` 不同：`/search` 的 citations 默认**开**
- `fallback_rendered` (str|null)：**默认 `null`**。仅服务端配了 `fallback_template` 且 `not_initialized`/`score_gated` 时渲染兜底串，客户端默认无感

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

响应：
```json
{
  "container": "my-project",
  "deleted": true,
  "message": "Container my-project deleted."
}
```

### POST /containers/{name}/rename · PUT /containers/{name}/rename

物理重命名指定 canonical 容器。

- **入参**：`{"new_name": "<new_canonical_name>"}`
- **校验规则**：
  - 必须为 canonical 容器名（禁止通过 alias 改名，避免副作用）；
  - `new_name` 必须符合容器命名规则（仅支持字母、数字、下划线、中划线，长度 1-64）；
  - 目标容器名若已存在则拒绝（409 Conflict）；
  - 容器当前若正在进行后台索引（indexing）则拒绝（409 Conflict）。
- **同步迁移与副作用**：
  - 物理目录：原子移动 `tasks/rag/containers/<old_name>` 至 `<new_name>`；
  - 元数据：自动迁移对应 `container_metadata`；
  - 别名表：自动将所有原指向 `old_name` 的 alias 重定向至 `new_name`。

```bash
curl -sS -X POST "${ENDPOINT}/containers/${OLD_NAME}/rename" \
  -H "X-API-KEY: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"new_name": "new-container-name"}'
```

响应示例：
```json
{
  "old_name": "old-container-name",
  "new_name": "new-container-name",
  "renamed": true,
  "message": "Container old-container-name successfully renamed to new-container-name."
}
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

### GET /index-status · GET /containers/{name}/index-status（v0.18）

容器索引状态机（**需鉴权**）。union 多容器检索前，用它判断某个 sibling 是否**真的 embed 过**（避免把空镜像拉进来拖累整体）。

```bash
curl -sS "${ENDPOINT}/index-status" -H "X-API-KEY: ${API_KEY}" | jq               # 全容器批量
curl -sS "${ENDPOINT}/containers/${CONTAINER}/index-status" -H "X-API-KEY: ${API_KEY}" | jq  # 单容器
```

单容器响应：

```json
{
  "container": "my-project",
  "state": "ready",
  "total_objects": 128,
  "embedded_objects": 128,
  "backlog_active": 0,
  "backlog_counts": {"waiting": 0, "retrying": 0, "dead": 0},
  "dead_count": 0,
  "job_running": false,
  "next_retry_at": null,
  "last_error_class": null,
  "last_embed_ok_at": "2026-06-08T12:00:00Z",
  "last_embed_attempt_at": "2026-06-08T12:00:00Z"
}
```

| 字段 | 含义 |
|---|---|
| `state` | 实时推导的状态机值（`ready` / `indexing` / `stale` / `unknown` …）。`embedded_objects:0` 的从未 embed 容器落 `stale`/`unknown` |
| `total_objects` / `embedded_objects` | 对象总数 / 已 embed 数（子进程权威计数；无记录时回退 jsonl 行数） |
| `backlog_active` / `backlog_counts` / `dead_count` | embedding backlog 摘要（含死信） |
| `job_running` | 该容器是否有 embed 类 job 在 pending/running |
| `next_retry_at` / `last_error_class` | backlog 下次重试时刻 / 最近错误类 |

- 批量端点包成 `{"containers": [ <上述对象>, ... ], "count": N}`，容器并集 = 曾 embed 过 ∪ 有 backlog ∪ 当前目录。
- 单容器：入参是 alias 时解析到 canonical；`removed` 容器 410；完全无记录 404。
- **典型用法**：union 前查 sibling 的 `state` ——非 `ready` 就别 union（v0.18 server 也会自动软跳过未就绪 sibling）。

### POST /embed-multimodal（v0.18）

把单个媒体文件（图 / 音 / 视频）经 Gemini 原生多模态 embedding 算成统一向量空间的**一条 LanceDB 行**，`/search` 即可向量检回。与 `/documents/upload` 不同：后者走 RAGAnything + mineru 解析 + 知识图谱（图片靠 VLM 转写），本端点路径最短、不建 KG。**multipart 表单**（需鉴权）：

```bash
curl -sS -X POST "${ENDPOINT}/embed-multimodal" \
  -H "X-API-KEY: ${API_KEY}" \
  -F "container=${CONTAINER}" -F "file=@./photo.jpg" \
  -F "caption=可选文字描述" -F "doc_id=可选稳定 id"
```

| 表单字段 | 必需 | 说明 |
|---|---|---|
| `container` | 是 | 目标容器，须路由到 `gemini_native` provider 的 embedding profile |
| `file` | 是 | 媒体二进制 |
| `caption` | 否 | 给出时与媒体作为联合 part 一起 embed，并作为该行可读文本；缺省回退文件名 |
| `doc_id` | 否 | 稳定 id（缺省由 container+filename 派生） |

缺 `caption` 时服务端经 route 的 VLM fallback 链 **best-effort** 自动生成 caption（全链挂也不阻塞落库——媒体原生向量仍可检回）。错误码：空文件 400 / 超 inline 限 413 / 不支持的 mime 415 / 上游 embed 失败 502。落库行 `docType:"multimodal"`、`source:"embed-multimodal"`、`metadata` 含 `modality`/`mime_type`/`size_bytes`/`caption`/`caption_source`。

### 容器 alias 路由（v0.18）

把短的 alias 名映射到真实 canonical 容器（**需鉴权，admin**）。删除只摘路由记录，**不**触碰 canonical 物理数据。

```bash
# upsert 一条 alias
curl -sS -X POST "${ENDPOINT}/containers/aliases" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"alias":"proj","canonical":"my-project","reason":"shorthand","status":"active","notes":""}'

curl -sS "${ENDPOINT}/containers/aliases" -H "X-API-KEY: ${API_KEY}"          # 列出 → {"aliases":[...],"count":N}
curl -sS -X DELETE "${ENDPOINT}/containers/aliases/proj" -H "X-API-KEY: ${API_KEY}"  # 删 → {"deleted":true,"alias":"proj"}
```

| body 字段（POST） | 必需 | 说明 |
|---|---|---|
| `alias` / `canonical` | 是 | 均走 `validate_container_name`（防路径遍历） |
| `status` | 否 | `active`（默认）/ `deprecated` / `removed`；其它值 400 |
| `reason` / `notes` | 否 | 备注 |

DELETE 不存在的 alias → 404。alias 删后该名回退「未注册」，下次写入会被当新容器自动创建。

### GET /admin/usage/*（v0.18）

请求用量分析（**需鉴权**），数据源是队列 DB 的请求日志。

```bash
curl -sS "${ENDPOINT}/admin/usage/summary?window=24h"                         -H "X-API-KEY: ${API_KEY}" | jq
curl -sS "${ENDPOINT}/admin/usage/endpoints?window=7d&sort=calls&limit=20"    -H "X-API-KEY: ${API_KEY}" | jq
curl -sS "${ENDPOINT}/admin/usage/containers?window=7d&sort=calls&limit=50"   -H "X-API-KEY: ${API_KEY}" | jq
curl -sS "${ENDPOINT}/admin/usage/timeseries?path=/search&window=7d&bucket=1h" -H "X-API-KEY: ${API_KEY}" | jq
curl -sS -X POST "${ENDPOINT}/admin/usage/cleanup" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"retention_days":90}'
```

| 端点 | 关键 query / body | 说明 |
|---|---|---|
| `GET /summary` | `window`（默认 `24h`） | 窗口内总览 |
| `GET /endpoints` | `window` `7d` · `sort` `calls` · `limit` `20` | 按端点聚合（`sort` 非法值 400） |
| `GET /containers` | `window` `7d` · `sort` `calls` · `limit` `50` | 按容器聚合 |
| `GET /timeseries` | `path`（**必需**）· `window` `7d` · `bucket` `1h` | 单端点时间序列 |
| `POST /cleanup` | body `retention_days` | 删超保留期的用量记录 |

### GET /admin/ui/*（v0.18）

Cookie-session 管理面板（浏览器向；agent 一般用上面的 JSON 端点而非走 UI）。`POST /admin/ui/login`（body `{"password":"..."}` 形态的 `LoginRequest`）签发 HttpOnly + SameSite=Strict 会话 cookie（`TM_ENV=dev` 时关 `Secure` 以便本地 HTTP 调试）；`POST /admin/ui/logout` 清会话；`GET /admin/ui/me` 回当前登录态。POST 路由强制 `X-Requested-With: XMLHttpRequest`（CSRF 防御）。`GET /admin/ui` 及 `GET /admin/ui/{path}` 兜底服务构建好的 React bundle（`/app/static/admin`）。

## 治理与梦境端点（v0.20）

> 服务端 v0.20 自治记忆治理子系统的 HTTP 契约。**全部走统一鉴权**（`X-API-KEY` / `Authorization: Bearer <api-key>` / cookie session 任一）。全部**降级安全**——存储/网关故障返回降级状态而非 5xx。总览 + 安全模型见 [`governance.md`](./governance.md)；命令速查见 [`commands.md`](./commands.md)。
>
> 安全骨架：**dry-run-first → 可逆动作需 `dry_run=false` AND `allow_apply=true` 双闸 → 破坏性动作永远只进审批队列**。默认部署（调度 OFF、`TM_AGENT_ORCHESTRATION_ENABLED=0`、`prune_apply=false`）不自动改任何数据。

### GET /admin/config · PUT /admin/config（v0.20）

运行时配置中心。`GET` 枚举全部已知键（`KNOWN_CONFIG`）的有效值 / 是否被覆盖 / 默认值；`PUT` 单条或批量写覆盖（逐键经 `config_store.set`，热重载广播）。

**脱敏铁律**：敏感键（`config:model:api_keys:*`）`value` 恒 `null`，仅 `configured:bool` 表示是否已配置——真值从不读回。

```bash
# 列全部配置
curl -sS "${ENDPOINT}/admin/config" -H "X-API-KEY: ${API_KEY}" | jq

# 批量写（开梦境后台调度 + 关某工具）
curl -sS -X PUT "${ENDPOINT}/admin/config" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"updates":[
        {"key":"config:dreaming:scheduler_enabled","value":true},
        {"key":"config:tools:global_enabled_map","value":{"snapshot_and_quarantine":false}}
      ]}' | jq
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `GET` → `items[]` | `ConfigItem[]` | `{key, module, type, value, is_override, default, configured, group, label, description}`；`value` 为有效值（override 优先，否则 `default`），敏感键恒 null |
| `GET` → `count` | int | 已知键总数 |
| `PUT` body `updates[]` | `{key, value}[]` | `value=null` 清除该键覆盖回默认；至少 1 条 |
| `PUT` → `results[]` | `{key, ok, rejected_reason}[]` | `ok=false` 时 `rejected_reason` ∈ `unknown_key` / `rejected_base_url_host`（HR-9 主机锁）/ `invalid_value_or_persist_failed`（不回显可能敏感的 value） |
| `PUT` → `applied` / `rejected` | int | 成功 / 失败计数 |

> 治理相关可写键全集（dreaming / tools / agent 共 19 个，含默认值）见 [`governance.md`](./governance.md) §5。改工具开关 / 梦境调度 / agent 步数都走这里，**不旁路** config_store 的校验（known-key allowlist + HR-9 base_url 主机锁 + 类型 coerce + 敏感键加密 write-only）。

### GET /admin/tools · POST /admin/tools/{tool}/invoke（v0.20）

治理工具箱矩阵 + 单工具调用。6 个预设工具 + 三档风险（SAFE / LLM / 破坏性可逆），详见 [`governance.md`](./governance.md) §2。

```bash
# 看工具矩阵（全局开关 + 各容器 resolved/raw 开关）
curl -sS "${ENDPOINT}/admin/tools" -H "X-API-KEY: ${API_KEY}" | jq

# dry-run 预览一次知识聚类压缩（默认 dry_run=true，不改数据）
curl -sS -X POST "${ENDPOINT}/admin/tools/compress_knowledge_cluster/invoke" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"my-project"}' | jq

# 真执行（显式 dry_run=false；LLM 经 rag_engine 网关，附加式不删源）
curl -sS -X POST "${ENDPOINT}/admin/tools/compress_knowledge_cluster/invoke" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"my-project","dry_run":false}' | jq
```

`GET /admin/tools` 响应（`ToolsListResponse`）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `global_enabled_map` | `dict[str,bool]` | 各工具全局开关（默认全 ON） |
| `sandbox_mem_limit` | str | 工具沙箱内存上限（默认 `512m`） |
| `approval_ttl_days` | int | 审批有效期（默认 30 天） |
| `new_tool_default_enabled` | bool | 表外新工具默认开关（默认 false） |
| `tools[]` | `{name, scope, description}[]` | 6 个预设工具静态描述 |
| `containers[]` | `{container, resolved_map, raw_map}[]` | `resolved_map`=容器有效开关（容器覆盖叠加全局）；`raw_map`=容器自身覆盖（无覆盖 = null，完全继承全局） |

`POST /admin/tools/{tool}/invoke` 请求 `ToolInvokeRequest`：`{container?:str, params?:dict, dry_run?:bool=true}`。响应 `ToolInvokeResponse`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `tool` | str | 工具名 |
| `status` | enum | `ok` / `disabled`（开关关）/ `dry_run`（预览）/ `error` / `deferred` / `applied` |
| `container` | str\|null | 作用容器 |
| `result` | dict | 工具产物 / plan；真执行改了记忆主文件时 `result.reindex_required=true` 会触发 best-effort re-embed（`result.reindex_job={job_id,status}`） |
| `applied` | bool | 是否真落地了改动 |
| `notes` | str | 备注 / 指引（如 `pass dry_run=false to execute`） |

**dry_run 语义**：SAFE 工具（`manage_token_quotas` / `analyze_retrieval_latency` 只读；`update_container_routing` 加性写）**总是真执行**；LLM / 破坏性工具默认 `dry_run=true` 只产 plan 预览，显式 `dry_run=false` 才真执行。破坏性 `snapshot_and_quarantine` 经此端点 `dry_run=false` 可直接真执行（运维手动操作）——但在 **agent 循环里它永不自动执行**，只进审批队列（见下）。

**`compress_knowledge_cluster` 响应面（v0.21.0 幂等 4 态，详见 [`governance.md`](./governance.md) §2.2）**：

- `result.action` ∈ `first_card` / `skipped_unchanged` / `consolidated` / `superseded`（真执行）；dry_run 预览的 plan 里则是 `plan.decision` ∈ `first_card` / `skip_unchanged` / `consolidate` / `supersede`。
- **顶层 `status` ≠ action**：skip 路径顶层 `status` 是 **`ok`**（不是 `skipped_unchanged`——后者只在 `result.action`，否则响应校验 500）；建首卡/合并/取代为 `applied`。
- `result.cluster_fingerprint`（簇指纹幂等键）、`result.cluster_group`（supersede 链稳定分组键）、`result.card_id`（当前卡 id）始终带。
- 取代/合并时带 `result.supersedes`（被退役卡 id 列表）+ `result.superseded_count` + `result.superseded_path`（governance 可逆快照路径）；skip 时带 `result.card_id`=既有卡、`reindex_required=false`、不调 LLM。
- dry_run 预览的 plan 额外带 `batch_count` / `estimated_bytes` / `cluster_size` / `source_ids` / `decision` / `superseded_card_ids` / `new_source_count`（不调 LLM 的可执行预览）。

### GET /admin/dreaming/status · POST /admin/dreaming/trigger（v0.20）

梦境子系统（后台/手动记忆整理周期）。详见 [`governance.md`](./governance.md) §3。

```bash
# 状态（全局开关 / 调度配置与实际运行态 / cron / 各容器解析配置 / 最近报告）
curl -sS "${ENDPOINT}/admin/dreaming/status" -H "X-API-KEY: ${API_KEY}" | jq

# 手动触发一次（dry_run 默认 true = 仅产候选报告不删）
curl -sS -X POST "${ENDPOINT}/admin/dreaming/trigger" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"my-project"}' | jq
```

`GET …/status`（`DreamStatusResponse`）：`{global_enabled, scheduler_enabled, scheduler_running, trigger_cron, batch_model, last_report:DreamReport|null, containers:[{container, enabled, cron, model}]}`。

`POST …/trigger` 请求：`{container?:str (null=所有启用容器), dry_run?:bool=true}`。响应 `DreamReport`：`{status('ok'|'skipped_global_disabled'), started_at, finished_at, container_scope, dry_run, excluded_from_rag(恒 true), actions:[{tool, container, summary, candidates, applied}], notes}`。

> **破坏性二次守护**：`dry_run` 默认 true = report-only。即便 `dry_run=false`，真删除**仍**受 `config:dreaming:prune_apply`（默认 false）二次守护——单凭这个请求体永远删不掉数据。总闸 `config:dreaming:global_enabled` 关时返回 `status:"skipped_global_disabled"` 不执行。

### POST /admin/agent/{name}/invoke · GET /admin/agent/runs（v0.20）

治理编排 Agent（网关 LLM tool-use 循环）。**opt-in，默认 OFF**：`TM_AGENT_ORCHESTRATION_ENABLED=0` 时 invoke 返回 `status:"disabled"` 不入队。详见 [`governance.md`](./governance.md) §4。

```bash
# 入队一次 agent run（dry_run 默认 true = 全程 plan，不落地）
curl -sS -X POST "${ENDPOINT}/admin/agent/dream-orchestrator/invoke" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"my-project","goal":"consolidate duplicate decision memories"}' | jq

# 允许可逆工具落地（须同时 dry_run=false 且 allow_apply=true）
curl -sS -X POST "${ENDPOINT}/admin/agent/dream-orchestrator/invoke" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"my-project","goal":"...","dry_run":false,"allow_apply":true}' | jq

# 历史 run（newest first）
curl -sS "${ENDPOINT}/admin/agent/runs?limit=20" -H "X-API-KEY: ${API_KEY}" | jq
```

`POST …/invoke` 请求 `AgentInvokeRequest`：`{container?:str (null=全局), goal?:str, params?:dict, dry_run?:bool=true, allow_apply?:bool=false}`。响应 `AgentInvokeResponse`：`{agent_name, run_id, job_id?, status('enqueued'|'disabled'|'error'), container, dry_run, allow_apply, notes}`。

> **apply 双闸**：服务端 `effective_allow_apply = allow_apply AND NOT dry_run`——任一闸留安全默认，整个 run 停在 plan。可逆工具仅在双闸全开时自动落地；**破坏性工具（`snapshot_and_quarantine`）任何情况只进审批队列**，由人在 approve 端点执行。

`GET …/runs?limit=50` → `{runs:[{run_id, agent_name, container, created_at, status, dry_run, proposals, job_id}]}`（读隔离 governance store；不可用时降级空表）。

### GET /admin/agent/approvals · approve / reject（v0.20）

破坏性提案的人工审批队列。**`/approve` 是整个 server 唯一一处破坏性治理工具以 `dry_run=False` 真执行的地方**——人（鉴权背后）是唯一执行器，无人值守循环从不自己跑破坏性工具。

```bash
# 列 pending 审批（默认 status=pending；过期的被存储层隐藏）
curl -sS "${ENDPOINT}/admin/agent/approvals?status=pending&limit=50" \
  -H "X-API-KEY: ${API_KEY}" | jq

# 批准并真执行（记录的工具 + 记录的 params，dry_run=False）
curl -sS -X POST "${ENDPOINT}/admin/agent/approvals/42/approve" \
  -H "X-API-KEY: ${API_KEY}" | jq

# 拒绝（不执行）
curl -sS -X POST "${ENDPOINT}/admin/agent/approvals/42/reject" \
  -H "X-API-KEY: ${API_KEY}" | jq
```

| 端点 | 响应 | 说明 |
|---|---|---|
| `GET /admin/agent/approvals?status=&limit=` | `{approvals:[{id, run_id, agent_name, container, tool, status, created_at}]}` | 按 status 过滤（默认 pending）；TTL（`config:tools:approval_ttl_days`，默认 30 天）过期 pending 被隐藏 |
| `POST …/{id}/approve` | `ToolInvokeResponse` | pending→approved 后以记录的 tool+params 真执行（`dry_run=False`）；reindex 时复用 re-embed 路径；**404** = 不存在/已决/已过期 |
| `POST …/{id}/reject` | `AgentApprovalInfo`（decided row） | 仅置 rejected，不执行；**404** = 不存在/已决/已过期 |

> approve/reject 会记审计者标签（session api-key hash 前缀，否则 client IP）。`approve` 的执行结果与直接 `/admin/tools/{tool}/invoke` `dry_run=false` 同形（`ToolInvokeResponse`），破坏性工具的可逆语义（快照 + 隔离、零硬删）不变。

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
