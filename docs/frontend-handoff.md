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
transcendence-memory backend export-connection --topology split_machine --output bundle.json
```

导出成功后，CLI 应同时明确告诉部署方：
- 当前前端要使用的鉴权模式
- 前端仍需本地补齐哪些鉴权材料
- 前端下一步应执行的命令顺序

也就是说，后端部署完成后，不应该只把 `bundle.json` 丢给前端，还应把 CLI 输出的 handoff 提醒一并交给前端操作员。

### 前端机器导入

```bash
transcendence-memory frontend import-connection --bundle-file bundle.json
# 如果后端导出时提示 auth mode=api_key，则前端需要补：
transcendence-memory auth set-api-key --api-key <frontend-local-api-key>
transcendence-memory frontend check
transcendence-memory frontend smoke
```

### Rules

- bundle 只包含非敏感信息
- API key、token、secret 不应包含在 bundle 中
- split-machine 不允许导出 `127.0.0.1` / `localhost` / 私有网段 / 保留测试网 IP 作为前端连接目标
- 如果 backend `config.toml` 里的 `advertised_url` 仍是本机回环、局域网或测试地址，先改成前端实际可达的公网域名/公网 IP，再执行导出
- 前端机器需要自行补齐本地 secret

### Acceptance

导入后至少验证：
- reachability
- auth compatibility
- `health` / `search` / `embed` smoke path

## English

Use `frontend import-connection`, then `frontend check`, then `frontend smoke`. The imported bundle is redacted and never carries secrets.
