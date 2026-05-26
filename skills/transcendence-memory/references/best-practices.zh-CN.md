# 最佳实践

> English version: [`best-practices.md`](./best-practices.md)

本文档记录 transcendence-memory 在真实项目中沉淀出的使用模式与避坑指引。当 SKILL.md 与 troubleshooting.md 不能给出明确答案时,这里是判断基准。

---

## 1. 双路径模型：何时用 `/search`,何时用 `/query`

服务端有两条**完全独立**的数据通道,内容入哪条就只能从哪条召回,不会自动互通。

```
┌─────────────────────────────────────────────────┐
│           POST /ingest-memory/objects           │
│           POST /ingest-structured               │
│      (轻量路径 — Lightweight Path)              │
└────────────────────┬────────────────────────────┘
                     ↓
              LanceDB 向量索引
                     ↓
              POST /search
              (返回原文片段 + score)


┌─────────────────────────────────────────────────┐
│           POST /documents/text                  │
│           POST /documents/upload                │
│        (多模态路径 — RAG-Anything Path)         │
└────────────────────┬────────────────────────────┘
                     ↓
   实体抽取 + 关系推断 + LLM 索引（异步,20–60s）
                     ↓
              知识图谱 (Knowledge Graph)
                     ↓
              POST /query
        (返回 LLM 合成答案 + 引用)
```

### 1.1 决策树

| 你想要的 | 用什么入库 | 用什么召回 |
|---------|-----------|-----------|
| 翻原始笔记/代码片段/命令 | `/ingest-memory/objects` | `/search` |
| 让 LLM 综合多条记忆给一句话回答 | `/documents/text` | `/query` |
| 上传 PDF / 图片 / Markdown 文件 | `/documents/upload` | `/query` |
| 同时支持上述两种 | **跨路径双写** ↓ | `/search` 或 `/query` |

### 1.2 跨路径双写

如果一份知识既要支持精确翻原文,又要支持 LLM 综合答疑,要**写两遍**：

```bash
# 路径 1：写结构化对象供 /search
curl -sS -X POST "${ENDPOINT}/ingest-memory/objects" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","objects":[{"id":"recipe-1","title":"...","tags":[...],"text":"..."}],"auto_embed":true}'

# 路径 2：写长文本进图谱供 /query
DOC_TEXT=$(python3 -c "import json; print(json.dumps(open('/path/to/recipe.md').read()))")
curl -sS -X POST "${ENDPOINT}/documents/text" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container\":\"${CONTAINER}\",\"text\":${DOC_TEXT},\"description\":\"...\"}"
# /documents/text 入队即返回 job 标识（pid/job_id），知识图谱后台异步构建，不阻塞。
# 内容稍后才可被 /query 召回属正常；用 /tm jobs 查进度，失败由 SessionStart 静默提示。
```

> **常见误判**：只走路径 1 时 `/search` 立刻能召回,以为"完成了",几小时后用 `/query` 却得到"提供的知识库中没有相关信息"。这不是 bug,是路径隔离导致的。

---

## 2. 跨项目复用经验：建立专属容器

### 2.1 反模式 — 把所有东西塞默认容器

很多项目默认 container 是 `my-project`、`home` 这种通用名,日积月累塞进数千条对话备份/笔记。**新写入的精炼经验会被淹没在噪声里**:

- 实测:在 5000+ chunks 的 my-project 容器里写入 4 条 RN OTA 经验,用 "react native ota" 检索,top 5 全部是历史对话,新经验进不了 topk=10
- 同样 4 条放进新建的 mobile-recipes 容器(只有 4 条),top 1 score=0.475 直接命中

### 2.2 推荐模式 — 按主题建专属容器

为每个**可复用的、跨项目的知识主题**单独建容器,命名用 kebab-case 短名：

```
mobile-recipes      # RN 实战经验
ios-publishing-guides     # iOS 发版/审核
flutter-recipes           # Flutter 经验
auth-oidc-patterns        # 认证集成
docker-prod-checklist     # 生产 Docker 配置
strapi-cms-patterns       # Strapi CMS 设计
```

### 2.3 跨容器召回

存到专属容器后,在新项目里用以下命令调出来:

```bash
# 单容器精确检索
/tm search --match mobile-recipes "react native ota"

# 多容器模糊检索
/tm search --match recipes "ota"   # 命中所有 *-recipes 容器

# 全库
/tm search --all "react-native-ota-hot-update"
```

### 2.4 双轨 embedding 与默认 union 召回（v0.11.0+）

