# Frontend Handoff / 前端连接导入

## 中文优先

后端机器导出：

```bash
transcendence-memory backend export-connection --topology split_machine
```

前端机器导入：

```bash
transcendence-memory frontend import-connection --bundle-file bundle.json
transcendence-memory frontend check
transcendence-memory frontend smoke
```

注意：
- bundle 只包含非敏感信息
- 本地 secret 仍然需要在前端机器自行配置
- split-machine 不允许导出 `127.0.0.1` / `localhost` 这类地址

## English

Use `frontend import-connection`, then `frontend check`, then `frontend smoke`. The imported bundle is redacted and never carries secrets.
