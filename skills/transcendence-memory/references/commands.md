# Commands Reference

每条 HTTP 端点 / `/tm` 命令的 **curl 调用 · 入参 · 响应 schema** 速查矩阵。

本文件是 [`SKILL.md`](../SKILL.md) 「Built-in Commands」表与 [`api-reference.md`](./api-reference.md) 之间的桥梁：
SKILL.md 给"什么时候用哪条命令"，本文件给"每条命令到底发什么、收回什么"，
api-reference.md 给"完整字段类型 / 别名 / 取全文"细节。三者保持一致。

- 认证：业务端点统一 `X-API-KEY: <key>` 或 `Authorization: Bearer <key>`；`/health` 与 `/ingest-memory/contract` 无需认证。
- 变量约定：`${ENDPOINT}` / `${API_KEY}` / `${CONTAINER}` 均读自 `~/.transcendence-memory/config.toml`。
- **首选用 `scripts/tm-search.sh`**（`search` / `query` / `status`）发检索 / 探活：它读 config、zsh-glob-safe 地构造 JSON、带 WAF 兼容 UA、代理自动回退、惰性吸收冷启动；下方裸 `curl` 是其底层调用的文档与逃生通道。
- **HTTP 200 ≠ 成功**：跨容器与冷启动场景必须解析 body（见 [troubleshooting.md 冷启动段](./troubleshooting.md#冷启动服务端索引未热起http-200-但-body-未就绪)）。
- 自定义客户端务必带非默认 `User-Agent`，否则 Cloudflare 1010 拦截（见 [troubleshooting.md 403 段](./troubleshooting.md#403-forbiddencloudflare--waf-拦截--error-code-1010)）。
- 响应字段别名对照（`text` vs `content`/`chunk`，`score` vs `vectorScore`/`rerankScore`）见 [api-reference.md「响应字段别名对照表」](./api-reference.md#响应字段别名对照表坑-d)。

## 目录 (Table of Contents)

- [命令 ⇄ 端点速查表](#命令--端点速查表)
- [连接与状态](#连接与状态)
  - [`/tm connect` → 写 config](#tm-connect--写-config)
  - [`/tm status` → GET /health + POST /search 探针](#tm-status--get-health--post-search-探针)
- [检索（轻量路径 · LanceDB）](#检索轻量路径--lancedb)
  - [`/tm search` → POST /search](#tm-search--post-search)
  - [跨容器 / union 选项矩阵](#跨容器--union-选项矩阵)
  - [POST /search 响应 schema](#post-search-响应-schema)
- [写入与索引（轻量路径）](#写入与索引轻量路径)
  - [`/tm remember` → POST /ingest-memory/objects](#tm-remember--post-ingest-memoryobjects)
  - [`/tm update` → PUT /containers/{c}/memories/{id}](#tm-update--put-containerscmemoriesid)
  - [DELETE /containers/{c}/memories/{id}](#delete-containerscmemoriesid)
  - [`/tm embed` → POST /embed](#tm-embed--post-embed)
  - [`/tm batch` → batch-ingest.py](#tm-batch--batch-ingestpy)
  - [GET /ingest-memory/contract](#get-ingest-memorycontract)
- [多模态路径（RAG-Anything 知识图谱）](#多模态路径rag-anything-知识图谱)
  - [`/tm query` → POST /query](#tm-query--post-query)
  - [`/tm upload` → POST /documents/upload](#tm-upload--post-documentsupload)
  - [POST /documents/text](#post-documentstext)
- [容器管理](#容器管理)
  - [`/tm containers` → GET /containers](#tm-containers--get-containers)
  - [DELETE /containers/{name}](#delete-containersname)
  - [GET /export-connection-token](#get-export-connection-token)
- [任务队列](#任务队列)
  - [`/tm jobs` → 本地账本 + GET /jobs/{id}](#tm-jobs--本地账本--get-jobsid)
  - [GET /jobs（列表）](#get-jobs列表)
  - [DELETE /jobs/{id}](#delete-jobsid)
- [运维 / 管理端点](#运维--管理端点)
- [本地命令（不发 HTTP）](#本地命令不发-http)
  - [`/tm auto`](#tm-auto)
  - [`/tm upgrade`](#tm-upgrade)
- [Quick Reference（单页 curl 矩阵）](#quick-reference单页-curl-矩阵)

---

## 命令 ⇄ 端点速查表

| `/tm` 命令 | HTTP 方法 + 路径 | 认证 | 响应主字段 | 备注 |
|---|---|---|---|---|
| `connect <token>` | 写本地 config + GET /health | 验证用 | `status` | 不发业务请求，仅 health 验证 |
| `status` | GET /health + POST /search(topk=1) | search 需 | `runtime_ready` / `degraded` | **200 必须解析 body**，见下 |
| `search <q>` | POST /search | 是 | `results[]`（非 `hits`） | 每条命中 `text` + `score` |
| `search --match <p> <q>` | POST /search（`container_pattern`） | 是 | `results[]` + `per_container_status` | 跨容器 |
| `search --all <q>` | POST /search（`container_pattern:""`） | 是 | `results[]` + `per_container_status` | 全容器 |
| `remember <text>` | POST /ingest-memory/objects | 是 | `accepted` / `index_hint` | `auto_embed:true` 自动入队 |
| `update <id> <text>` | PUT /containers/{c}/memories/{id} | 是 | `status:"updated"` | 之后需 `/tm embed` |
| `embed` | POST /embed | 是 | `pid`(=job_id) / `status` | 默认 `wait:false` 入队立返；index 重建**可轮询** |
| `query <q>` | POST /query | 是 | `answer` + `sources[]` | LLM 综合答案 |
| `upload <file>` | POST /documents/upload | 是 | `pid`/`job_id` | KG 构建异步入队，**勿轮询** |
| `containers [pat]` | GET /containers | 是 | `containers[]` / `count` | 模糊过滤 |
| `batch <file.jsonl>` | scripts/batch-ingest.py → POST /ingest-memory/objects | 是 | 脚本汇总 | 内置 WAF UA / 413 缩批 |
| `jobs` | 本地账本 + GET /jobs/{id} | 是 | `running` / `exit_code` | **无顶级 `status` 字段** |
| `auto on/off/status` | 本地标记文件 | 否 | 文本 | 不发 HTTP |
| `upgrade` | `git pull`（本地） | 否 | 文本 | 不发 HTTP |

> 完整端点（含 `/documents/text`、`/ingest-structured`、`/admin/*`、`/jobs` 列表与取消）见 [api-reference.md](./api-reference.md)。

---

## 连接与状态

### `/tm connect` → 写 config

把连接令牌（base64 of `{endpoint, api_key, container}`）解码后写入 `~/.transcendence-memory/config.toml`，再用 `/health` 验证。

```bash
TOKEN="$1"
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
curl -sS "$ENDPOINT/health"   # 验证连接
```

`connect --manual`：向用户索取 `endpoint` / `api_key` / `container`，写同样的 config。完整首次配置流程见 [`setup.md`](./setup.md)，模板见 `templates/config.toml.template`。

| 字段 | 来源 | 说明 |
|---|---|---|
| `endpoint` | token / 手填 | 服务基址，无尾部 `/` |
| `api_key` | token / 手填 | `X-API-KEY` 用值 |
| `container` | token / 手填 | 默认检索/写入容器 |

### `/tm status` → GET /health + POST /search 探针

首选 `bash scripts/tm-search.sh status`（一行健康探针，已自动解析 body / 吸收冷启动）。手动等价：

```bash
CONFIG="$HOME/.transcendence-memory/config.toml"
ENDPOINT=$(grep '^endpoint' "$CONFIG" | sed 's/.*= *"//' | sed 's/".*//')
API_KEY=$(grep '^api_key' "$CONFIG" | sed 's/.*= *"//' | sed 's/".*//')
CONTAINER=$(grep '^container' "$CONFIG" | sed 's/.*= *"//' | sed 's/".*//')

# 1) 健康检查（公开，无需认证）
curl -sS "$ENDPOINT/health" | python3 -m json.tool

# 2) 鉴权 + 检索探针（topk=1）
curl -sS -X POST "$ENDPOINT/search" \
  -H "X-API-KEY: $API_KEY" -H "Content-Type: application/json" \
  -d "{\"container\":\"$CONTAINER\",\"query\":\"test\",\"topk\":1}"
```

**判定（HTTP 200 不代表就绪 — 必须解析 body）**：

| 信号 | 来源字段 | 含义 |
|---|---|---|
| 服务活着 | `/health` `status == "ok"` | 进程在 |
| 能力就绪 | `/health` `runtime_ready.search` / `.query` | `false` = 该能力未就绪 |
| 准入开放 | `/health` `accepting_ingest` | `false` 时退避，勿继续 ingest |
| **冷启动未就绪** | `/search` body `per_container_status` 含 `timeout`/`not_initialized`，或 `degraded:true` | 服务端索引在冷加载，**不是连接失败** |

> 冷启动判定与处理（首选 `scripts/tm-search.sh` 已惰性吸收；手动排查才短间隔重发几次。`curl --retry` 抓不到——它只对 transport/5xx 重试，对带坏 body 的 200 无能为力）见 [troubleshooting.md 冷启动段](./troubleshooting.md#冷启动服务端索引未热起http-200-但-body-未就绪)。
> `/health` 公开字段语义见 [api-reference.md GET /health](./api-reference.md#get-health)。

---

## 检索（轻量路径 · LanceDB）

### `/tm search` → POST /search

首选 `bash scripts/tm-search.sh search <query>`。底层 HTTP 调用：

```bash
curl -sS -X POST "${ENDPOINT}/search" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","query":"搜索内容","topk":5}'
```

| 参数 | 类型 | 必需 | 默认 | 说明 |
|---|---|---|---|---|
| `query` | string | 是 | — | 搜索文本 |
| `topk` | int | 否 | 5 | 全局返回上限（跨容器=合并后总数）。**取全文/不截断时调大** |
| `container` | string | 否 | `home` | 单容器（向后兼容字段） |
| `containers` | string[] | 否 | — | 显式多容器，优先级最高 |
| `container_pattern` | string | 否 | — | 模糊匹配容器名 |
| `pattern_mode` | string | 否 | `substring` | `substring` / `prefix` / `glob` |
| `union` | bool\|null | 否 | `null` | 单 container 是否自动并 sibling `_openai`；`null`=随 server 默认 |
| `per_container_timeout_s` | float | 否 | 12.0 | 单容器子查询超时（0.5–30，v0.11.1+；v0.19.0 起 server 默认放宽到 30.0 降低冷启动误降级） |
| `score_threshold` | float\|null | 否 | `null` | **v0.19.0**：请求级 score-gate（L2 距离上界，越小越相关）。`null`=随 server `profiles.yaml` 的 `similarity_threshold`（默认 None=关）；`≤0`=显式关。被拦命中数计入响应 `blocked_low_score` |
| `timeout_s` | int | 否 | 600 | subprocess 整体超时 |

完整入参定义见 [api-reference.md POST /search](./api-reference.md#post-search)。

> **zsh 提示**：裸 `-d '{...}'` 在 zsh 下可能触发 `zsh: no matches found`（glob 展开）。手写 curl 时务必单引号包住 body，或用 `jq -n ... | curl --data @-`；`tm-search.sh` 已规避此坑。

### 跨容器 / union 选项矩阵

| 目标 | curl body 片段 | `/tm` 形式 |
|---|---|---|
| 单容器 | `{"container":"X","query":"q","topk":5}` | `/tm search q` |
| 单容器强制不 union | `{"container":"X","query":"q","topk":5,"union":false}` | （脚本 `tm-search.sh` 默认即 `union:false`） |
| 单容器强制 union（sibling 须存在） | `{"container":"X","query":"q","topk":5,"union":true}` | — |
| 模糊多容器 | `{"container_pattern":"my-proj","query":"q","topk":5}` | `/tm search --match my-proj q` |
| 全部容器 | `{"container_pattern":"","query":"q","topk":10}` | `/tm search --all q` |

> 跨容器响应里每条 hit 会带 `container` 字段，并附 `containers` / `per_container_status` 用于诊断。`topk` 是合并后的全局上限，不是每容器独立。
> **为什么默认 `union:false`**：未初始化的 sibling（如 `X_openai` 存在却未 embed）被 union 拉进来会令整体 `degraded:true` 并污染 `per_container_status`——主容器结果其实正常，只是被拖累。止血：本次显式传 `"union":false` 跳过 sibling，或先给 sibling 跑一次 `/embed` 再 union。详 [troubleshooting.md union 拖累段](./troubleshooting.md#degradedtrue--union-把未初始化-sibling-拉进来拖累整体)。
> v0.11.0+ 若 server `profiles.yaml` 设 `union_search_default: true`，单 container 查询会自动并 sibling `_openai`（gemini-3072 + openai-1024 双轨召回），按 `(taskId, chunkId)` 去重合并；响应多出 `union_applied` / `degraded` / `per_container_status`。显式 `containers` / `container_pattern` 会跳过自动 union。

### POST /search 响应 schema

顶层命中数组字段名是 **`results`**（不是 `hits`）。每条命中：

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
      "metadata": {},
      "lineStart": null,
      "lineEnd": null
    }
  ],
  "containers": ["my-container", "my-container_openai"],
  "per_container_status": {"my-container": "ok", "my-container_openai": "ok"},
  "degraded": false,
  "is_degraded": false,
  "fallback_source": null,
  "union_applied": false,
  "rerank_applied": false,
  "citations": [
    {"chunkId": "<taskId>#client-ingest#<idx>", "sourcePath": "...", "section": "client_ingest", "score": 0.56, "container": "my-container", "lineStart": null, "lineEnd": null}
  ],
  "blocked_low_score": 0,
  "fallback_rendered": null
}
```

| 字段 | 含义 |
|---|---|
| `results[].text` | 命中正文（主字段；别名 `content`/`chunk` 见 api-reference） |
| `results[].score` | 相关性分（rerank 后可能呈 `vectorScore`/`rerankScore`，见 api-reference） |
| `results[].taskId` + `chunkId` | 客户端 `id` **不回流** `results[].id`；按这两者或 `text` 匹配 |
| `results[].lineStart` / `lineEnd` | **v0.19.0**：命中 chunk 在源文件中的 1-based 起止行号；**P4 前 ingest 的老 chunk 恒 `null`**（无 schema 迁移、无需 re-embed），新 chunk 才有值。可据此构造"文件 X 第 42–67 行"式源定位 |
| `citations` | **v0.19.0**：结构化溯源数组（投影 `chunkId`/`sourcePath`/`section`/`score`/`container`/`lineStart`/`lineEnd`）。`/search` 默认**开**（`citation_enabled=true`）；老客户端忽略不影响 |
| `blocked_low_score` | **v0.19.0**：被 score-gate 阈值拦掉的命中数。**默认 0**（score-gate 默认关）；若 `>0` 且 `results` 空 = 阈值过严**不是**库空（见 troubleshooting） |
| `fallback_rendered` | **v0.19.0**：opt-in 兜底模板渲染串。**默认 `null`**（未配模板时恒 null，行为与 P4 前逐字节一致）；非 null 是"无命中/全降级"的结构化提示，**非高置信检索结果** |
| `is_degraded` / `fallback_source` | 降级语义别名（`is_degraded`=`degraded` 同值双写；`fallback_source="partial_containers"` 表部分容器成功）。判定见解析约定 |
| `per_container_status` | 跨容器每容器状态：`ok` / `timeout` / `not_initialized` / `error` |
| `degraded` | 任一目标容器超时/失败/未初始化 → `true`（结果不完整） |
| `union_applied` | 自动并入 sibling `_openai` 时 `true` |

**关键解析约定**：

- 每条命中**没有顶级 `id` 字段**。`/ingest-memory/objects` 时给的 `id` 不会原样回流到 `results[].id`；下游按 `taskId + chunkId` 或 `text` 内容自行匹配。
- 同一条 ingest 的长文本**会被切成多个 chunks**（`chunkId` 末尾 `#<idx>` 是切片序号）；search 可能返回多条同 `taskId` 的不同 chunk。
- `title` 字段在多数情况下为空 `""`，即使 ingest 时显式给了；以 `text` 头几行为准。
- **行号溯源（v0.19.0）**：`results[].lineStart`/`lineEnd` 与 `citations[]` 给出命中 chunk 的源文件行范围——**仅 P4 后 ingest 的新 chunk 有值，老 chunk 恒 `null`**（向后兼容、零 re-embed）。渲染源定位链接前先判 `lineStart != null`。
- **score-gate 拦截 ≠ 库空（v0.19.0）**：`/search` 默认不开 score-gate（`blocked_low_score` 恒 0）。若服务端配了 `similarity_threshold` 或你传了请求级 `score_threshold`，低于阈值的命中被丢弃并计入 `blocked_low_score`；看到 `results:[]` 同时 `blocked_low_score>0` 是阈值过严，**别误判为"没有这条记忆"**。
- **`/search` vs `/query` 字段名不同**：`/search` 命中在 `results[]`、正文字段是 **`text`**；`/query` 的检索证据在 **`sources[]`**、正文字段是 **`content`**（不是 `text`）。跨两个端点解析时不要假设同名。
- **开启 reranker 后分数字段会变**：未 rerank 时只有单一 `score`（向量相似度）；rerank 后可能改为 / 附加 `vectorScore`（召回阶段）+ `rerankScore`（重排后，排序以它为准）。读分数优先认 `rerankScore`（若存在），否则回落 `score`；不要硬编码只读 `score`。
- **结果可能被 `topk` / `top_k` 截断，长文本只回中间 chunk**：要拿全文按 `taskId` 拉该来源全部 chunk，或调大 `topk` 重查——单条命中不等于该记忆全文。
- 详细字段定义与别名 / 取全文方法见 [api-reference.md「响应字段别名对照表」](./api-reference.md#响应字段别名对照表坑-d) 与 [§POST /search](./api-reference.md#post-search) / [§POST /query](./api-reference.md#post-query)。

---

## 写入与索引（轻量路径）

### `/tm remember` → POST /ingest-memory/objects

首选 wrapper 脚本（jq 构 JSON 杜绝手写转义 422、内置 secret 脱敏、代理自动回退）：

```bash
bash <skill-path>/scripts/tm-remember.sh "记忆正文" \
  [--title t] [--tags a,b] [--container c] [--id mem-x] [--no-embed] [--json]
# 成功输出一行: stored id=... container=... embed=queued|skipped
```

底层 HTTP 调用（仅 wrapper 不可用时手写；注意 JSON 转义是历史 422 高发根因）：

```bash
MEM_ID="mem-$(date +%s)"
curl -sS -X POST "${ENDPOINT}/ingest-memory/objects" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","objects":[{"id":"'"$MEM_ID"'","text":"记忆内容","tags":[]}],"auto_embed":true}'
```

| 对象字段 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 客户端 id（**不会**回流到 search `results[].id`） |
| `text` | string | 是 | 记忆正文 |
| `title` / `source` | string | 否 | 元信息（`title` 常在 search 回空） |
| `tags` | string[] | 否 | 标签 |
| `metadata` | object | 否 | 自定义元数据（避免不支持类型，否则 422） |

响应：`{"container":"...","accepted":1,"stored_path":"...","index_hint":"Embed job queued; ..."}`。
`auto_embed:true` 时服务端自动入队 embed（同 container 合并），无需再单独 `/tm embed`。

### `/tm update` → PUT /containers/{c}/memories/{id}

```bash
MEM_ID="$1"; shift; NEW_TEXT="$*"
curl -sS -X PUT "${ENDPOINT}/containers/${CONTAINER}/memories/${MEM_ID}" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "$(python3 -c 'import json,sys; print(json.dumps({"text": sys.argv[1]}))' "${NEW_TEXT}")"
# 之后必须 /tm embed 刷新索引（PUT/DELETE 不自动重建索引）
```

入参 `text` / `tags` / `metadata` 均可选。响应 `{"status":"updated","id":"mem-001","container":"..."}`。

### DELETE /containers/{c}/memories/{id}

```bash
curl -sS -X DELETE "${ENDPOINT}/containers/${CONTAINER}/memories/mem-001" \
  -H "X-API-KEY: ${API_KEY}"
# 响应 {"status":"deleted","id":"mem-001","container":"..."}；之后 /tm embed
```

### `/tm embed` → POST /embed

```bash
curl -sS -X POST "${ENDPOINT}/embed" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}"}'
```

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `container` | string | — | 目标容器（必需） |
| `wait` | bool | `false` | `false`=入队立返 `job_id`；`true`=阻塞轮询直到完成/超时 |
| `timeout_s` | int | 600 | `wait=true` 的轮询超时 |
| `background` | bool | — | 旧字段，语义并入 `wait` |

入队响应（`wait=false`）：`{"command":[...],"code":0,"pid":42,"status":"enqueued","note":"..."}`。
**`pid` 现在是 queue job_id**（非 OS PID），用 `GET /jobs/42` 查进度。队列内置指数退避自动重试。Server v0.5.10+ 单 worker 以宿主友好节奏排空，同 container 重复 `/embed` 自动合并为一个 pending job。

> **`/embed` 是 index 重建，可轮询**——它**不**受 SKILL.md `## AI Behavior — async ingestion silent-mode` 的「禁轮询」约束（那条只针对 `/documents/*` / `/tm upload` 的 KG 构建任务）。`remember` / `update` / `delete` 之后跑一次 `/embed`。

### `/tm batch` → batch-ingest.py

```bash
python3 <skill-path>/scripts/batch-ingest.py \
  "${ENDPOINT}" "${API_KEY}" "${CONTAINER}" "$1" [options]
```

| Option | 默认 | 用途 |
|---|---|---|
| `--max-bytes N` | 512000 | 单批最大字节数 |
| `--batch-size N` | 50 | 单批最大条数 |
| `--redact` | off | 入库前脱敏（API key / token / 私钥）——bare-skill 安装无 hooks 时的脱敏路径 |
| `--probe` | off | 先探 `/ingest-memory/contract` 确认 schema |
| `--resume` | off | 跳过已成功行（断点续传） |
| `--failed-log F` | `<input>.failed.jsonl` | 失败对象输出 |
| `--test-waf` | — | 自检 UA 是否被 WAF 拦（不入库） |

脚本内置 WAF 兼容 UA、413 自动缩批、失败重试日志。自写客户端务必带非默认 `User-Agent: transcendence-memory-batch/0.2`（或任意非默认值），否则 Cloudflare 1010 拦截（见 [troubleshooting.md 403 段](./troubleshooting.md#403-forbiddencloudflare--waf-拦截--error-code-1010)）。

### GET /ingest-memory/contract

无需认证。批量导入前探测字段约束，避免 422。

```bash
curl -sS "${ENDPOINT}/ingest-memory/contract"
```

---

## 多模态路径（RAG-Anything 知识图谱）

> 与轻量路径**互不相通**：`/documents/*` 入知识图谱（服务 `/query`），`/ingest-memory/objects` 入 LanceDB（服务 `/search`）。需要两边都召回须双写（见 [best-practices.md](./best-practices.md) §1.2）。

### `/tm query` → POST /query

首选 `bash scripts/tm-search.sh query <q>`。底层 HTTP 调用：

```bash
curl -sS -X POST "${ENDPOINT}/query" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"query":"你的问题","container":"${CONTAINER}","mode":"hybrid","top_k":60}'
```

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `query` | string | — | 查询文本（必需） |
| `container` | string | — | 目标容器（必需） |
| `mode` | string | `hybrid` | 检索模式 |
| `top_k` | int | 60 | 检索候选数 |
| `rerank` | bool | route 默认 | 临时开/关重排（字段名必须 `rerank`，非 `enable_rerank`） |
| `reranker_model` | string | route 默认 | 临时换 reranker profile |

响应：`{"answer":"...","sources":[{"chunk_id":"...","score":0.85,"text":"..."}]}`。
注意 `/query` 的来源数组叫 **`sources`**（每条 `chunk_id`/`score`/`text`），与 `/search` 的 `results` 不同名；rerank 后分数语义见 [api-reference.md 别名表](./api-reference.md#响应字段别名对照表坑-d)。

> **前提**：`/query` 只看 `/documents/text` / `/documents/upload` 入库的内容（`/tm remember` 的 LanceDB-only 记忆不参与综合）。**异步**：刚 ingest 完立即 `/query` 返空属正常，KG 尚未建好——见 SKILL.md async silent-mode，**勿轮询** KG 构建任务。

### `/tm upload` → POST /documents/upload

```bash
RESP=$(curl -sS -X POST "${ENDPOINT}/documents/upload" \
  -H "X-API-KEY: ${API_KEY}" -H "User-Agent: transcendence-memory-skill/0.4" \
  -F "file=@$1" -F "container=${CONTAINER}")
echo "$RESP"
echo "$RESP" | python3 "<skill-path>/scripts/job-ledger.py" add \
  --endpoint "${ENDPOINT}" --container "${CONTAINER}" --kind upload --source "/tm upload"
```

响应：`{"status":"enqueued","container":"...","filename":"...","pid":12345,"job_id":12345}`。
**异步入队 → 记账本 → 结束回合，禁止轮询**（见 [SKILL.md async silent-mode](../SKILL.md#ai-behavior--async-ingestion-silent-mode-v041-strict)）。
支持 PDF / PNG / JPG / Markdown。`POST /documents/file` 是 alias。

### POST /documents/text

```bash
curl -sS -X POST "${ENDPOINT}/documents/text" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -H "User-Agent: transcendence-memory-skill/0.4" \
  -d '{"container":"${CONTAINER}","text":"长文本...","description":"可选描述"}'
```

响应：`{"status":"enqueued","container":"...","pid":12345,"job_id":12345}`。同样异步、勿轮询。

---

## 容器管理

### `/tm containers` → GET /containers

```bash
curl -sS "${ENDPOINT}/containers" -H "X-API-KEY: ${API_KEY}"                          # 全部
curl -sS "${ENDPOINT}/containers?pattern=my-project" -H "X-API-KEY: ${API_KEY}"       # 子串
curl -sS "${ENDPOINT}/containers?pattern=my-project&mode=prefix" -H "X-API-KEY: ${API_KEY}"
curl -sS "${ENDPOINT}/containers?pattern=my-project_*&mode=glob" -H "X-API-KEY: ${API_KEY}"
```

| 查询参数 | 默认 | 说明 |
|---|---|---|
| `pattern` | — | 匹配串（≤64，禁 `/` 与控制字符） |
| `mode` | `substring` | `substring` / `prefix` / `glob` |

响应：`{"containers":[{"name":"...","objects":N,"indexed":true,"last_modified":"..."}],"count":N}`。

### DELETE /containers/{name}

```bash
curl -sS -X DELETE "${ENDPOINT}/containers/${CONTAINER}" -H "X-API-KEY: ${API_KEY}"
# 不可逆。响应 {"status":"deleted","container":"..."}
```

### GET /export-connection-token

```bash
curl -sS "${ENDPOINT}/export-connection-token?container=${CONTAINER}" -H "X-API-KEY: ${API_KEY}"
# 响应 {"token":"eyJlbmRwb2ludCI6..."}（base64，给 /tm connect 用）
```

---

## 任务队列

### `/tm jobs` → 本地账本 + GET /jobs/{id}

```bash
python3 "<skill-path>/scripts/job-ledger.py" list
```

读 `~/.transcendence-memory/pending-jobs.jsonl`，逐条 re-check `GET /jobs/{id}`。
单条状态：

```bash
curl -sS "${ENDPOINT}/jobs/12345" -H "X-API-KEY: ${API_KEY}"
# {"pid":12345,"running":true|false,"exit_code":null|0|<非0>,"message":"status=... attempts=n/max"}
```

| 字段 | 说明 |
|---|---|
| `pid` | queue job_id（非 OS PID） |
| `running` | pending/running 时 true |
| `exit_code` | done=0；其余 null |
| `message` | `status=<s> attempts=<n>/<max>`，失败附 last_error |

> **无顶级 `status` 字段** — 判定用 `running` / `exit_code`，不要读 `.status`。日常很少用：成功静默，失败由 SessionStart hook 浮现。

### GET /jobs（列表）

```bash
curl -sS "${ENDPOINT}/jobs?status=pending&limit=20" -H "X-API-KEY: ${API_KEY}"
```

参数 `status`（`pending`/`running`/`done`/`failed`/`cancelled`）、`container`（精确）、`limit`（1–500，默认 50）。
响应含 `jobs` / `stats`（按状态计数）/ `worker_running`。

### DELETE /jobs/{id}

```bash
curl -sS -X DELETE "${ENDPOINT}/jobs/12345" -H "X-API-KEY: ${API_KEY}"
# 仅能取消 pending；running/done → 409
```

---

## 运维 / 管理端点

需鉴权，日常检索不用。详见 [api-reference.md 管理端点](./api-reference.md#管理端点) 与 [api-reference.md Multi-Model 端点](./api-reference.md#multi-model-端点v070)。

| 端点 | 用途 |
|---|---|
| `GET /admin/system-health` | 数值化诊断（阈值 / 队列计数 / 容器清单 / 资源快照） |
| `GET /admin/profiles` | 列 embedding / reranker profile + route 表（secret 自动 redact） |
| `POST /admin/probe-embedding?profile=<n>` | 单 profile 探活（latency + 实测 dim） |
| `GET /index-status` · `GET /containers/{name}/index-status` | **v0.18** 容器索引状态机：`state` + 对象计数 + embed backlog 摘要 |
| `POST /containers/aliases` · `GET /containers/aliases` · `DELETE /containers/aliases/{alias}` | **v0.18** 容器名 alias 路由 upsert / 列出 / 删除（admin） |
| `POST /embed-multimodal`（multipart） | **v0.18** 单媒体文件 → Gemini 原生多模态 embedding → 一条 LanceDB 行（容器须路由到 `gemini_native` profile） |
| `GET /admin/usage/{summary,endpoints,containers,timeseries}` · `POST /admin/usage/cleanup` | **v0.18** 请求用量分析（调用数 / 延迟 / 按容器 / 时间桶）+ 保留期清理 |
| `GET /admin/ui` · `POST /admin/ui/{login,logout}` · `GET /admin/ui/me` | **v0.18** Cookie-session 管理面板 SPA（浏览器向，agent 少直调） |

### v0.18 运维端点详解

**`GET /index-status` / `GET /containers/{name}/index-status`** — 容器索引状态机，**union 前判断 sibling 是否真就绪**的权威来源（避免把未 embed 的 sibling 拉进来拖累整体）：

```bash
curl -sS "${ENDPOINT}/index-status" -H "X-API-KEY: ${API_KEY}" | jq          # 全容器批量
curl -sS "${ENDPOINT}/containers/${CONTAINER}/index-status" -H "X-API-KEY: ${API_KEY}" | jq
```

单容器响应：`{"container":"...","state":"ready|indexing|stale|...","total_objects":N,"embedded_objects":M,"backlog_active":0,"backlog_counts":{...},"dead_count":0,"job_running":false,"next_retry_at":null,"last_error_class":null,"last_embed_ok_at":"...","last_embed_attempt_at":"..."}`。批量端点包成 `{"containers":[...],"count":N}`。入参是 alias 时解析到 canonical；从未 embed 过的容器 `embedded_objects:0` → state 落 `stale`/`unknown`。

**`POST /embed-multimodal`** — multipart 表单，把单个媒体文件直接算成统一向量空间的一条向量行：

```bash
curl -sS -X POST "${ENDPOINT}/embed-multimodal" \
  -H "X-API-KEY: ${API_KEY}" \
  -F "container=${CONTAINER}" -F "file=@./photo.jpg" \
  -F "caption=可选文字描述" -F "doc_id=可选稳定 id"
```

表单字段：`container`（必需）/ `file`（必需，媒体二进制）/ `caption`（可选，给出则与媒体联合 embed 并作为可读文本）/ `doc_id`（可选稳定 id）。缺 caption 时服务端经 VLM best-effort 自动生成（失败不阻塞落库，回退文件名）。要求目标容器路由到 `gemini_native` provider；空文件 400、超限 413、不支持的 mime 415。落库后 `/search` 即可向量检回。

**`POST /containers/aliases`**（upsert）— body `{"alias":"短名","canonical":"真实容器","reason":"","status":"active|deprecated|removed","notes":""}`，返回写入行；`GET /containers/aliases` → `{"aliases":[...],"count":N}`；`DELETE /containers/aliases/{alias}` → `{"deleted":true,"alias":"..."}`（不存在 404）。删除只摘路由记录，**不**触碰 canonical 物理数据。

**`GET /admin/usage/*`** — query 参数：`summary?window=24h`；`endpoints?window=7d&sort=calls&limit=20`；`containers?window=7d&sort=calls&limit=50`；`timeseries?path=/search&window=7d&bucket=1h`（`path` 必需）。`POST /admin/usage/cleanup` body `{"retention_days":N}` 删超期记录。

**`GET /admin/ui` + `POST /admin/ui/login|logout` + `GET /admin/ui/me`** — Cookie-session 登录（HttpOnly + SameSite=Strict；POST 需 `X-Requested-With: XMLHttpRequest`）包住既有 api-key 网关，外加 SPA 兜底服务前端 bundle。浏览器面向，agent 一般用上面的 JSON 端点而非走 UI。

---

## 本地命令（不发 HTTP）

### `/tm auto`

启用 / 禁用 / 查看「git commit 自动存记忆」。自动存本身在 PostToolUse / Stop hooks 里跑——**仅 plugin 安装生效**，bare-skill 安装无 hooks（见 SKILL.md hooks 说明）。

```bash
# on  — 建标记文件，hooks 自动存 commit 摘要
mkdir -p ~/.transcendence-memory && touch ~/.transcendence-memory/auto-memory.enabled
echo "Automatic memory enabled. Git commit summaries will be stored automatically."

# off — 删标记文件
rm -f ~/.transcendence-memory/auto-memory.enabled
echo "Automatic memory disabled."

# status — 查当前状态 + 当前 endpoint/container
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

### `/tm upgrade`

自动定位安装位置（plugin cache / `~/.claude/skills/` / Cursor / git clone）并 `git pull --ff-only`。非 git 安装（`npx skills add` tarball）则打印重装命令。升级后重启 AI CLI 生效。

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
  echo "  • Claude Code plugin:  /plugin update transcendence-memory@transcendence-memory"
  echo "  • npx skills:          npx skills add https://github.com/leekkk2/transcendence-memory --skill transcendence-memory --force"
fi
```

> 升级刷新 `SKILL.md` / `references/` / `scripts/` / 仓库自带 plugin hooks（SessionStart + UserPromptSubmit + PostToolUse + Stop）。
> **若升级失败（`fatal: Not possible to fast-forward`）**：本地有 cherry-pick 副本 / divergence。处理：`git tag backup/pre-upgrade-$(date +%Y%m%d) HEAD && git reset --hard origin/main`。完全可回退（`git reset --hard backup/pre-upgrade-<date>`）。

---

## Quick Reference（单页 curl 矩阵）

需要单页速览所有端点时用。变量读自 `~/.transcendence-memory/config.toml`；认证 `X-API-KEY: <key>` 或 `Authorization: Bearer <key>`。

### 文本记忆（轻量路径）

```bash
# 检索（首选 bash scripts/tm-search.sh search <q>）
curl -sS -X POST "${ENDPOINT}/search" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","query":"what you want to search for","topk":5}'

# 存一条记忆
curl -sS -X POST "${ENDPOINT}/ingest-memory/objects" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","objects":[{"id":"mem-001","text":"content to store","tags":["tag1"]}],"auto_embed":true}'

# 重建索引（remember 用了 auto_embed 则无需；update/delete 后需要）
curl -sS -X POST "${ENDPOINT}/embed" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}"}'

# 更新一条记忆（之后跑 /embed）
curl -sS -X PUT "${ENDPOINT}/containers/${CONTAINER}/memories/mem-001" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"text":"updated content","tags":["new-tag"]}'

# 删除一条记忆（之后跑 /embed）
curl -sS -X DELETE "${ENDPOINT}/containers/${CONTAINER}/memories/mem-001" \
  -H "X-API-KEY: ${API_KEY}"
```

### 多模态 RAG（RAG-Anything pipeline）

```bash
# 入库长文本到知识图谱。异步（server v0.15.0+）——记 job_id 后勿轮询。
curl -sS -X POST "${ENDPOINT}/documents/text" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -H "User-Agent: transcendence-memory-skill/0.4" \
  -d '{"container":"${CONTAINER}","text":"long text to ingest...","description":"optional"}'

# 上传文件（PDF / image / Markdown）——同样异步，同 job_id 语义。
curl -sS -X POST "${ENDPOINT}/documents/upload" \
  -H "X-API-KEY: ${API_KEY}" -H "User-Agent: transcendence-memory-skill/0.4" \
  -F "file=@/path/to/document.pdf" -F "container=${CONTAINER}"

# RAG 查询（返回 LLM 综合答案；首选 bash scripts/tm-search.sh query <q>）
curl -sS -X POST "${ENDPOINT}/query" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"query":"your question","container":"${CONTAINER}","mode":"hybrid","top_k":60}'
```

### 容器管理 + 健康

```bash
curl -sS "${ENDPOINT}/containers" -H "X-API-KEY: ${API_KEY}"                     # 列全部
curl -sS "${ENDPOINT}/containers?pattern=my-project" -H "X-API-KEY: ${API_KEY}" # 模糊过滤
curl -sS -X DELETE "${ENDPOINT}/containers/${CONTAINER}" -H "X-API-KEY: ${API_KEY}"  # 删容器
curl -sS "${ENDPOINT}/health"                                                   # 健康检查（200≠就绪，解析 body）
```
