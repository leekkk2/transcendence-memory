# 排障 / Troubleshooting

## 快速诊断

```bash
# 读取本地配置
ENDPOINT=$(grep 'endpoint' ~/.transcendence-memory/config.toml | head -1 | cut -d'"' -f2)
API_KEY=$(grep 'api_key' ~/.transcendence-memory/config.toml | head -1 | cut -d'"' -f2)

# 检查配置文件是否存在
ls -la ~/.transcendence-memory/config.toml

# 检查连接
curl -sS -i "${ENDPOINT}/health"
```

## 通用问题

### health 返回空容器列表

`available_containers: []` 是正常的 — 容器在首次写入数据时按需创建。新部署的 server 没有任何容器。

### 配置文件不存在

尚未完成首次配置。参考 `references/setup.md`。

### 连接被拒绝 / 超时

```bash
# 检查 endpoint 是否可达
curl -sS -o /dev/null -w "%{http_code}" "${ENDPOINT}/health"
```

可能原因：
- endpoint 地址错误
- server 未启动
- 防火墙 / 网络不通
- 反向代理配置问题

→ 联系后端管理员确认服务状态。

### 401 Unauthorized

API key 不匹配：

```bash
# 确认本地 key
grep 'api_key' ~/.transcendence-memory/config.toml

# 直接测试
curl -sS -i "${ENDPOINT}/search" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"test","query":"hello","topk":1}'
```

→ 向后端管理员确认正确的 API key。

### 403 Forbidden（Cloudflare / WAF 拦截）

如果 `curl` 成功但 Python 脚本返回 403，且响应体包含 `error code: 1010` 或 Cloudflare 页面：

**根因**：Python `urllib.request` 的默认 `User-Agent` 被 WAF 识别并拦截。

**解决**：
- 使用 `batch-ingest.py` v0.2+，已内置 WAF 兼容请求头
- 或在自定义脚本中显式设置：
  ```python
  headers["User-Agent"] = "transcendence-memory-batch/0.2"
  headers["Accept"] = "application/json, text/plain, */*"
  ```
- 确认不是 API key 问题：同一 key 用 `curl` 测试是否成功

### 413 Request Entity Too Large

单次请求体超出网关/反向代理限制（通常来自 nginx）。

**解决**：
- 使用 `batch-ingest.py --max-bytes 500000` 限制单批字节数
- 脚本会在遇到 413 时自动对半缩批重试
- 对超长文件（>100KB），建议先截断或拆分再入库
- 若反复出现，联系管理员调大 nginx `client_max_body_size`

### 422 Unprocessable Entity

请求体格式不符合 `/ingest-memory/objects` 的 schema 要求。

**排查**：
1. 先探测接口 contract：
   ```bash
   curl -sS "${ENDPOINT}/ingest-memory/contract"
   ```
2. 用最小 payload 测试：
   ```bash
   curl -sS -X POST "${ENDPOINT}/ingest-memory/objects" \
     -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
     -d '{"container":"${CONTAINER}","objects":[{"id":"test","text":"hello"}]}'
   ```
3. 逐步加回 `tags`、`metadata` 等字段定位不兼容字段
4. 使用 `batch-ingest.py --probe` 在批量导入前自动探测

常见原因：
- `metadata` 字段包含不支持的类型
- `tags` 非字符串数组
- `text` 为空
- 字段名拼写错误

### 5xx 错误

服务端问题，不是客户端问题。联系后端管理员，或参考 `transcendence-memory-server` 的排障文档。

## 轻量路径问题

### search 返回 200 但 body 有错误

这不算成功。可能原因：
- container 未初始化 → 先执行 `/embed`
- server 内部错误 → 检查 server 日志

### search 无结果

```bash
# 先重建索引
curl -sS -X POST "${ENDPOINT}/embed" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","background":false,"wait":true}'

# 再搜索
curl -sS -X POST "${ENDPOINT}/search" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","query":"test","topk":5}'
```

新 container 或新写入的记忆需要先 `/embed` 才能被检索到。

### update/delete 后变更未生效

**关键**：更新或删除记忆后，必须调用 `/embed` 刷新索引，否则 `/search` 仍返回旧数据。

```bash
# 更新/删除操作后，执行索引重建
curl -sS -X POST "${ENDPOINT}/embed" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","background":false,"wait":true}'
```

## 多模态路径问题

### 文档上传失败

```bash
# 检查文件是否存在且格式正确
file /path/to/document.pdf

# 检查上传
curl -sS -i -X POST "${ENDPOINT}/documents/upload" \
  -H "X-API-KEY: ${API_KEY}" \
  -F "file=@/path/to/document.pdf" \
  -F "container=${CONTAINER}"
```

可能原因：
- 文件格式不支持（仅支持 PDF、PNG/JPG 图片、Markdown）
- 文件过大（检查 server 端限制）
- multipart/form-data 格式错误
- VLM 未配置（server 端问题）→ 联系管理员

### query 返回空答案

```bash
# 确认知识图谱中有数据
curl -sS -X POST "${ENDPOINT}/query" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"query":"列出所有已入库的内容","container":"${CONTAINER}","mode":"hybrid","top_k":60}'
```

可能原因：
- 尚未通过 `/documents/text` 或 `/documents/upload` 入库任何内容
- 入库后处理尚未完成（异步任务）→ 用 `/jobs/{pid}` 检查状态
- 查询与入库内容语义不相关 → 尝试更宽泛的查询
- LLM 未配置（server 端问题）→ 联系管理员

### 异步任务查询

大文件上传通常异步处理：

```bash
# 上传时记录返回的 pid
# {"status": "accepted", "pid": 12345}

# 查询任务状态
curl -sS "${ENDPOINT}/jobs/12345" -H "X-API-KEY: ${API_KEY}"
# running → 仍在处理
# completed → 处理完成，可以查询
# failed → 处理失败，检查错误信息
```

### VLM 相关问题

VLM（视觉语言模型）用于处理图片和 PDF 中的视觉内容。如果文档上传后 `/query` 无法回答图片中的内容：

- VLM 是 server 端配置（默认 qwen3-vl-plus），skill 端无法直接排查
- 联系后端管理员确认 VLM 模型是否正常工作
- 纯文本内容不依赖 VLM，如果文本查询正常但图片查询异常，大概率是 VLM 问题

## 批量入库问题

### 批量导入推荐流程

大规模入库前建议按此顺序执行，减少失败率：

1. `curl -sS "${ENDPOINT}/health"` — 确认服务可用
2. `curl -sS "${ENDPOINT}/ingest-memory/contract"` — 确认接口 schema
3. 用 1-3 条对象做 dry-run — 确认格式正确
4. 正式批量导入，建议加 `--probe --redact --resume`
5. 导入完成后统一 `/embed`
6. `/search` 验证

### 入库后搜索不到

- 确认已执行 `/embed` 刷新索引
- embed 大容器可能需要数分钟，使用 `background:true` + `/jobs/{pid}` 监控

### 脱敏不完整

`--redact` 覆盖常见模式（OpenAI/GitHub/AWS/Google/Slack/Telegram token、PEM 私钥、通用 key=value）。对于非标准敏感信息，建议在入库前自行预处理。

## 重置配置

如需重新配置：

```bash
rm -rf ~/.transcendence-memory
```

然后重新按 `references/setup.md` 操作。