如果 server 同时跑**双轨 embedding**（如 gemini-3072 主轨 + `<container>_openai` 镜像走 text-embedding-3-small / 1024 dim），在 `profiles.yaml` 顶层设 `union_search_default: true`，普通 `/tm search my-container ...` 会**自动同时查两轨**，结果按 `(taskId, chunkId)` 去重合并，免费拿到跨轨召回。

```yaml
# config/profiles.yaml
union_search_default: true
```

触发时响应里 `union_applied: true`，`per_container_status` 同时列两个容器。若一轨超时（默认 3s），另一轨仍返回，整体 `degraded: true` — 不会因为一个慢镜像让整个查询失败。

按需关闭某次查询（如 eval 想拿单轨 baseline）：

```bash
/tm search "react native ota" --container my-container  # 走配置的默认行为
curl ... -d '{"container":"my-container","query":"X","union":false}'  # 强制单轨
```

### 2.5 何时迁移

如果发现某个主题在默认容器里被淹没,做一次性迁移:

1. 用 `/search --match <oldcontainer> <topic>` + 大 topk 把相关条目导出
2. 整理为 jsonl
3. `/tm batch <file>.jsonl --probe`,目标设为新容器
4. 同时通过 `/documents/text` 把整理后的 Markdown 入图谱

---

## 3. 索引与异步任务：预期时长

| 操作 | 容器规模 | 预期时长 |
|------|---------|---------|
| `/ingest-memory/objects` 写入 | 任意 | < 1s |
| `/embed` 同步, < 100 chunks | 小 | 5–30 秒 |
| `/embed` 同步, 100–1000 chunks | 中 | 30–120 秒 |
| `/embed` 同步, 1000+ chunks | 大 | **避免同步,改 background:true** |
| `/documents/text` 入队返回 job 标识 | 任意 | < 1s（仅"已入队"） |
| `/documents/text` 图谱可被 `/query` 召回 | 短文档 | 数十秒 |
| `/documents/text` 图谱可被 `/query` 召回 | 长文档（10KB+） | 数分钟 |

### 3.1 别同步 embed 大容器

实战观察到 `wait=true` 模式下 curl 长时间无任何输出,即使 `--max-time 240` 也只会得到空 body 和退出码 0。**不要在大容器上用 `wait=true`**,改异步:

```bash
RESP=$(curl -sS -X POST "${ENDPOINT}/embed" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","background":true}')
PID=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['pid'])")
echo "embed PID=$PID, 轮询..."
until ! curl -sS "${ENDPOINT}/jobs/${PID}" -H "X-API-KEY: ${API_KEY}" \
  | python3 -c "import json,sys; sys.exit(0 if json.load(sys.stdin).get('running') else 1)"; do
  sleep 5
done
```

### 3.2 `/documents/text` 是异步的 —— 别阻塞等建图

server v0.15.0+ 入队即返回 job 标识（`pid`）,知识图谱由后台 worker 构建。内容**不即时可查**——这是设计如此,不是 bug。**不要轮询、不要 sleep 等待**,让它后台建完即可,后续会话自动可召回。用 `/tm jobs` 查进度,失败由 SessionStart 静默提示。（旧版 `< v0.15.0` server 同步建图,可能超时——见 `troubleshooting.md`。）

---

## 4. 通用建议清单

### 4.1 入库

- 单条 < 5KB 的精炼经验 → `/ingest-memory/objects`,带 title/tags 便于召回
- 长文档（手册、设计稿、API 文档） → `/documents/text` 或 `/documents/upload`
- 大量条目（50+） → `/tm batch file.jsonl --probe --redact --resume`,完成后统一 `/embed`
- 含密钥/敏感信息 → 用 `--redact` 自动脱敏,或入库前手动过滤
- 同时要 `/search` 与 `/query` → 双写（见 §1.2）

### 4.2 检索

- 翻原文 → `/tm search "<query>"`,score 越小越相关（< 0.5 通常是强匹配）
- 要总结/答疑 → `/tm query "<question>"`,问题写得**具体**（含实体名、库名）
- 跨项目调取经验 → `/tm search --match <container-prefix> "<query>"`
- 不知道在哪个容器 → `/tm search --all "<query>"`,topk=20 浏览 hits

### 4.3 容器管理

- 一个主题一个容器(< 1000 chunks 单容器搜索体验最好)
- 默认容器(`my-project`/`home` 等)只放当前项目的临时记忆,不放长期可复用知识
- 周期性 `/tm containers` 检查容器列表,清理废弃容器(`DELETE /containers/{name}`)

