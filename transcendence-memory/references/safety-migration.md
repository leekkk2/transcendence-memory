# Safety Migration / 安全与范围迁移说明

从原 `rag-everything-enhancer` 保留的关键安全规则：

- builtin memory 保持启用
- RAG / external retrieval 是 enhancement，不是 replacement
- 公共仓库中不得出现真实 API key
- 公共仓库中不得出现私有 endpoint
- 迁移兼容说明必须明确区分 `Preserved` / `Adapted` / `Not Migrated`
