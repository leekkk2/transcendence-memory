---
name: transcendence-memory
description: Use when connecting to a self-hosted memory backend, searching/storing/managing memories, importing connection tokens, or troubleshooting retrieval issues. Use this skill whenever the user mentions memory search, RAG retrieval, embedding, memory storage, multimodal document upload, knowledge query, or wants to connect to a memory service — even if they don't explicitly say 'transcendence-memory'.
allowed-tools: Bash, Read, Write, Grep, Glob
argument-hint: "[command] [args...]"
---

## What This Skill Does

为 AI agent 提供自托管长期记忆能力，连接 [transcendence-memory-server](https://github.com/leekkk2/transcendence-memory-server) 后端。

核心能力：
- **连接**：通过 connection token 或手动配置一步完成鉴权
- **文本记忆**：通过轻量路径 CRUD 管理结构化记忆
- **多模态 RAG**：上传文档（PDF/图片/MD）或文本，经 RAG-Anything pipeline 入库，用自然语言查询获取 LLM 答案
- **容器管理**：列出、删除容器
- **排障**：诊断连接和检索问题

## Compatibility

本技能遵循 AgentSkills 规范，兼容以下 AI coding CLI：

| 平台 | 安装方式 |
|------|---------|
| Claude Code | `/install-skill https://github.com/leekkk2/transcendence-memory` |
| OpenClaw | `claw skill install transcendence-memory` |
| Codex CLI | 复制到 `~/.codex/skills/transcendence-memory/` |
| 其他 Agent | 将 SKILL.md 作为系统指令加载 |

## Principles

- **Keep builtin memory**：云端记忆是增强，不替换 agent 内置记忆
- **Zero dependency**：不需要安装任何软件包，agent 用原生工具（curl / 文件读写 / Python stdlib）即可完成所有操作
- **Progressive loading**：首次使用时读 `references/setup.md` 完成配置，之后只需本文件即可日常操作

## Built-in Commands

以下命令可通过斜杠命令 `/transcendence-memory <command>` 或简写 `/tm <command>` 调用：

| 命令 | 用途 | 示例 |
|------|------|------|
| `connect <token>` | 导入 connection token 并写入配置 | `/tm connect eyJlbmRw...` |
| `connect --manual` | 手动输入 endpoint / api_key / container | `/tm connect --manual` |
| `status` | 检查连接状态和服务健康 | `/tm status` |
| `search <query>` | 语义搜索记忆 | `/tm search 上次部署的架构决策` |
| `remember <text>` | 快速存储一条记忆 | `/tm remember 端口冲突导致部署失败` |
| `embed` | 重建当前容器索引 | `/tm embed` |
| `query <question>` | 多模态 RAG 查询（LLM 生成答案） | `/tm query 项目的整体架构是什么` |
| `upload <file>` | 上传文件到知识图谱 | `/tm upload ./design.pdf` |
| `containers` | 列出所有容器 | `/tm containers` |
| `batch <file.jsonl>` | 批量导入记忆 | `/tm batch memories.jsonl` |

### Command: `connect`

导入 connection token 或手动配置连接。

**Token 模式**（推荐）：
```bash
# Agent 收到 token 后自动执行：
TOKEN="$1"  # 用户提供的 base64 token
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

# 验证连接
curl -sS "$ENDPOINT/health"
```

**手动模式**：询问用户 endpoint、api_key、container，然后写入 config.toml。

### Command: `status`

检查连接和服务状态：
```bash
# 读取配置
CONFIG="$HOME/.transcendence-memory/config.toml"
ENDPOINT=$(grep '^endpoint' "$CONFIG" | sed 's/.*= *"//' | sed 's/".*//')
API_KEY=$(grep '^api_key' "$CONFIG" | sed 's/.*= *"//' | sed 's/".*//')
CONTAINER=$(grep '^container' "$CONFIG" | sed 's/.*= *"//' | sed 's/".*//')

# 健康检查
curl -sS "$ENDPOINT/health" | python3 -m json.tool

# 认证测试
curl -sS -X POST "$ENDPOINT/search" \
  -H "X-API-KEY: $API_KEY" -H "Content-Type: application/json" \
  -d "{\"container\":\"$CONTAINER\",\"query\":\"test\",\"topk\":1}"
```

### Command: `search`

```bash
curl -sS -X POST "${ENDPOINT}/search" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container\":\"${CONTAINER}\",\"query\":\"$ARGUMENTS\",\"topk\":5}"
```

### Command: `remember`

快速存储一条记忆（自动生成 ID，自动触发 embed）：
```bash
MEM_ID="mem-$(date +%s)"
curl -sS -X POST "${ENDPOINT}/ingest-memory/objects" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container\":\"${CONTAINER}\",\"objects\":[{\"id\":\"${MEM_ID}\",\"text\":\"$ARGUMENTS\",\"tags\":[]}],\"auto_embed\":true}"
```

### Command: `query`

多模态 RAG 查询（知识图谱 + LLM 答案生成）：
```bash
curl -sS -X POST "${ENDPOINT}/query" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"query\":\"$ARGUMENTS\",\"container\":\"${CONTAINER}\",\"mode\":\"hybrid\",\"top_k\":60}"
```

### Command: `upload`

上传文件到知识图谱：
```bash
curl -sS -X POST "${ENDPOINT}/documents/upload" \
  -H "X-API-KEY: ${API_KEY}" \
  -F "file=@$1" \
  -F "container=${CONTAINER}"
```

### Command: `batch`

批量导入记忆（使用内置脚本）：
```bash
python3 <skill-path>/scripts/batch-ingest.py \
  "${ENDPOINT}" "${API_KEY}" "${CONTAINER}" "$1"
```

## Quick Reference（已配置用户）

### 文本记忆（轻量路径）

```bash
# 检索记忆
curl -sS -X POST "${ENDPOINT}/search" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","query":"你要搜的内容","topk":5}'

# 存储记忆
curl -sS -X POST "${ENDPOINT}/ingest-memory/objects" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","objects":[{"id":"mem-001","text":"要存储的内容","tags":["tag1"]}]}'

# 重建索引（存储新记忆后执行）
curl -sS -X POST "${ENDPOINT}/embed" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","background":false,"wait":true}'

# 更新记忆
curl -sS -X PUT "${ENDPOINT}/containers/${CONTAINER}/memories/mem-001" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"text":"更新后的内容","tags":["new-tag"]}'

# 删除记忆
curl -sS -X DELETE "${ENDPOINT}/containers/${CONTAINER}/memories/mem-001" \
  -H "X-API-KEY: ${API_KEY}"
```

> 更新或删除记忆后，需调用 `/embed` 刷新索引。

### 多模态 RAG（RAG-Anything pipeline）

```bash
# 文本入知识图谱
curl -sS -X POST "${ENDPOINT}/documents/text" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","text":"要入库的长文本...","description":"可选描述"}'

# 上传文件（PDF/图片/Markdown）
curl -sS -X POST "${ENDPOINT}/documents/upload" \
  -H "X-API-KEY: ${API_KEY}" \
  -F "file=@/path/to/document.pdf" \
  -F "container=${CONTAINER}"

# 多模态 RAG 查询（返回 LLM 生成的答案）
curl -sS -X POST "${ENDPOINT}/query" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"query":"你的问题","container":"${CONTAINER}","mode":"hybrid","top_k":60}'
```

### 容器管理

```bash
# 列出所有容器
curl -sS "${ENDPOINT}/containers" -H "X-API-KEY: ${API_KEY}"

# 删除容器
curl -sS -X DELETE "${ENDPOINT}/containers/${CONTAINER}" \
  -H "X-API-KEY: ${API_KEY}"

# 健康检查
curl -sS "${ENDPOINT}/health"
```

变量从本地配置文件 `~/.transcendence-memory/config.toml` 读取。

## First-Time Setup

首次使用时，阅读 `references/setup.md` 完成配置。

核心流程只有两步：
1. 从 server 获取 **connection token**（通过 `/export-connection-token` 端点或管理员提供）
2. 运行 `/tm connect <token>` 自动完成配置

或手动运行 `/tm connect --manual` 逐步输入。

> 配置完成后，`references/setup.md` 不再需要加载到上下文中。

## API Reference

详细的请求/响应格式见 `references/api-reference.md`。

### 轻量路径（文本记忆 CRUD）

| 端点 | 方法 | 用途 | 认证 |
|------|------|------|------|
| `/health` | GET | 健康检查 | 不需要 |
| `/search` | POST | 检索记忆 | 需要 |
| `/embed` | POST | 重建索引 | 需要 |
| `/ingest-memory/objects` | POST | 写入 typed objects | 需要 |
| `/ingest-memory/contract` | GET | 查看 ingest 语义边界 | 不需要 |
| `/ingest-structured` | POST | 结构化 JSON ingest | 需要 |
| `/containers/{container}/memories/{id}` | PUT | 更新记忆 | 需要 |
| `/containers/{container}/memories/{id}` | DELETE | 删除记忆 | 需要 |

### 多模态路径（RAG-Anything pipeline）

| 端点 | 方法 | 用途 | 认证 |
|------|------|------|------|
| `/documents/text` | POST | 文本入知识图谱 | 需要 |
| `/documents/upload` | POST | 上传文件（PDF/图片/MD）入库 | 需要 |
| `/query` | POST | 多模态 RAG 查询 | 需要 |

### 管理端点

| 端点 | 方法 | 用途 | 认证 |
|------|------|------|------|
| `/containers` | GET | 列出容器 | 需要 |
| `/containers/{name}` | DELETE | 删除容器 | 需要 |
| `/export-connection-token` | GET | 导出连接令牌 | 需要 |
| `/jobs/{pid}` | GET | 异步任务状态 | 需要 |

认证方式：`X-API-KEY: <api-key>` 或 `Authorization: Bearer <api-key>`

## Architecture Overview

详见 `references/ARCHITECTURE.md`。

```
Agent ──HTTPS + API Key──> transcendence-memory-server
                            |-- FastAPI HTTP 层
                            |-- Container 隔离
                            |-- 轻量路径: /search + /ingest + /embed
                            |   └── Embedding -> LanceDB 向量存储
                            └── 多模态路径: /documents + /query
                                └── RAG-Anything -> 知识图谱 -> LLM 答案
```

## Troubleshooting

详见 `references/troubleshooting.md`。

常见快速排查：
- **连接不上**：运行 `/tm status` 检查，或 `curl -sS "${ENDPOINT}/health"`
- **401/403**：检查 API key 是否正确
- **search 返回空**：先执行 `/tm embed` 重建索引
- **search 200 但 body 有错**：视为失败，检查 server 日志
- **文档上传失败**：检查文件格式（支持 PDF/图片/MD）和大小
- **query 返回空**：确认已通过 `/documents/text` 或 `/documents/upload` 入库
- **update/delete 后搜索不到变更**：需调用 `/tm embed` 刷新索引

## Batch & Async Operations

### 批量入库（大量记忆）

当需要入库几十到几百条记忆时：

```bash
# 准备 JSONL 文件（每行一个 JSON 对象）
# {"id":"mem-001","text":"记忆内容","tags":["tag1"]}
# {"id":"mem-002","text":"另一条记忆","source":"telegram"}

/tm batch memories.jsonl
# 或直接调用脚本：
python3 <skill-path>/scripts/batch-ingest.py \
  "${ENDPOINT}" "${API_KEY}" "${CONTAINER}" memories.jsonl
```

脚本自动分批（每批 50 条）、失败重试、进度输出。零外部依赖，只用 Python 标准库。

### 异步任务

`/embed` 和 `/documents/upload` 支持异步模式：

```bash
# 异步提交索引重建
curl -sS -X POST "${ENDPOINT}/embed" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","background":true}'

# 查询异步任务状态
curl -sS "${ENDPOINT}/jobs/${PID}" -H "X-API-KEY: ${API_KEY}"
```

### 操作方式选择

| 场景 | 推荐方式 |
|------|---------|
| 健康检查、单次搜索、几条记忆写入 | `/tm` 内置命令 |
| 几十到几百条记忆批量入库 | `/tm batch file.jsonl` |
| 大容器索引重建 | `/tm embed` 或异步模式 |
| 文档入知识图谱 | `/tm upload file.pdf` 或 `/documents/text` |
| 需要 LLM 综合答案 | `/tm query 你的问题` |

## Files in this skill

| 文件 | 用途 | 何时加载 |
|------|------|---------|
| `references/setup.md` | 首次配置指南 | 仅首次使用 |
| `references/api-reference.md` | API 完整参考 | 需要 API 细节时 |
| `references/ARCHITECTURE.md` | 架构与数据流 | 需要理解系统时 |
| `references/OPERATIONS.md` | 操作验证与验收 | 部署验证时 |
| `references/troubleshooting.md` | 排障指引 | 出问题时 |
| `references/templates/config.toml.template` | 配置文件模板 | 首次配置时 |
| `scripts/batch-ingest.py` | 批量入库脚本 | 大量记忆入库时 |

## When NOT to Use

- 部署后端服务 -> `transcendence-memory-server` 仓库
- 管理 Docker / systemd / Nginx -> `transcendence-memory-server` 仓库
- 排障服务端问题（5xx、存储、日志） -> `transcendence-memory-server` 仓库
- 配置 Embedding / LLM / VLM 模型 -> server 端配置，skill 端无需关注
