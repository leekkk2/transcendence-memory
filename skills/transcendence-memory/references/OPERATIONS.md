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

## Reminder

Builtin memory 保持启用。本技能增强检索能力，不替换内置记忆。
