# Dataflow Migration / 数据流迁移说明

## Source shape

原始 `rag-everything-enhancer` dataflow 围绕：
- `/health`
- `/search`
- `/embed`
- `container` namespace

## Current shape

当前 `transcendence-memory` 仍保留 `health` / `search` / `embed` 作为 operator-facing acceptance surface，但 backend API 已适配为新的 memory route 和 PostgreSQL + pgvector 持久化实现。

## Not Migrated

- `build-manifest`
- `ingest-memory`

这些旧别名目前没有在公共代码库里恢复。
