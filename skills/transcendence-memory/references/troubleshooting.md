# 排障 / Troubleshooting

## 目录 (Table of Contents)

- [快速诊断](#快速诊断)
- [通用问题](#通用问题)
  - [怎么查容器列表](#怎么查容器列表)
  - [配置文件不存在](#配置文件不存在)
  - [连接被拒绝 / 超时](#连接被拒绝--超时)
  - [401 Unauthorized](#401-unauthorized)
  - [403 Forbidden（Cloudflare / WAF 拦截 — `error code: 1010`）](#403-forbiddencloudflare--waf-拦截--error-code-1010)
  - [Hook 报错 `xargs: unterminated quote`（auto-memory 后台静默失败）](#hook-报错-xargs-unterminated-quoteauto-memory-后台静默失败)
  - [413 Request Entity Too Large](#413-request-entity-too-large)
  - [422 Unprocessable Entity](#422-unprocessable-entity)
  - [5xx 错误](#5xx-错误)
- [轻量路径问题](#轻量路径问题)
  - [search 返回 200 但 body 有错误](#search-返回-200-但-body-有错误)
  - [冷启动：服务端索引未热起（HTTP 200 但 body 未就绪）](#冷启动服务端索引未热起http-200-但-body-未就绪)
  - [`degraded:true` — union 把未初始化 sibling 拉进来拖累整体](#degradedtrue--union-把未初始化-sibling-拉进来拖累整体)
  - [v0.18 优雅降级：部分成功不再整体失败（`is_degraded` / `fallback_source`）](#v018-优雅降级部分成功不再整体失败is_degraded--fallback_source)
  - [v0.18：未 embed 的 `_openai` sibling 被软跳过（`not_initialized`）](#v018未-embed-的-_openai-sibling-被软跳过not_initialized)
  - [search 无结果](#search-无结果)
  - [embed 任务失败 / 卡住（上游 embedding 限速）](#embed-任务失败--卡住上游-embedding-限速)
  - [update/delete 后变更未生效](#updatedelete-后变更未生效)
- [多模态路径问题](#多模态路径问题)
  - [文档上传失败](#文档上传失败)
  - [`/documents/text` / `/documents/upload` 返回 524 / 超时](#documentstext--documentsupload-返回-524--超时)
  - [query 返回空答案](#query-返回空答案)
  - [`/search` 有结果但 `/query` 返回"无信息"](#search-有结果但-query-返回无信息)
  - [异步任务查询](#异步任务查询)
  - [VLM 相关问题](#vlm-相关问题)
- [批量入库问题](#批量入库问题)
  - [批量导入推荐流程](#批量导入推荐流程)
  - [入库后搜索不到](#入库后搜索不到)
  - [脱敏不完整](#脱敏不完整)
- [重置配置](#重置配置)
- [Multi-Embedding / dim mismatch（v0.7.0+）](#multi-embedding--dim-mismatchv070)
  - ["query dim X doesn't match the column vector dim Y" lance error](#query-dim-x-doesnt-match-the-column-vector-dim-y-lance-error)
  - [`/admin/probe-embedding` 返回 `ok: false`](#adminprobe-embedding-返回-ok-false)
  - [行级查询 `metadata.embedding_model` 永远拿不到](#行级查询-metadataembedding_model-永远拿不到)
  - [Per-request `embedding_model` override 不生效](#per-request-embedding_model-override-不生效)
  - [Reranker 配置了但永远不生效](#reranker-配置了但永远不生效)
  - [客户端代码用 `enable_rerank` 字段没反应](#客户端代码用-enable_rerank-字段没反应)
  - [Reranker upstream 返回 400 `model_price_error` / `model_not_found`](#reranker-upstream-返回-400-model_price_error--model_not_found)
  - [`/query` 报 `AssertionError: Embedding dim mismatch, expected: X, but loaded: Y`](#query-报-assertionerror-embedding-dim-mismatch-expected-x-but-loaded-y)
  - [服务拒绝启动：`FATAL: EMBEDDING_DIM=X disagrees with LanceDB schemas`（v0.18 启动闸）](#服务拒绝启动fatal-embedding_dimx-disagrees-with-lancedb-schemasv018-启动闸)
- [治理 / 梦境（v0.20）](#治理--梦境v020)
  - [agent run 卡在 pending 审批不前进](#agent-run-卡在-pending-审批不前进)
  - [compress_knowledge_cluster 大簇分批 / 曾经 400](#compress_knowledge_cluster-大簇分批--曾经-400)

## 快速诊断

```bash
# 读取本地配置
ENDPOINT=$(grep 'endpoint' ~/.transcendence-memory/config.toml | head -1 | cut -d'"' -f2)
API_KEY=$(grep 'api_key' ~/.transcendence-memory/config.toml | head -1 | cut -d'"' -f2)

# 检查配置文件是否存在
ls -la ~/.transcendence-memory/config.toml

# 检查连接
curl -sS -i "${ENDPOINT}/health"
```

## 通用问题

### 怎么查容器列表

公开 `/health` **不再**包含容器清单（防止匿名访问者枚举租户/项目名）。需要时用：

```bash
curl -sS "${ENDPOINT}/admin/system-health" -H "X-API-KEY: ${API_KEY}" | jq .available_containers
# 或更轻量的专用端点：
curl -sS "${ENDPOINT}/containers" -H "X-API-KEY: ${API_KEY}"
```

`available_containers: []` 是正常的 — 容器在首次写入数据时按需创建。新部署的 server 没有任何容器。

### 配置文件不存在

尚未完成首次配置。参考 `references/setup.md`。

### 连接被拒绝 / 超时

```bash
# 检查 endpoint 是否可达
curl -sS -o /dev/null -w "%{http_code}" "${ENDPOINT}/health"
```

可能原因：
- **连接超时既可能是代理劫持、也可能是直连被墙——两条路都要试**（高频，最易误判）：连接超时**不等于**「代理在捣乱」。本机若设了 `HTTP_PROXY` / `HTTPS_PROXY` / `ALL_PROXY=socks5://...`，存在两种相反情形：
  - **代理坏 / 直连可用**：代理本身挂了，绕过它直连才通 → 该加 `--noproxy`。
  - **代理是唯一活路（GFW 区高频）**：自建域名走 **Cloudflare**，本机在墙内**直连 Cloudflare edge 不稳**（实测 ~12s connect 超时、两个 edge IP 都失败），而经本机 localhost 代理反而 ~1–1.4s 稳定可达 → 此时**盲目 `--noproxy` 会把唯一能用的路掐断**，越改越坏。

  `scripts/tm-search.sh` 已自动两路 fallback（**默认尊重环境代理**，失败再自动直连重试一次），日常无需手动判路。手搓 `curl` 自检时也两路都试：
  ```bash
  # 路 1：尊重环境代理（GFW 区 Cloudflare-fronted endpoint 常是可靠路径）
  curl -sS -o /dev/null -w "%{http_code}" "${ENDPOINT}/health"
  # 路 2：直连（代理坏 / 直连可用的反向场景；给更宽的 connect-timeout）
  curl -sS --noproxy '*' --connect-timeout 15 -o /dev/null -w "%{http_code}" "${ENDPOINT}/health"
  ```
  判定：哪条通用哪条；两条都超时再往下查 endpoint / server / 网络。安全说明：经本机 localhost 代理走 HTTPS 是 CONNECT 隧道，TLS 终结在 Cloudflare，代理只见 `host:443`，看不到 `X-API-KEY` / body，无凭证泄漏。
- endpoint 地址错误
- server 未启动
- 防火墙 / 网络不通
- 反向代理配置问题

→ 两路都试过仍不通，联系后端管理员确认服务状态。

### 401 Unauthorized

API key 不匹配：

```bash
# 确认本地 key
grep 'api_key' ~/.transcendence-memory/config.toml

# 直接测试
curl -sS -i "${ENDPOINT}/search" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"test","query":"hello","topk":1}'
```

→ 向后端管理员确认正确的 API key。

### 403 Forbidden（Cloudflare / WAF 拦截 — `error code: 1010`）

> **2026-04-29 实测确认**：触发条件**与 payload 大小、内容、是否含 markdown / 代码块完全无关**，**只取决于 `User-Agent` 头**。Cloudflare 的 `Browser Integrity Check` 把"Python-urllib/x.x"、空 UA、已知爬虫 UA 列入黑名单，整请求秒拒（响应 0.5–1s 内回 403）。`curl` 默认 UA `curl/8.x` **不被拦**，所以同样 5KB payload 用 curl 通过、用 urllib 失败的对比常被误读为"WAF 拦大 payload"——**实际不是**。

#### 自检：你撞上的是 WAF 还是别的？

```bash
# 1) 不带 UA 的 urllib —— 必 1010
python3 -c "
import urllib.request, urllib.error
try:
    urllib.request.urlopen('${ENDPOINT}/health', timeout=5).read()
    print('OK')
except urllib.error.HTTPError as e:
    print(e.code, e.read()[:80])
"
# 期望：403 b'error code: 1010'

# 2) 带 WAF 兼容 UA 的 urllib —— 必 200
python3 -c "
import urllib.request, json
req = urllib.request.Request('${ENDPOINT}/health',
    headers={'User-Agent':'transcendence-memory-batch/0.2'})
print(urllib.request.urlopen(req, timeout=5).read()[:80])
"

# 3) 一行 batch-ingest 自检（v0.3+）
python3 <skill-path>/scripts/batch-ingest.py "${ENDPOINT}" "${API_KEY}" "${CONTAINER}" --test-waf
```

若 1) 失败 + 2) 成功，证明就是 WAF UA 拦截；否则继续往下排查。

#### 解决（自写客户端必读 — 不限于 batch-ingest）

任何**绕过 `batch-ingest.py` 直接调用 `/ingest-memory/objects`、`/search`、`/embed` 等**的脚本（Python urllib / requests / Node fetch / Go net/http 默认 client / Rust reqwest 默认 client）都需要**显式设 User-Agent**：

```python
# Python urllib
headers = {
    "Content-Type": "application/json",
    "X-API-KEY": api_key,
    "User-Agent": "transcendence-memory-batch/0.2",  # ← 关键
    "Accept": "application/json, text/plain, */*",
}

# Python requests
session = requests.Session()
session.headers.update({
    "User-Agent": "transcendence-memory-batch/0.2",
    "Accept": "application/json, text/plain, */*",
})
```

```javascript
// Node fetch
fetch(url, {
  headers: {
    "User-Agent": "transcendence-memory-batch/0.2",
    "X-API-KEY": apiKey,
  }
})
```

或者一律走 `batch-ingest.py` —— 它已内置 WAF 兼容请求头，并提供 `--probe` / `--resume` / `--redact`。

> **管理员侧改法（可选）**：若希望接口对 Python 默认 UA 也放行，在 Cloudflare 把该 endpoint 的 Browser Integrity Check 关闭，或加 WAF Custom Rule `(http.host eq "your.host" and starts_with(http.request.uri.path, "/ingest-memory/")) → Skip Browser Integrity Check`。属于服务端运维，本 skill 不涉及。

### Hook 报错 `xargs: unterminated quote`（auto-memory 后台静默失败）

> ⚠️ **SUPERSEDED 2026-04-30 → v0.3.0 已内置修复，无需手动操作**
> 本节仅作历史参考。v0.3.0+ 插件通过 `hooks/common.sh` 共享库统一处理命令 trim，不再使用 `xargs`，此问题已不复存在。如果你用 `/plugin install transcendence-memory` 安装的是最新版，可跳过本节。

**现象**：在执行 `git commit` / `python3 -c "..."` / `bash -c "..."` 等含**嵌套引号**的命令后，agent 提示：

```
Failed with non-blocking status code: xargs: unterminated quote
Failed with non-blocking status code: xargs: unterminated quote
```

是 non-blocking 错误，**不影响主流程**，但 auto-memory hook 已静默退出，那次 commit 不会被自动记录。

**根因**：用户机上的 **`~/.claude/hooks/transcendence-memory/on-post-tool-use.sh`** 第 39 行（旧版本）使用 `xargs` 做空白 trim：

```bash
first_cmd=$(echo "$cmd" | head -1 | sed 's/&&.*//' | sed 's/;.*//' | xargs)
#                                                                    ^^^^^
#  xargs 会按 shell-quoted 规则解析输入，遇到未配对引号就抛 unterminated quote
```

`sed` 截掉 `&&` / `;` 后半段时不解释引号语法，前半段经常残留孤立引号；或者 `python3 -c "import json; print(json.dumps({\"x\":\"y\"}))"` 本身的转义双引号在 `xargs` 看来不配对。

**复现**：

```bash
echo 'echo "hello && world' | head -1 | sed 's/&&.*//' | xargs
# → xargs: unterminated quote (exit 1)

echo 'python3 -c "import json; print(json.dumps({\"a\":\"b\"}))"' | sed 's/&&.*//' | xargs
# → xargs: unterminated quote (exit 1)
```

**修复（手动改文件 — 推荐）**：把那一行替换为不解释 shell 引号的 awk trim：

```bash
first_cmd=$(echo "$cmd" | head -1 | sed 's/&&.*//' | sed 's/;.*//' \
  | awk '{$1=$1; print}')
```

或一行 sed 自动 patch：

```bash
sed -i.bak "s/| xargs)$/| awk '{\$1=\$1; print}')/" \
  ~/.claude/hooks/transcendence-memory/on-post-tool-use.sh
```

**为什么不用 `xargs -0`**：本场景输入并非 null-delimited，`xargs -0` 仍按规则要求每条记录无 NUL；最干净的做法就是不用 xargs。`awk '{$1=$1; print}'` 是 POSIX awk 的标准 trim 习语，**不解释**任何引号、反斜杠、特殊字符。

**验证**：

```bash
# 修复后再跑一次，预期 exit 0、无报错输出
echo 'python3 -c "import json; print(json.dumps({\"a\":\"b\"}))"' \
  | sed 's/&&.*//' | sed 's/;.*//' | awk '{$1=$1; print}'
echo "exit=$?"  # 期望 0
```

> 仓库自带的 `hooks/post-commit-memory`（plugin 标准格式）**不含此 bug**。本节针对的是用户独立部署到 `~/.claude/hooks/transcendence-memory/` 的全局 hook 套件（不通过 `/plugin install` 而是手动写入）。

### 413 Request Entity Too Large

单次请求体超出网关/反向代理限制（通常来自 nginx）。

**解决**：
- 使用 `batch-ingest.py --max-bytes 500000` 限制单批字节数
- 脚本会在遇到 413 时自动对半缩批重试
- 对超长文件（>100KB），建议先截断或拆分再入库
- 若反复出现，联系管理员调大 nginx `client_max_body_size`

### 422 Unprocessable Entity

请求体格式不符合 `/ingest-memory/objects` 的 schema 要求。

**排查**：
1. 先探测接口 contract：
   ```bash
   curl -sS "${ENDPOINT}/ingest-memory/contract"
   ```
2. 用最小 payload 测试：
   ```bash
   curl -sS -X POST "${ENDPOINT}/ingest-memory/objects" \
     -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
     -d '{"container":"${CONTAINER}","objects":[{"id":"test","text":"hello"}]}'
   ```
3. 逐步加回 `tags`、`metadata` 等字段定位不兼容字段
4. 使用 `batch-ingest.py --probe` 在批量导入前自动探测

常见原因：
- `metadata` 字段包含不支持的类型
- `tags` 非字符串数组
- `text` 为空
- 字段名拼写错误

### 5xx 错误

服务端问题，不是客户端问题。联系后端管理员，或参考 `transcendence-memory-server` 的排障文档。

## 轻量路径问题

### search 返回 200 但 body 有错误

这不算成功。可能原因：
- container 未初始化 → 先执行 `/embed`
- server 内部错误 → 检查 server 日志
- **冷启动未就绪**（见下条）→ 不是错误，重发即可

### 冷启动：服务端索引未热起（HTTP 200 但 body 未就绪）

**现象**：`/search` 返回 **HTTP 200**，但 body 里：
- `per_container_status` 出现 `timeout` 或 `not_initialized`
- `initialized: false`
- `degraded: true`

**根因**：**不是连接失败、不是 bug**。服务端 subprocess 冷加载（py + lancedb + lightrag import + table load + embed call）实测 5–10s，首个请求常在索引热起前先返回，命中为空或部分超时。

**首选 — 用 `scripts/tm-search.sh`**：它已**惰性吸收**冷启动（首跑触发热加载、内部等就绪后再返回），日常检索直接用它即可，无需手动重试：
```bash
bash <skill-path>/scripts/tm-search.sh "<query>"
```

**手动 curl 排查时才需要短间隔重发几次**（等服务端热起）：
```bash
for i in 1 2 3; do
  curl -sS --noproxy '*' -X POST "${ENDPOINT}/search" \
    -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
    -d "{\"container\":\"${CONTAINER}\",\"query\":\"<q>\",\"topk\":5}"
  sleep 3
done
```

> ⚠ **不要依赖 `curl --retry`**：`--retry` 只对连接错误 / 指定的 5xx 重试，对 **HTTP 200 + 坏 body**（冷启动正是这种）**完全不会重试**。必须解析 body 看 `per_container_status` / `degraded` / `runtime_ready` 后再自行重发。

### `degraded:true` — union 把未初始化 sibling 拉进来拖累整体

**现象**：单容器查询本应只查一个容器，结果 `degraded:true`，`per_container_status` 里冒出一个 `<container>_openai`（或其它 sibling）= `not_initialized` / `timeout`。

**根因**：server 端 `union_search_default:true`（或请求带 `union:true`）会自动把 sibling `_openai` 镜像并进来一起查；当该 sibling **尚未初始化 / 未 embed** 时，它直接令整体 `degraded:true` 并污染 `per_container_status`，但主容器结果其实是好的。

**规避（任选）**：
- **首选 `scripts/tm-search.sh`** —— 默认带 `union:false`，不会把未就绪 sibling 拉进来。
- 手动 curl 强制单容器（即使 server 默认开 union）：
  ```bash
  curl -sS --noproxy '*' -X POST "${ENDPOINT}/search" \
    -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
    -d "{\"container\":\"${CONTAINER}\",\"query\":\"<q>\",\"topk\":5,\"union\":false}"
  ```
- 确实要双轨召回 → 先给 sibling 跑一次 `/embed` 让它初始化，之后 union 才不会 degraded。

> 判定要点：`degraded:true` 时先看 `per_container_status` 是哪个容器坏的——如果坏的是 `*_openai` sibling 而主容器 `ok`，主结果可信，按上面 `union:false` 止血即可，不必当成数据丢失。

### v0.18 优雅降级：部分成功不再整体失败（`is_degraded` / `fallback_source`）

**v0.18 行为变更**：union 多容器检索时，**只要任一容器（尤其主容器）出结果**，`/search` 就返回 **HTTP 200** 且照常给 `results`，body 标记：

- `is_degraded: true`（= 旧 `degraded`，**同值双写**——Agent 读新名、前端读旧名，任选其一即可）
- `fallback_source: "partial_containers"`（部分容器成功、部分失败时）
- `per_container_status` 仍列出每容器 `ok` / `timeout` / `not_initialized` / `error: <msg>`
- 部分成功时 `message` 为 `null`（**不再**弹红色错误文案）

**只有全部容器都失败**（无任一结果）才回 `status: "error"` + 人话错误 `message`（仍是 HTTP 200，body 标志为准——转 503 是 Phase 2 才考虑的事）。

**对调用方的含义**：

| 你看到 | 判定 | 动作 |
|---|---|---|
| `status:"ok"` + `is_degraded:false` | 完整成功 | 正常用 |
| `status:"ok"` + `is_degraded:true` + `results` 非空 | 部分降级但有结果 | **照常渲染 `results`**；可选提示哪些容器没就绪（看 `per_container_status`） |
| `status:"error"` | 全部容器失败 | 这才是真失败，按 `message` 排查 |

> 旧代码若硬判 `status==="error"` 之外都算失败、或只认 `degraded` 字段——升 v0.18 后建议改读 `is_degraded`（与 `degraded` 同值，未来 `degraded` 可能淡出）。**别把部分降级当数据丢失**。

### v0.18：未 embed 的 `_openai` sibling 被软跳过（`not_initialized`）

**v0.18 行为变更**：union 解析阶段，server 会探测 sibling 是否真有 `chunks` 表；**从未 embed 过的 sibling 直接被软跳过**，不再算进 `per_container_status`、不再把整次检索拖成 `degraded`/`error`。这根治了「主容器好好的、却因为一个空 `*_openai` 镜像导致整条搜索失败」的老问题。

- **现象（修复后）**：单容器查询自动 union 时，若 sibling 未初始化 → 响应里 `containers` 只剩主容器、`union_applied:false`、**没有** `not_initialized` 噪音、`results` 来自主容器。
- **想恢复双轨**：给 sibling 跑一次 `/embed`（让它建出 `chunks` 表）→ 下次 union 自动把它带回来。
- **确认 sibling 是否就绪**：`GET /containers/<sibling>/index-status` 看 `state`（非 `ready` 就是还没 embed 好）。

> 聚合处仍保留 `not_initialized` 分支作防御（万一 sibling 解析后又被清空也不拖垮主流程）。所以你偶尔仍可能在 `per_container_status` 看到它——但只要主容器 `ok` 就照常返回。

### v0.19.0：`/search` 空结果但 `blocked_low_score>0` —— score-gate 拦截非库空

**现象**：`/search` 回 `status:"ok"`、`results:[]`，但 body 里 `blocked_low_score` 是个 `>0` 的数；容器明明有数据。

**根因**：v0.19.0 score-gate。服务端 `profiles.yaml` 配了 `similarity_threshold`（或 Dashboard 热重载了 `config:rag:similarity_threshold`），或请求里传了 `score_threshold`——命中分（L2 距离，**越小越相关**）高于阈值的全被丢弃，`blocked_low_score` = 被拦条数。

**与冷启动 / 库空的区分**：

| 你看到 | 判定 |
|---|---|
| `blocked_low_score>0` + `results:[]` | score-gate 拦截（**有命中但都被判太弱**） |
| `per_container_status` 含 `not_initialized`/`timeout` + `initialized:false` | 冷启动（见冷启动段） |
| `blocked_low_score:0` + `results:[]` + 容器 `index-status` ready | 真的没相关记忆 |

**规避**：放宽或去掉请求级 `score_threshold`（传 `null` 或 `≤0` 关）重查；或运维在 Dashboard 下调 `similarity_threshold`。**默认部署不开 score-gate**（阈值 None），此字段恒 `0`，老行为逐字节不变。

### v0.19.0：行号溯源 `lineStart`/`lineEnd` 何时有值

**现象**：想用 `results[].lineStart`/`lineEnd` 或 `citations[].lineStart`/`lineEnd` 给命中加"源文件第 X–Y 行"定位，却拿到 `null`。

**根因（非 bug）**：P4（行号溯源，v0.19.0）后 ingest 的新 chunk 才在 `metadata` 里带 `lineStart`/`lineEnd`；**P4 之前 ingest 的老 chunk 没有这两个键 → 投影为 `null`**。这是刻意的向后兼容——**无 LanceDB schema 迁移、无需 re-embed**，老库照常工作。

**要点**：
- 行号是 server 端 ingest 时自动按 chunk 切分计算并写入 `metadata` JSON，**客户端 ingest 无需传任何新字段**。
- 渲染源定位链接前先判 `lineStart != null`；老记忆无行号属预期，不要当错误。
- `citations[]` 是 `/search` 默认开（`citation_enabled=true`）的结构化溯源投影；`/query` 默认关（`query_citation_enabled=false`，恒 `[]`）。

### search 无结果

```bash
# 先重建索引
curl -sS -X POST "${ENDPOINT}/embed" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","background":false,"wait":true}'

# 再搜索
curl -sS -X POST "${ENDPOINT}/search" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","query":"test","topk":5}'
```

新 container 或新写入的记忆需要先 `/embed` 才能被检索到。

### embed 任务失败 / 卡住（上游 embedding 限速）

**现象**：刚 `/tm remember` 后 `/tm search` 召回不到；`/jobs/{pid}` 显示 `exit_code` 非 0；server 日志含 `embedding upstream 500` 或 `429`。

**根因**：embedding 上游网关（newapi 类反代）短时限速。**server v0.5.2+ 已内置 6 次指数退避 + Retry-After 重试**（≈1.5/3/6/12/24/48s，总计 ≈90s），多数限速会被自动消化。

**诊断**：

1. 查 embed 任务最终态：`curl -sS "${ENDPOINT}/jobs/${PID}" -H "X-API-KEY: ${API_KEY}"`
   - `running:false, exit_code:0` → 成功
   - `running:false, exit_code:非0` → 重试已耗尽，上游持续故障
   - `running:true` → 仍在跑

2. 直接探上游：
   ```bash
   curl -sS -o /dev/null -w "%{http_code}\n" -X POST "$EMBEDDING_BASE_URL/embeddings" \
     -H "Authorization: Bearer $EMBEDDING_API_KEY" -H "Content-Type: application/json" \
     -d '{"model":"<embed-model>","input":"ping"}'
   ```
   持续 5xx → 等 5–15 分钟或换 key；200 → 已恢复，重发 `/tm embed`。

3. 重新触发：
   ```bash
   curl -sS -X POST "${ENDPOINT}/embed" -H "X-API-KEY: ${API_KEY}" \
     -H "Content-Type: application/json" \
     -d "{\"container\":\"${CONTAINER}\",\"background\":true}"
   ```

**管理员调参**（限速窗口 > 90s 时）：`EMBEDDING_MAX_RETRIES` / `EMBEDDING_RETRY_MAX_DELAY` / `EMBEDDING_RETRY_BASE_DELAY`。

**避免**：不要前台循环手动重试 `/tm embed`（会与后台重试踩同一限速窗口）；不要因 `search` 暂空就重写 `remember`（数据已落库）。
### update/delete 后变更未生效

**关键**：更新或删除记忆后，必须调用 `/embed` 刷新索引，否则 `/search` 仍返回旧数据。

```bash
# 更新/删除操作后，执行索引重建
curl -sS -X POST "${ENDPOINT}/embed" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","background":false,"wait":true}'
```

## 多模态路径问题

### 文档上传失败

```bash
# 检查文件是否存在且格式正确
file /path/to/document.pdf

# 检查上传
curl -sS -i -X POST "${ENDPOINT}/documents/upload" \
  -H "X-API-KEY: ${API_KEY}" \
  -F "file=@/path/to/document.pdf" \
  -F "container=${CONTAINER}"
```

可能原因：
- 文件格式不支持（仅支持 PDF、PNG/JPG 图片、Markdown）
- 文件过大（检查 server 端限制）
- multipart/form-data 格式错误
- VLM 未配置（server 端问题）→ 联系管理员

### `/documents/text` / `/documents/upload` 返回 524 / 超时

**现象**：调用 `/documents/text` 卡很久后返回 HTTP 524（Cloudflare 网关超时）或连接超时。

**根因**：server 为 **< v0.15.0 旧 build**。这些版本**同步建图**——实体抽取 + 关系推断 + LLM 索引在 HTTP 请求内完成，大文档耗时超过 Cloudflare 的网关上限即 524。

**v0.15.0+ 行为**：`/documents/text` 与 `/documents/upload` 改为**纯异步**——入队即返回 job 标识（整数 `pid`），知识图谱由后台 worker 构建，请求**不会**再 524。

**处理**：

```bash
# 1) 524 后数据可能已入队 —— 查队列里是否有对应 job 在跑
curl -sS "${ENDPOINT}/jobs?status=running" -H "X-API-KEY: ${API_KEY}"
# skill 侧等价命令：
/tm jobs
```

- 若队列里有对应 container 的 running job → 数据已入队，等后台建完即可，无需重试。
- 根治：升级 server 到 v0.15.0+。
- 旧版临时缓解：把大文档拆成多个小段分批 `/documents/text`，单段控制在数 KB 内。

### query 返回空答案

```bash
# 确认知识图谱中有数据
curl -sS -X POST "${ENDPOINT}/query" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"query":"列出所有已入库的内容","container":"${CONTAINER}","mode":"hybrid","top_k":60}'
```

可能原因：
- **最常见误用** — 只通过 `/ingest-memory/objects`（轻量路径）写入数据。该端点仅服务 `/search`,**不会自动进 RAG-Anything 知识图谱**。`/query` 必须通过 `/documents/text` 或 `/documents/upload` 显式入图。详见 `references/best-practices.md` 双路径决策树
- 后台建图尚未完成 — `/documents/text` / `/documents/upload` 入队即返回,知识图谱由后台 worker 异步构建（数十秒至数分钟）,建完前 `/query` 召回不到属正常。无需等待轮询,后续会话自动可召回;用 `/tm jobs` 查 job 进度,失败由 SessionStart 静默提示
- 查询与入库内容语义不相关 → 尝试更具体的关键词（实体名 / 库名 / 文件名）。本次实战观察到过宽泛的问题（如"推荐什么方案?"）召回率明显低于具体问题（如"OTA 安装步骤"）
- LLM 未配置（server 端问题）→ 联系管理员

### `/search` 有结果但 `/query` 返回"无信息"

**根因**：双路径架构下,内容只入了 LanceDB 向量索引,没入 RAG-Anything 知识图谱。

**修复**：把同一份内容也通过 `/documents/text` 入一次（推荐合并成一份 Markdown 长文本）：

```bash
DOC_TEXT=$(python3 -c "import json; print(json.dumps(open('/path/to/doc.md').read()))")
curl -sS -X POST "${ENDPOINT}/documents/text" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container\":\"${CONTAINER}\",\"text\":${DOC_TEXT},\"description\":\"概要\"}"
# 入队即返回 job 标识；后台异步建图，建完后 /query 自动可召回，无需等待。
```

详见 `references/best-practices.md` 的"跨路径双写"。

### 异步任务查询

大文件上传或 `/embed?background=true` 通常异步处理：

```bash
# 上传/embed 时记录返回的 pid
# {"pid": 12345, "status": "started", ...}

# 查询任务状态
curl -sS "${ENDPOINT}/jobs/12345" -H "X-API-KEY: ${API_KEY}"
```

**响应字段实测**：

```json
{"pid": 12345, "running": true|false, "exit_code": null|0|<非0>, "message": "..."}
```

- `running: true` → 仍在处理
- `running: false, exit_code: 0` → 处理完成,可以 query/search
- `running: false, exit_code: <非0>` → 处理失败,联系管理员看 server 日志

> 旧版文档中提到的 `status: running|completed|failed` 与 `progress` 字段不准确,**以 `running` 字段为判定基准**。

正确轮询模板：

```bash
until ! curl -sS "${ENDPOINT}/jobs/${PID}" -H "X-API-KEY: ${API_KEY}" \
  | python3 -c "import json,sys; sys.exit(0 if json.load(sys.stdin).get('running') else 1)"; do
  sleep 5
done
```

### VLM 相关问题

VLM（视觉语言模型）用于处理图片和 PDF 中的视觉内容。如果文档上传后 `/query` 无法回答图片中的内容：

- VLM 是 server 端配置（默认 qwen3-vl-plus），skill 端无法直接排查
- 联系后端管理员确认 VLM 模型是否正常工作
- 纯文本内容不依赖 VLM，如果文本查询正常但图片查询异常，大概率是 VLM 问题

## 批量入库问题

### 批量导入推荐流程

大规模入库前建议按此顺序执行，减少失败率：

1. `curl -sS "${ENDPOINT}/health"` — 确认服务可用
2. `curl -sS "${ENDPOINT}/ingest-memory/contract"` — 确认接口 schema
3. 用 1-3 条对象做 dry-run — 确认格式正确
4. 正式批量导入，建议加 `--probe --redact --resume`
5. 导入完成后统一 `/embed`
6. `/search` 验证

### 入库后搜索不到

- 确认已执行 `/embed` 刷新索引
- embed 大容器可能需要数分钟，使用 `background:true` + `/jobs/{pid}` 监控

### 脱敏不完整

`--redact` 覆盖常见模式（OpenAI/GitHub/AWS/Google/Slack/Telegram token、PEM 私钥、通用 key=value）。对于非标准敏感信息，建议在入库前自行预处理。

## 重置配置

如需重新配置：

```bash
rm -rf ~/.transcendence-memory
```

然后重新按 `references/setup.md` 操作。

## Multi-Embedding / dim mismatch（v0.7.0+）

### "query dim X doesn't match the column vector dim Y" lance error

**症状**：`/search` 或 `/query` 返回 `code: 1`，stderr 含
`lance error: Invalid user input: query dim(3072) doesn't match the column vector vector dim(1024)`。

**根因**（按概率排序）：
1. **container 名 vs route 不匹配**：第一次写入用了 default 3072，后来想换 1024；或反之
2. **server v0.7.0–v0.10.1 老版本 bug**：subprocess 缺 `CONTAINER` env → 退化到 default route。
   - v0.10.1 修了**异步** JobWorker 子进程路径（影响 `/ingest-memory` 等队列驱动端点）
   - v0.10.2 才补全**同步** `task_rag_server.run()` 路径（影响 `/search` `/embed` `/build-manifest` 等同步端点）
   - 完整修复需服务端 **v0.10.2+**；只升 v0.10.1 时 multi-route 仍半瘫（同步端点继续走 default route）
3. **per-request `embedding_model` 与 container 实际 dim 错配**：override 了一个不同 dim 的 profile

**判定**：
```bash
# 看 server 路由当前 container 走哪个 profile
curl -sS -H "X-API-KEY: ${KEY}" "${ENDPOINT}/admin/profiles" | jq '.routes, .default_route'

# 探活该 profile 实际 dim
curl -sS -X POST -H "X-API-KEY: ${KEY}" "${ENDPOINT}/admin/probe-embedding?profile=<name>"
# {"ok": true, "dim": 1024}  # 与表 dim 必须一致
```

**修复**：
- 不要试图换 dim 复用同名 container（dim 锁死铁律，见 best-practices §6.3）
- 真要换 dim：用 server `scripts/migrate_embeddings.py`（in-place 替换 + 旧表自动备份为 chunks_old_<ts>）
- 想双轨并存：新建一个 `<container>_openai` clone（用 clone 工具或重新 ingest）

### `/admin/probe-embedding` 返回 `ok: false`

| error message 关键字 | 含义 | 修复 |
|---|---|---|
| `embedding upstream 503` / `429` | 上游 quota / rate limit | 等 5 分钟 retry；或配 fallback 链 |
| `EmbeddingProfile ... not found` | profiles.yaml 未声明该 profile | 检查 yaml 拼写 + reload |
| `breaker_open: True` | per-profile circuit breaker 跳开 | `POST /admin/probe-embedding?profile=X` 探活成功即重置 |

### 行级查询 `metadata.embedding_model` 永远拿不到

**症状**：审计脚本读 `json.loads(row['metadata'])['embedding_model']` 返回 None / KeyError。

**根因**：v0.7.0+ chunks 表把 embedding 归属设计为**顶级 LanceDB 列**（`embedding_model` / `embedding_dim` / `embedding_profile`），不在业务 `metadata` JSON 内。`metadata` 是 client ingest 时给的 dict，不会被 ingest pipeline / clone 工具修改。

**正确取法**：
```python
df = t.to_pandas()
df[['chunkId', 'embedding_model', 'embedding_dim', 'embedding_profile']].head()
# 或
df['embedding_model'].value_counts()
```

详见 `references/OPERATIONS.md` "行级 embedding 归属查询" 段。

### Per-request `embedding_model` override 不生效

- 必须 server v0.7.0+。检查 `/health` `accepting_ingest: true` + `/admin/profiles` 能列出 routes
- override 名必须存在于 `/admin/profiles.embeddings[].name`
- override 的 dim 必须与 container 已有表的 dim 一致，否则报上面的 lance error

### Reranker 配置了但永远不生效

reranker 是个 silent feature — 2 个独立前置全满足才会触发：

| 层 | 前置条件 | 怎么验证 |
|---|---|---|
| **配置** | route 的 `reranker: <name>` 不为 null **且** `rerank.enabled: true`（或单次 body 带 `"rerank": true`）| `curl $SRV/admin/profiles` 看 route 的 `reranker` / `rerank_enabled` |
| **流量** | 客户端调用的是 `POST /query`（不是 `POST /search`）| server access log 是 `/query` 还是 `/search`；触发后 server log 应有 `Successfully reranked: N chunks from M original chunks` |

任一缺失 → reranker 静默不触发：

- `POST /search` 是 **LanceDB 直查 cosine + topk**，永远不调 reranker
- route `rerank.enabled: false`（默认值）+ 请求 body 也没传 `"rerank": true` → 不触发

> **数据层不是前置**：reranker 作用于 LightRAG 返回的 chunks，与来源无关。LanceDB-only container（仅 `/tm remember` 写入）上调 `/query` 时，LightRAG hybrid mode 会自动 fallback 用 LanceDB 向量召回，reranker 仍正常工作。要拿更高质量 answer，可额外通过 `/documents/text` 入知识图谱（不强制）。

### 客户端代码用 `enable_rerank` 字段没反应

**症状**：客户端 body 设了 `{"enable_rerank": true}`，server 完全没调 reranker，也没报错。

**根因**：字段名错了。正确字段是 `rerank: bool`，不是 `enable_rerank`。`QueryReq` 是 Pydantic strict 模型，**静默丢弃未知字段**，不会报错。

```bash
# 错（reranker 不触发，无 warning）
... -d '{"container":"X","query":"...","enable_rerank":true}'

# 对
... -d '{"container":"X","query":"...","rerank":true}'
```

### Reranker upstream 返回 400 `model_price_error` / `model_not_found`

**症状**：server log 出现 `ERROR: Error during reranking: 400 ... /v1/rerank`。LightRAG 静默吞错，`/query` answer 仍返回但**实际未经 rerank**（fallback 原序）。

**根因**：`rerankers[].model` 是网关不认识的 id。OpenAI-compat aggregator（newapi / one-api / litellm）只接受**已注册成 channel 的 model id**，臆造名字（`text-reranker`、profile 自身的 name 等）直接 400。

**修法（两选一）**：

1. 网关注册了**真正的 reranker channel**（cross-encoder 类） → `model` 改成那个 channel 实际注册的 model id（具体 id 由 gateway admin 决定）。
2. 网关只有 **embedding channel**（最常见的轻量部署） → `model` 改成你网关上**任何**一个 embedding model id。网关会把 `/v1/rerank` 路由成 embedding-cosine pseudo-rerank，返回合法 Cohere-v2 schema。质量边界：擅长分"最相关 vs 噪声"；小候选集（≤ 10 doc）退化为 binary classifier；顶级 ranking 仍需真 cross-encoder。

直接探活（不走 server）：

```bash
curl -sS -X POST "$GATEWAY/v1/rerank" -H "Authorization: Bearer $KEY" \
  -H 'Content-Type: application/json' \
  -d '{"model":"<your-embedding-or-rerank-model-id>","query":"x","documents":["a","b"],"top_n":2}'
```

改 `profiles.yaml` 后**必须** `docker compose up -d --force-recreate --pull never`（profiles registry 是 module-level singleton，只在 server 启动时 load 一次，`restart` 不重读 YAML）。验证：`curl $SRV/admin/profiles` 看 `rerankers[].model`。

### `/query` 报 `AssertionError: Embedding dim mismatch, expected: X, but loaded: Y`

**症状**：单 server 上某 container `/query` 500，nano_vectordb `AssertionError`。同 server 其他 dim 一致的 container 正常。

**根因**：LightRAG NanoVectorDB 当前在 `<server-data-root>/` 顶层共享 `vdb_*.json` / `graph_*.graphml` / `kv_store_*.json`，**不按 container 隔离**。第一个跑 `/query` 的 container 用自己的 dim 锁住这些文件，后续不同 dim container 全部撞 assertion。

**短期 workaround**：备份 + 清空全局文件让 LightRAG 重建（**会清空所有 container 共享的 KG**，下次 ingest 重抽 entity/relation）。详见 server 仓库 `docs/operations/known-issue-global-vdb-isolation.md`。

**避免触发**：单 server 不混用多 dim container 走 `/query`。`POST /search` 不受影响（直查 LanceDB，不加载 NanoVectorDB）。

### 服务拒绝启动：`FATAL: EMBEDDING_DIM=X disagrees with LanceDB schemas`（v0.18 启动闸）

**症状**：容器起不来，启动日志打一段 `=====` 包裹的：

```
[startup-check] FATAL: EMBEDDING_DIM=3072 disagrees with LanceDB schemas:
  - container=my-project: stored dim=1024
  ...
  Refusing to start to prevent silent /search RuntimeError storm.
```

**根因**：v0.18 在进入服务循环前做 **dim 一致性闸**——逐个 container 探 `chunks.lance` 的 `vector` 列实际维度，与运行时 `EMBEDDING_DIM` 比对。来源教训：2026-05-29 曾把 `EMBEDDING_DIM=3072` 配到 1024 维表上，导致所有 `/search` 连续 ~14h 报 `query dim doesn't match column vector dim`，而 `/health` 因为从不发向量查询一直绿。守卫**宁可不启动也不放行**这种静默错配。

**修复（择一）**：
- 把 `.env` 的 `EMBEDDING_DIM`（和 `EMBEDDING_MODEL`）对齐已落库容器的维度——通常是 `.env` 与 `profiles.yaml` 漂移、或误换 model 所致。
- 用新 model 重建受影响容器（`scripts/migrate_embeddings.py` in-place 换 dim）。
- **确在迁移途中**（明知短暂不一致）才临时 `TM_ALLOW_DIM_DRIFT=1` 跳过这道闸（设后日志打 `TM_ALLOW_DIM_DRIFT=1 set — skipping dim consistency check`）。**别**当常规启动参数挂着——它会让 14h 静默事故重演。

> 这是 **server 端 env**，不在本 skill 的 `config.toml`。skill 侧能做的只是识别这条 FATAL 日志、提示运维去对齐 dim。`EMBEDDING_DIM` 未设时此闸 best-effort 跳过（交由 runtime 内部 profiles 兜底）。

## 治理 / 梦境（v0.20）

> 自治记忆治理子系统（治理工具箱 / 梦境 / 编排 Agent）的排障。子系统总览 + 安全模型见 [`governance.md`](./governance.md)；端点 spec 见 [`api-reference.md`](./api-reference.md#治理与梦境端点v020)。

### agent run 卡在 pending 审批不前进

**症状**：`POST /admin/agent/{name}/invoke` 入队的 run 在 `GET /admin/agent/runs` 里 `status` 不再推进，`GET /admin/agent/approvals?status=pending` 里堆着一条破坏性工具（`snapshot_and_quarantine`）的待审批，没有任何东西自动执行它。

**根因**：**这是设计行为，不是 bug。** 破坏性工具在 agent 循环里**永不自动执行**——模型一旦想 apply 它，循环只记一条 pending 审批就继续/收尾。**人**通过审批端点是唯一执行器，无人值守循环从不自己跑破坏性删除。所以 run「停在 pending」= 安全闸生效，而非死锁。

**处理**：
- 真要执行 → `POST /admin/agent/approvals/{id}/approve`（人工背书，以记录的 tool+params 真执行 `dry_run=False`；这是 server 唯一破坏性真执行入口）。
- 不要执行 → `POST /admin/agent/approvals/{id}/reject`。
- 两端点 **404** = 审批不存在 / 已决 / **已过期**。pending 超过 `config:tools:approval_ttl_days`（默认 30 天）会被存储层隐藏 + 不可再 approve——这时 run 永远不会落地那一步，是预期。要延长有效期改 `PUT /admin/config` 的 `config:tools:approval_ttl_days`。
- 可逆工具「不落地」同理排查双闸：invoke 时须 `dry_run=false` **AND** `allow_apply=true` 才会自动 apply；任一留默认（`dry_run=true` 或 `allow_apply=false`）整个 run 都停在 plan 模式——这也是预期，不是失败。

### compress_knowledge_cluster 大簇分批 / 曾经 400

**症状**：对一个记忆很多的大容器跑 `POST /admin/tools/compress_knowledge_cluster/invoke`（`dry_run=false`）时，早期版本可能返回 **400**（簇全文超过单次 LLM 请求上限，request-too-large）；现在则看到 result 里出现多张局部索引卡 / 分批账目。

**根因 + 现状**：`compress_knowledge_cluster` 取同主题（同 tags 簇）最大簇压成高密度索引卡。**超大簇会按字节预算分批**——每批单独压成一张局部索引卡，送 LLM 前再经 `_truncate_for_llm` 兜底截断，避免整批超限。早期未分批时大簇会触发 400，**现已修复**（分批 + 截断）。压缩是**附加式不删源**（回滚 = 删掉新增的索引卡行），簇 <2 不压缩（单条无聚合价值）。

**处理 / 调参**：
- 分批字节预算：`config:agent:compress_batch_bytes`（或 env `TM_COMPRESS_BATCH_BYTES`，默认 8 MiB）。簇极大仍想更稳 → 调小批字节。
- 单行字符上限：`config:agent:compress_row_char_cap`。
- 先 `dry_run`（默认）预览会聚类哪个簇 + 簇内来源 + 字节账目（不调 LLM），确认范围再 `dry_run=false` 真执行。
- 真执行改了记忆主文件 → response `result.reindex_required=true` 会触发 best-effort re-embed（`result.reindex_job`）；re-embed 入队失败只记 warning + notes，不影响压缩结果本身。
- LLM 经 `rag_engine` 网关（HR-9 `LLM_*`）——若压缩报网关错（5xx / 超时），先查 server 的 `LLM_*` 配置与上游配额，而非这个工具本身。
