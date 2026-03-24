# Setup Migration / 迁移后的 Setup 契约

这个文档保留原 `rag-everything-enhancer` setup 契约中真正重要的 operator 形状，但已经去掉私有 endpoint、真实 API key 和内部路径假设。

## 保留的形状

- `endpoint`
- `auth.type`
- `auth.name`
- `auth.value`
- `defaultContainer`
- `RAG_CONFIG_FILE`
- `RAG_ENDPOINT`
- `RAG_AUTH_HEADER`
- `RAG_API_KEY`
- `RAG_DEFAULT_CONTAINER`

## 说明

- 这些字段的存在是为了迁移兼容，不代表当前 backend 一定仍然实现与原系统完全一致的 `container` 语义。
- 真实私有值已经移除，使用请参考 `docs/examples/` 下的 sanitized examples。
