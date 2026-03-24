# Frontend Handoff / 前端连接导入

## 中文优先

### 身份优先 / Identity first

本页主要面向 **frontend 身份** 或 **both 身份中的 frontend 阶段**。

- 如果当前机器是 `backend`，不要优先把自己当作 frontend 客户端
- 先检查本地 `operator-identity.md`
- 若身份文档缺失，先补录身份，再继续导入连接

对 `both` 身份：
- 先确认 backend 已健康
- 再执行 frontend import / check / smoke

### 后端机器导出

```bash
transcendence-memory backend export-connection --topology split_machine
```

### 前端机器导入

```bash
transcendence-memory frontend import-connection --bundle-file bundle.json
transcendence-memory frontend check
transcendence-memory frontend smoke
```

### Rules

- bundle 只包含非敏感信息
- API key、token、secret 不应包含在 bundle 中
- split-machine 不允许导出 `127.0.0.1` / `localhost` 作为前端连接目标
- 前端机器需要自行补齐本地 secret

### Acceptance

导入后至少验证：
- reachability
- auth compatibility
- `health` / `search` / `embed` smoke path

## English

Use `frontend import-connection`, then `frontend check`, then `frontend smoke`. The imported bundle is redacted and never carries secrets.