### 4.4 配置

- `~/.transcendence-memory/config.toml` 的默认 container 是日常工作的"主容器",其它专属容器通过 `--match` / `containers[]` / `container_pattern` 显式访问
- 多机器协作时统一 `/tm connect <token>` 导入,不要手抄 endpoint/api_key

---

## 5. 实战回顾：近期遇到的具体问题

| 问题 | 根因 | 修复 / 改进位置 |
|------|------|-----------------|
| 写入 4 条 OTA 记忆后 `/query` 返回"无信息" | 双路径隔离,只入了 LanceDB 没入 KG | 加 `/documents/text` 双写 → §1.2 |
| 5000+ chunks 容器里新写入的少量记忆被淹没 | topk 排名靠后 | 改用专属容器 → §2.2 |
| `/jobs/{pid}` 轮询失败 (`status` 字段恒为 None) | 实际响应字段是 `running` 不是 `status` | api-reference.md 已更正 |
| `wait=true` 大容器 embed curl 无响应 | 同步模式不适合大容器 | 改 `background:true` → §3.1 |
| 入图谱后立即 query 返回"无信息" | 图谱构建是异步的 | 等 20–60 秒 → §3.2 |

如本表条目重新出现,优先参考已更新的 api-reference.md / troubleshooting.md;若发现新的反模式,追加到本文档。

---

## 6. Embedding/Reranker 选型与 dim 决策树（v0.7.0+）

### 6.1 何时新建 profile vs 何时复用 default

| 情景 | 建议 |
|------|------|
| 单一团队/项目,所有 container 内容性质相近 | 用 default route 1 个 profile,不要过度拆 |
| 不同 container 知识空间差异大(代码 vs 中文长文 vs 多语) | 按主题拆 profile,routes 用 glob 命中(如 `*_zh` / `*_code`) |
| 上游 quota 经常爆/单点不可靠 | 加 fallback 链(`embedding_fallbacks: [...]`,必须同 dim) |
| 要做 A/B 对比检索质量 | 双轨命名(`home` + `home_openai`),用 migrate 工具 clone 一份 |
| 调用方完全无法控制 container 名 | per-request 带 `embedding_model` override |

### 6.2 选 dim 的决策树

```
你写入的内容是?
├─ 主要中英文混合长文 → 3072 维(gemini-embedding-001 或 text-embedding-3-large)
│                       优点:语义保真度高,跨语言对齐好
│                       代价:LanceDB 占用 ~3×,latency p50 高 ~30%
├─ 短句/代码/标签结构化记忆 → 1024 维(text-embedding-3-small)
│                       优点:latency 低,磁盘小
│                       代价:对相似但措辞不同的语义召回略弱
└─ 长尾多语种(日韩阿拉伯等) → 优先 multilingual-e5-large 或 jina-v3
```

### 6.3 维度锁死铁律

**第一次写入一个 container,该 container 的 LanceDB vec 列就锁死该 dim 永久。**
后续:
- 同 dim profile 换模型 → 可以,但已有向量与新向量语义空间不同,搜索质量混乱
- 不同 dim profile 切换 → **直接抛 lance error: query dim X != column dim Y**
- 想换 dim → 必须用 **`scripts/migrate_embeddings.py`**(in-place 替换,旧表
  自动备份为 `chunks_old_<ts>`)或**双轨命名**(新建 `<container>_openai` clone)

### 6.4 双轨并运的命名约定

成熟项目用「主轨 default 3072 + 镜像轨 `*_openai` 1024」双写模式:

```bash
# 写入(双轨同步)
curl -sS -X POST "${ENDPOINT}/ingest-memory/objects" -H "X-API-KEY: ${API_KEY}" \
  -d '{"container":"home","objects":[...],"auto_embed":true}'
curl -sS -X POST "${ENDPOINT}/ingest-memory/objects" -H "X-API-KEY: ${API_KEY}" \
  -d '{"container":"home_openai","objects":[...],"auto_embed":true}'

# 检索(选模型)
curl -sS -X POST "${ENDPOINT}/search" -H "X-API-KEY: ${API_KEY}" \
  -d '{"container":"home","query":"..."}'           # 3072 高保真
curl -sS -X POST "${ENDPOINT}/search" -H "X-API-KEY: ${API_KEY}" \
  -d '{"container":"home_openai","query":"..."}'    # 1024 低延迟
```

### 6.5 Reranker 何时开

