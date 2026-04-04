# Architecture

## 双轨架构总览

```
┌──────────────────────────┐
│  AI Agent (Claude Code)  │
│  + transcendence-memory  │
│    skill                 │
└──────────┬───────────────┘
           │ HTTPS + API Key
           ▼
┌──────────────────────────────────────────────────┐
│  transcendence-memory-server                     │
│  ├── FastAPI HTTP 层                             │
│  ├── Container 隔离                              │
│  │   ├── container: imac                         │
│  │   ├── container: work                         │
│  │   └── container: lab                          │
│  │                                               │
│  ├── 轻量路径 ─────────────────────────────────  │
│  │   ├── /search, /ingest-memory/objects, /embed │
│  │   ├── /containers/{c}/memories/{id} (CRUD)    │
│  │   ├── Embedding: gemini-embedding-001         │
│  │   └── LanceDB 向量存储 + 混合搜索            │
│  │                                               │
│  └── 多模态路径 ───────────────────────────────  │
│      ├── /documents/text, /documents/upload      │
│      ├── /query (RAG 查询 → LLM 答案)           │
│      ├── RAG-Anything pipeline                   │
│      │   ├── VLM: qwen3-vl-plus (视觉理解)      │
│      │   ├── LLM: gemini-2.5-flash (生成答案)    │
│      │   └── Embedding: gemini-embedding-001     │
│      └── 知识图谱存储                            │
└──────────────────────────────────────────────────┘
```

## 双轨说明

### 轻量路径（文本记忆 CRUD）

适用于结构化文本记忆的增删改查。数据流简单直接：

- **写入**：Agent 发送 objects → Server 持久化到 JSONL
- **索引**：Agent 调用 /embed → Server 用 Embedding 模型生成向量 → 写入 LanceDB
- **检索**：Agent 发送 query → Server embed query → LanceDB 向量搜索 → 返回匹配结果
- **更新/删除**：Agent 调用 PUT/DELETE → Server 修改持久化数据 → Agent 调用 /embed 刷新索引

### 多模态路径（RAG-Anything pipeline）

适用于复杂文档（PDF、图片、长文本）的理解与问答。数据流经过多阶段处理：

- **入库**：文档上传/文本提交 → RAG-Anything 解析（VLM 处理图片/PDF）→ 分块 → Embedding → 知识图谱存储
- **查询**：自然语言问题 → 混合检索（向量 + 关键词）→ 上下文组装 → LLM 生成答案 → 返回答案 + 来源引用

## 核心概念

- **Container**：命名空间隔离。每个 agent / 项目 / 机器可以有自己的 container，记忆互不干扰。
- **Embedding**：文本通过 gemini-embedding-001 (dim=3072) 转为向量。
- **知识图谱**：多模态路径将文档解析为结构化知识图谱，支持更精准的语义检索。
- **双轨互补**：轻量路径适合快速 CRUD；多模态路径适合复杂文档理解。两者共享同一 container 命名空间。

## 模型配置（Server 端）

| 用途 | 模型 | 说明 |
|------|------|------|
| Embedding | gemini-embedding-001 (dim=3072) | 向量化，双轨共用 |
| LLM | gemini-2.5-flash | `/query` 答案生成 |
| VLM | qwen3-vl-plus | 图片/PDF 视觉理解 |

所有模型在 server 端配置，通过统一 API endpoint 调用。Skill 端用户无需配置模型。

## 职责边界

| 组件 | 职责 |
|------|------|
| **Skill（本仓库）** | 引导 agent 如何连接、使用、排障 |
| **Server** | API 服务、存储、索引、embedding、LLM/VLM 推理、鉴权 |
| **Agent** | 读 skill 指令，用 curl / 文件操作执行 |
