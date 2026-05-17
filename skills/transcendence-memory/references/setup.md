# 首次配置指南 / First-Time Setup

> 本文件仅在首次使用时需要。配置完成后可归档，不再加载到上下文中。

---

## 方式一：Connection Token 导入（推荐）

### 获取 Token

从 server 端获取连接令牌：

```bash
# 从 server 端点获取（需要管理员权限）
curl -sS "${ENDPOINT}/export-connection-token?container=${CONTAINER}" \
  -H "X-API-KEY: ${API_KEY}"
# 返回: {"token": "eyJlbmRwb2ludCI6Imh0dHBz..."}
```

或由后端管理员直接提供 token。Token 是一个 base64 编码的 JSON 字符串，形如：
```
eyJlbmRwb2ludCI6Imh0dHBzOi8vcmFnLmV4YW1wbGUuY29tIiwiYXBpX2tleSI6InNrLXh4eCIsImNvbnRhaW5lciI6ImhvbWUifQ==
```

### 导入步骤

1. **解码 token**：
```bash
echo '<token>' | base64 -d
# 输出: {"endpoint":"https://rag.example.com","api_key":"sk-xxx","container":"home"}
```

2. **创建配置目录**：
```bash
mkdir -p ~/.transcendence-memory && chmod 700 ~/.transcendence-memory
```

3. **写入配置文件**（用解码后的值替换）：
```bash
cat > ~/.transcendence-memory/config.toml << 'EOF'
[connection]
endpoint = "https://rag.example.com"
container = "home"

[auth]
mode = "api_key"
api_key = "sk-xxx"
EOF
chmod 600 ~/.transcendence-memory/config.toml
```

4. **验证连接**：
```bash
curl -sS "https://rag.example.com/health"
```

预期：HTTP 200 且 `runtime_ready: true`。

5. **验证鉴权**：
```bash
curl -sS -X POST "https://rag.example.com/search" \
  -H "X-API-KEY: sk-xxx" -H "Content-Type: application/json" \
  -d '{"container":"home","query":"test","topk":3}'
```

预期：HTTP 200（新 container 可能返回空结果，这正常）。

**配置完成。** 回到 SKILL.md 的 Quick Start 即可开始使用。

---

## 方式二：手动配置

如果没有 connection token，手动收集以下信息：

| 信息 | 说明 | 示例 |
|------|------|------|
| endpoint | 后端服务地址 | `https://rag.example.com` |
| api_key | 后端 API 密钥 | `sk-xxx` |
| container | 你的命名空间 | `home`、`work`、`lab` |

然后按方式一的步骤 2-5 操作，手动填入值。

---

## 方式三：使用可选 CLI 工具

如果偏好命令行工具：

```bash
pip install transcendence-memory
transcendence-memory init frontend --yes
transcendence-memory frontend import-token <base64-token>
transcendence-memory frontend smoke
```

CLI 是可选的，安装需要 Python >= 3.13。

---

## 配置检查

### Skill 端（本地）

配置文件位于 `~/.transcendence-memory/config.toml`：

```toml
[connection]
endpoint = "https://rag.example.com"   # 后端地址
container = "home"                       # 命名空间

[auth]
mode = "api_key"                         # 鉴权模式
api_key = "sk-xxx"                       # API 密钥
```

完整模板见 `templates/config.toml.template`。

### Server 端（无需 skill 端配置）

以下模型均在 server 端配置，skill 端用户**无需关注**：

| 模型用途 | 默认模型 | 说明 |
|---------|---------|------|
| Embedding (default) | gemini-embedding-001 (dim=3072) | 文本向量化（双轨默认）|
| Embedding (alt) | text-embedding-3-small (dim=1024) | `*_openai` 命名的 container 走这条 |
| LLM | gemini-2.5-flash | `/query` 生成答案 |
| VLM | qwen3-vl-plus | 图片/PDF 视觉理解 |