- **默认关**:routes 的 `rerank.enabled: false`。Reranker 把 query 延迟翻倍(~+500ms)
- **开启时机**:
  - 文档密度高(`/query` RAG 召回 top_k > 10,需要精排)
  - 跨语言检索(reranker 在语义对齐上比纯 vec 更准)
  - 业务关键搜索(用户搜不到会卡壳)
- **per-request 启用**:`/search` / `/query` 带 `"rerank": true`,无需改 routes

---

## 7. 结构化记忆编写工艺

未来召回该记忆的 agent 使用的是**模糊自然语言**，不是当初的 ASCII id。在写
高价值 memory 时按下面三层结构展开，能显著提升后续命中率。

### 7.1 标题同义词头部

> ❌ `[ASC + Play metadata fix @ project-a 1.0.1]`
> ✅ `[送审 / 上架 / 提审 · 商店元数据修正 @ 2026-05-26 project-a 1.0.1 实战]`

标题中至少包含 2-3 个同义词，覆盖中英常见说法（动词 + 实体 + 场景），让模
糊检索（"怎么送审"、"上架失败怎么办"）都能命中同一条记忆。

### 7.2 「何时召回我」章节

正文开头加一行 `When to recall me / 何时召回我`，明确列出召回触发面：

- **动词**：送审、提审、撤回、发版、回滚 / submit、release、rollback
- **实体**：应用名、模块名、子系统名（用占位名如 `your-project` /
  `team-alpha`，避免泄漏真实命名）
- **提问句式**：怎么做、出错怎么办、为什么 / how do I, what if it fails,
  why does X happen

这一行同时是给未来的自己留的"语义路标"——若 agent 检索时打到这行，就知道
落在正确的主题，再读详细内容。

### 7.3 双语冗余 Tags

每条 memory 同时打技术 id 与自然语言 tag，让两种检索路径都能命中：

```json
{
  "tags": ["asc", "release", "送审", "上架", "应用名称"]
}
```

技术 id 给精确召回（`tag=release`），自然语言 tag 给模糊召回与人工浏览。

---

## 8. 高密度索引卡设计

针对**反复回查的 SOP、流程、决策树**，单独创建一张「索引卡」memory，统一吸
收所有同义检索。

特征：

- 卡片标题囊括所有同义词
- 卡片正文是高关键词密度入口，逐步链接到详细 memory 的 id 或 chunkId
- 用来吸收模糊查询：命中卡片后顺藤摸瓜读详情

模板：

```text
[索引卡 · 部署 / Deploy / Release · 完整 SOP]

When to recall me: deploy 部署 launch 发版 上线 release 流程 ci/cd
回滚 rollback 端口冲突 docker compose

Steps:
1. ... (详见 mem-deploy-step1)
2. ... (详见 mem-deploy-step2)
...

Related memories: mem-deploy-step1, mem-deploy-rollback-sop, ...
```

经验值：每 50–100 条同类 memory 建一张索引卡，召回率会有显著拐点。索引卡
本身不可替代细粒度 memory，只是模糊查询的"目录页"。

---

## 9. 凭证脱敏 Checklist

写入 memory 之前，确认文本中**不含**：

- [ ] OpenAI / Anthropic / Stripe API key（`sk-...`、`pk_live_...`、`sk_live_...`）
- [ ] Slack / GitHub token（`xoxb-...`、`xoxp-...`、`ghp_...`、`gho_...`）
- [ ] AWS access key id（`AKIA...`）
- [ ] `Authorization: Bearer <token>`、JWT 三段式 token
- [ ] URL 内嵌的 `user:password`（如 `postgres://u:p@host`）
- [ ] PEM 私钥块（`-----BEGIN ... PRIVATE KEY-----`）
- [ ] `.env` 内的明文 secret 值

skill 的 PostToolUse + Stop hook 已经自动调用 `redact_secrets()`（见
[`hooks/common.sh`](../../../hooks/common.sh)），但**程序化批量入库时必须
自己 pipe 一次**，否则 secret 会直接落进向量库。

正确范例：

```bash
# 批量入库走 batch-ingest.py，加 --redact 即可
python3 scripts/batch-ingest.py "$ENDPOINT" "$API_KEY" "$CONTAINER" data.jsonl --redact

# 自定义脚本写入前，先 source common.sh 调用 redact_secrets
source hooks/common.sh
clean_text=$(printf '%s' "$raw_text" | redact_secrets)
```

如果发现历史 memory 已经混入 secret，按 [`retrofit-playbook.md`](./retrofit-playbook.md)
做事后清洗，不要直接对老库做覆盖写入。
