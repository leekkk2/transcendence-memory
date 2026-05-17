# 操作验证 / Operations

## 连接验证流程

按顺序执行，全部通过即可视为 rollout 完成：

```bash
# 1. 加载配置
ENDPOINT=$(grep 'endpoint' ~/.transcendence-memory/config.toml | head -1 | cut -d'"' -f2)
API_KEY=$(grep 'api_key' ~/.transcendence-memory/config.toml | head -1 | cut -d'"' -f2)
CONTAINER=$(grep 'container' ~/.transcendence-memory/config.toml | head -1 | cut -d'"' -f2)

# 2. 健康检查
curl -sS "${ENDPOINT}/health"
# 预期：200 + runtime_ready: true

# 3. 搜索测试
curl -sS -X POST "${ENDPOINT}/search" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container\":\"${CONTAINER}\",\"query\":\"test\",\"topk\":3}"
# 预期：200（空结果正常）

# 4. 索引重建
curl -sS -X POST "${ENDPOINT}/embed" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container\":\"${CONTAINER}\",\"background\":false,\"wait\":true}"
# 预期：200 + success

# 5. typed object 写入（按需）
curl -sS -X POST "${ENDPOINT}/ingest-memory/objects" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container\":\"${CONTAINER}\",\"objects\":[]}"
# 预期：accepted
```

## 批量入库预检

在执行大规模批量导入前，先执行以下探测：

```bash
# 5a. 探测 ingest contract — 确认接口接受的字段
curl -sS "${ENDPOINT}/ingest-memory/contract"
# 预期：200 + 返回 schema 信息

# 5b. 最小 payload 探针 — 确认最基本的写入可行
curl -sS -X POST "${ENDPOINT}/ingest-memory/objects" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container\":\"${CONTAINER}\",\"objects\":[{\"id\":\"probe-test\",\"text\":\"contract probe\"}]}"
# 预期：accepted: 1

# 5c. 逐步加回可选字段测试（tags / metadata）
curl -sS -X POST "${ENDPOINT}/ingest-memory/objects" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container\":\"${CONTAINER}\",\"objects\":[{\"id\":\"probe-tags\",\"text\":\"test\",\"tags\":[\"probe\"],\"metadata\":{\"source\":\"test\"}}]}"
# 预期：accepted: 1；若 422 则定位不兼容字段

# 5d. 清理探针数据
curl -sS -X DELETE "${ENDPOINT}/containers/${CONTAINER}/memories/probe-test" \
  -H "X-API-KEY: ${API_KEY}"
curl -sS -X DELETE "${ENDPOINT}/containers/${CONTAINER}/memories/probe-tags" \
  -H "X-API-KEY: ${API_KEY}"
```

> 使用 `batch-ingest.py --probe` 可自动完成步骤 5a。

## 多模态验证流程

在轻量路径验证通过后，执行多模态路径验证：

```bash
# 6. 文本入知识图谱
curl -sS -X POST "${ENDPOINT}/documents/text" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container\":\"${CONTAINER}\",\"text\":\"Transcendence Memory 是一个多模态 RAG 系统，支持文本、PDF 和图片的知识管理。\",\"description\":\"验证文本\"}"
# 预期：200 + status: accepted

# 7. 多模态 RAG 查询
curl -sS -X POST "${ENDPOINT}/query" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"query\":\"什么是 Transcendence Memory\",\"container\":\"${CONTAINER}\",\"mode\":\"hybrid\",\"top_k\":60}"
# 预期：200 + answer 字段包含 LLM 生成的答案

# 8. 容器列表
curl -sS "${ENDPOINT}/containers" -H "X-API-KEY: ${API_KEY}"
# 预期：200 + 包含测试容器
```

## CRUD 验证流程

验证记忆的完整增删改查：

```bash
# 9. 写入记忆
curl -sS -X POST "${ENDPOINT}/ingest-memory/objects" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container\":\"${CONTAINER}\",\"objects\":[{\"id\":\"test-crud-001\",\"text\":\"CRUD 验证记忆\",\"tags\":[\"test\"]}]}"
# 预期：accepted: 1

# 10. 重建索引
curl -sS -X POST "${ENDPOINT}/embed" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container\":\"${CONTAINER}\",\"background\":false,\"wait\":true}"
# 预期：200 + success

# 11. 搜索确认写入
curl -sS -X POST "${ENDPOINT}/search" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container\":\"${CONTAINER}\",\"query\":\"CRUD 验证\",\"topk\":3}"
# 预期：结果包含 test-crud-001

# 12. 更新记忆
curl -sS -X PUT "${ENDPOINT}/containers/${CONTAINER}/memories/test-crud-001" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"text\":\"CRUD 验证记忆（已更新）\",\"tags\":[\"test\",\"updated\"]}"
# 预期：status: updated

# 13. 删除记忆
curl -sS -X DELETE "${ENDPOINT}/containers/${CONTAINER}/memories/test-crud-001" \
  -H "X-API-KEY: ${API_KEY}"
# 预期：status: deleted

# 14. 重建索引（更新/删除后必须执行）
curl -sS -X POST "${ENDPOINT}/embed" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container\":\"${CONTAINER}\",\"background\":false,\"wait\":true}"
# 预期：200 + success
```

## Rollout 完成标准