LLM/VLM 仍由 `.env` 中 `LLM_MODEL` / `LLM_BASE_URL` / `VLM_*` 变量驱动；
embedding/reranker 自 v0.7.0+ 改由 `config/profiles.yaml` + routes 表声明式管理。

### Server 端 Multi-Embedding 配置（v0.7.0+，可选）

如部署多个 embedding profile（如 default Gemini + fallback OpenAI），在
server 端编辑 `config/profiles.yaml`（路径可由 `TM_PROFILES_FILE` env 覆盖）：

```yaml
version: 1
embeddings:
  - name: gemini-3072            # 主路径
    provider: openai_compatible
    model: gemini-embedding-001
    dim: 3072
    base_url: https://newapi.example.com/v1
    api_key_env: EMBEDDING_API_KEY    # ← 间接引用，yaml 不存 secret
    max_token_size: 8192
  - name: openai-small-1024       # 备/对比/双轨
    provider: openai_compatible
    model: text-embedding-3-small
    dim: 1024
    base_url: https://newapi.example.com/v1
    api_key_env: EMBEDDING_API_KEY
rerankers:
  - name: selfhosted-bge
    provider: cohere_compatible
    model: text-reranker
    base_url: https://newapi.example.com/v1
    api_key_env: EMBEDDING_API_KEY
routes:
  - match: {glob: "*_openai"}     # 镜像 container 命名约定
    embedding: openai-small-1024
  - match: {default: true}
    embedding: gemini-3072
    reranker: selfhosted-bge
    rerank: {enabled: false}      # per-call 启用
```

**重要**：`api_key_env` 是间接引用，实际密钥写在 docker-compose `.env` /
systemd EnvironmentFile，**yaml 永远不直接含 secret**。

> 💡 **shared vs per-profile key**：上例两个 profile 复用同一个 `EMBEDDING_API_KEY`（首次配置最简，与 eva 生产一致）。**生产推荐 per-profile key 隔离 quota** —— 比如 `gemini-3072` 用 `GEMINI_API_KEY`，`openai-small-1024` 用 `OPENAI_API_KEY`，避免一个 profile 触发 rate limit 时拖累另一个；server 内置 `config/profiles.yaml.example` 用的就是 per-profile 命名。

验证 server 已加载：
```bash
curl -sS -H "X-API-KEY: ${API_KEY}" "${ENDPOINT}/admin/profiles" | jq '.embeddings[].name, .routes[].match'
# 探活单条 profile（latency + 实测 dim）
curl -sS -X POST -H "X-API-KEY: ${API_KEY}" "${ENDPOINT}/admin/probe-embedding?profile=openai-small-1024"
# {"ok": true, "profile": "openai-small-1024", "latency_ms": 885, "dim": 1024, "breaker_reset": false}
```

**无 profiles.yaml 时**：server 自动合成 legacy profile 走 v0.6.x 单 embedding 行为，
完全向后兼容旧 `.env` 部署。

### 安全说明

- 配置文件权限应为 600（仅当前用户可读写）
- API key 存储在本地文件中，不会被上传或分享
- Connection token 是一次性的传输载体，导入后 token 本身可以丢弃
- 配置文件中不应包含 OAuth refresh token 等长期凭证

---

## 验证清单

配置完成后，依次验证：

| 步骤 | 命令 | 预期 |
|------|------|------|
| 健康检查 | `curl -sS "${ENDPOINT}/health"` | 200 + `runtime_ready: true` |
| 搜索测试 | `curl -sS -X POST "${ENDPOINT}/search" -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" -d '{"container":"${CONTAINER}","query":"test","topk":3}'` | 200（空结果正常） |
| 索引重建 | `curl -sS -X POST "${ENDPOINT}/embed" -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" -d '{"container":"${CONTAINER}","background":false,"wait":true}'` | 200 + success |
| 容器列表 | `curl -sS "${ENDPOINT}/containers" -H "X-API-KEY: ${API_KEY}"` | 200 + 包含你的容器 |

全部通过后，配置完成。**本文件可以归档，后续使用只需 SKILL.md。**
