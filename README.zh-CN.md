# Transcendence Memory

> **为 AI coding agent 提供长期记忆能力。自托管、多模态、跨会话可用。**

[English Documentation](README.md)

Transcendence Memory 是一个 agent skill，为各类 AI coding CLI 提供持久化记忆能力。你可以搜索过去的决策、保存关键经验，并基于文档构建的知识图谱进行查询。

## 为什么需要它

AI 对话天然是短时的。这个 skill 让你的 agent 可以：

- **记住**：跨会话保存决策、经验和上下文
- **回忆**：通过语义检索在新会话里找回过去状态
- **推理**：对 PDF、图片、代码等资料执行多模态 RAG 查询，并生成答案
- **复用**：通过 container 隔离实现跨项目知识复用

## 安装

一行安装：

```bash
npx skills add https://github.com/leekkk2/transcendence-memory --skill transcendence-memory
```

或者在 Claude Code 会话内通过插件市场安装：

```text
/plugin marketplace add leekkk2/transcendence-memory
/plugin install transcendence-memory
```

安装后重启会话，即可使用 `/tm` 命令。

## 快速开始

### 1. 部署后端

你需要先运行 [transcendence-memory-server](https://github.com/leekkk2/transcendence-memory-server)：

```bash
git clone https://github.com/leekkk2/transcendence-memory-server.git
cd transcendence-memory-server
cp .env.example .env   # 填入你的 API keys
docker compose up -d --build
```

### 2. 建立连接

从服务端获取 connection token，然后告诉你的 agent：

```text
/tm connect eyJlbmRwb2ludCI6Imh0dHBz...
```

也可以手动连接：

```text
/tm connect --manual
```

agent 会把 endpoint、API key 和 container 名称写入 `~/.transcendence-memory/config.toml`。

### 3. 使用

```text
/tm search what was the database migration strategy
/tm remember port 5432 conflicts with local postgres, use 5433
/tm query summarize the authentication architecture
/tm upload ./design-doc.pdf
/tm status
```

## 内置命令

| 命令 | 说明 |
|------|------|
| `/tm connect <token>` | 导入 connection token |
| `/tm connect --manual` | 手动配置 endpoint/key/container |
| `/tm status` | 检查连接和服务健康状态 |
| `/tm search <query>` | 语义检索记忆 |
| `/tm remember <text>` | 快速保存一条记忆 |
| `/tm embed` | 重建搜索索引 |
| `/tm query <question>` | 多模态 RAG 查询并返回 LLM 答案 |
| `/tm upload <file>` | 上传 PDF/图片/Markdown 到知识图谱 |
| `/tm containers` | 列出全部 containers |
| `/tm batch <file.jsonl>` | 批量导入记忆 |

## 架构

```text
你的 Agent + 这个 skill
    |
    | HTTPS + API Key
    v
transcendence-memory-server
    |-- LanceDB 向量检索（文本记忆）
    |-- LightRAG 知识图谱（实体/关系抽取）
    └-- RAG-Anything（PDF/图片/表格多模态解析）
```

这个 skill 是一个**无状态客户端**，所有数据都保存在你的服务端。skill 负责向 agent 提供说明文档和调用 API 的 curl 模板。

## 项目结构

```text
skills/transcendence-memory/
  SKILL.md                    # 主技能入口（agent 会读取这里）
  references/
    setup.md                  # 首次配置指南
    api-reference.md          # 完整 API 参考
    ARCHITECTURE.md           # 系统架构
    OPERATIONS.md             # 验证清单
    troubleshooting.md        # 排障指南
    templates/
      config.toml.template    # 配置文件模板
  scripts/
    batch-ingest.py           # 批量导入（零依赖，仅 Python 标准库）
```

## 相关项目

- **Server**: [transcendence-memory-server](https://github.com/leekkk2/transcendence-memory-server) - 负责存储、索引和检索记忆的后端
- **API Docs**: 默认可在 `http://your-server:8711/docs` 查看（FastAPI Swagger UI）

## License

MIT
