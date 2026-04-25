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
# 等 30 秒图谱构建完成
```

> **常见误判**：只走路径 1 时 `/search` 立刻能召回,以为"完成了",几小时后用 `/query` 却得到"提供的知识库中没有相关信息"。这不是 bug,是路径隔离导致的。

---

## 2. 跨项目复用经验：建立专属容器

### 2.1 反模式 — 把所有东西塞默认容器

很多项目默认 container 是 `yzjx`、`imac` 这种通用名,日积月累塞进数千条对话备份/笔记。**新写入的精炼经验会被淹没在噪声里**:

- 实测:在 5000+ chunks 的 yzjx 容器里写入 4 条 RN OTA 经验,用 "react native ota" 检索,top 5 全部是历史对话,新经验进不了 topk=10
- 同样 4 条放进新建的 react-native-recipes 容器(只有 4 条),top 1 score=0.475 直接命中

### 2.2 推荐模式 — 按主题建专属容器

为每个**可复用的、跨项目的知识主题**单独建容器,命名用 kebab-case 短名：

```
react-native-recipes      # RN 实战经验
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
/tm search --match react-native-recipes "react native ota"

# 多容器模糊检索
/tm search --match recipes "ota"   # 命中所有 *-recipes 容器

# 全库
/tm search --all "react-native-ota-hot-update"
```

### 2.4 何时迁移

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
| `/documents/text` HTTP 200 返回 | 任意 | < 1s（仅"已接收"） |
| `/documents/text` 图谱可被 `/query` 召回 | 短文档 | 20–40 秒 |
| `/documents/text` 图谱可被 `/query` 召回 | 长文档（10KB+） | 1–3 分钟 |

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

### 3.2 别立即 query

`/documents/text` 返回 200 不代表可以 query,这只是"已接收"。**先等 30 秒**,大文档则更久。如果脚本里要等待,加 sleep 或 monitor 探测。

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
- 默认容器(`yzjx`/`imac` 等)只放当前项目的临时记忆,不放长期可复用知识
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