### 基础（轻量路径）
- `/health` 返回 200 且 `runtime_ready: true`
- `/search` 返回 200（body 无错误）
- `/embed` 返回 200 + success

### 多模态路径
- `/documents/text` 返回 200 + accepted
- `/query` 返回 200 + 包含 LLM 生成的 answer
- `/containers` 返回 200 + 容器列表

### CRUD
- 写入 → 索引 → 搜索 → 更新 → 删除 → 索引，全链路通过

### 批量入库预检
- `/ingest-memory/contract` 返回 200
- 最小 payload 写入成功（无 422）
- 可选字段（tags/metadata）兼容性已确认

### 通用规则
- HTTP 200 但 body 有 error → **不算通过**
- 任何 5xx → **不算通过**
- 403 + Cloudflare 页面 → **WAF 拦截，非鉴权失败**

## Multi-Embedding 运维操作（v0.7.0+ / v0.10.0+）

### 切换 container 默认 embedding profile

只改 server 端 `config/profiles.yaml` routes 段即可，**不需要重启容器**（cache key 含 route signature，profile 变化时下次请求自动刷新 LightRAG instance）：

```yaml
routes:
  - match: {exact: home}                  # 新增 exact 规则
    embedding: openai-small-1024
  - match: {default: true}                # 兜底不变
    embedding: gemini-3072
```

### container 内 in-place 换 dim（替换式 migration）

使用 server 自带 `scripts/migrate_embeddings.py`（v0.10.0+）。dry-run 默认；显式 `--commit` 才写：

```bash
docker exec <container> python3 /app/scripts/migrate_embeddings.py \
  --container default --from gemini-3072 --to openai-small-1024 --dry-run
docker exec <container> python3 /app/scripts/migrate_embeddings.py \
  --container default --from gemini-3072 --to openai-small-1024 --commit
# 写 chunks_v2 → atomic rename → 旧表保留为 chunks_old_<ts>
```

回滚：把 `chunks.lance` 删，将 `chunks_old_<ts>.lance` rename 回 `chunks.lance`。

### 双轨并运（新建镜像 container，源不动）

clone 一个 container 到 sibling 命名（如 `home` → `home_openai`），源完全不动。`routes` 配上 glob（如 `*_openai → openai-small-1024`），dst 命名命中 glob 即自动路由。

**何时用 clone vs in-place migrate**：
- in-place migrate（上节，server 内置）：想换 profile 但保持 container 名不变；旧表自动备份；适合**单轨切换**
- clone（本节）：源 container 完全不动，镜像出 sibling container；适合**双轨并运** / A/B 对比 / 实验性试 profile / 容器重命名

使用 server v0.11.0+ 内置 `scripts/clone_container_reembed.py`（含 dry-run/commit + 自动 chown tm:tm + 顶级列三字段同步 + 9 个 regression tests）：

```bash
docker exec <container> python3 /app/scripts/clone_container_reembed.py \
  --src home --dst home_openai --to-profile openai-small-1024 --dry-run
docker exec <container> python3 /app/scripts/clone_container_reembed.py \
  --src home --dst home_openai --to-profile openai-small-1024 --commit
# 自动 chown 到 tm:tm (10001:10001)；--no-chown 跳过（宿主无权场景）
```

后续写入：双轨需调用方**写两遍**保持同步（或等 server 端 `mirror_containers` feature 自动镜像）。读取：按业务选 container 名，server 自动路由对应 profile。

### 行级 embedding 归属查询（重要！避免误判位置）

LanceDB chunks 表 v0.7.0+ 起为每行 schema 增加了 **3 个顶级列**记录嵌入归属：

| 顶级列 | 含义 | 取法 |
|---|---|---|
| `embedding_model` | 实际调用的 model 名（如 `text-embedding-3-small`） | `row['embedding_model']` |
| `embedding_dim` | 实际维度（如 `1024`） | `row['embedding_dim']` |
| `embedding_profile` | profiles.yaml 里的 profile 名（如 `openai-small-1024`） | `row['embedding_profile']` |

⚠ **常见误判位置**：这 3 个字段**不在** `row['metadata']` JSON 内（`metadata` 是业务侧 client ingest 时给的 dict），它们是**顶级 LanceDB 列**。审计 / 排查时直接读 `t.to_pandas()['embedding_model']` 不要 `json.loads(row['metadata'])['embedding_model']`（永远拿不到）。

容器内查询示例：

```python
import lancedb
db = lancedb.connect('/data/tasks/rag/containers/<X>/lancedb')
t = db.open_table('chunks')
df = t.to_pandas()
print(df[['chunkId', 'embedding_model', 'embedding_dim', 'embedding_profile']].head())
# 全表分桶
print(df['embedding_model'].value_counts())
```

如果某行该列为空（v0.6.x 写入的旧行），按业务侧 server 端 profiles.yaml 的 default route 推断即可。

### 监控 / 巡检

```bash
curl -sS -H "X-API-KEY: ${KEY}" "${ENDPOINT}/admin/profiles" | jq
curl -sS -X POST -H "X-API-KEY: ${KEY}" "${ENDPOINT}/admin/probe-embedding?profile=<name>"
curl -sS -H "X-API-KEY: ${KEY}" "${ENDPOINT}/admin/system-health"   # 含 profiles summary
```

## Reminder

Builtin memory 保持启用。本技能增强检索能力，不替换内置记忆。
