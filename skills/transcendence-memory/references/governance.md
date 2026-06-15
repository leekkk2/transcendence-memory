# Governance Framework (server v0.20 → v0.21.0)

> 服务端 v0.20 引入的「自治记忆治理」子系统总览：**治理工具箱**（6 工具）+ **梦境子系统**（dreaming）+ **治理编排 Agent**（LLM tool-use 循环 + 人工审批）。**v0.21.0** 给 `compress_knowledge_cluster` 加了**幂等 4 态**（§2.2）与**批预算默认 256 KiB**（§2 末）。
> 全部端点都在 `/admin/*` 下、走统一鉴权（`X-API-KEY` / `Authorization: Bearer` / cookie session），默认**安全态**——一个全新部署不会自动改任何数据。
>
> 端点完整请求/响应 spec 见 [`api-reference.md`](./api-reference.md) §治理与梦境端点；命令速查见 [`commands.md`](./commands.md) §治理 / 梦境。
> 本文用占位符 `https://your-tm-host`（或 `http://localhost:8711`）代表你自己的 endpoint —— 真值在本地 `~/.transcendence-memory/config.toml`。

---

## 0. 一句话心智模型

服务端不再只是被动的 RAG 检索后端：v0.20 起它能（在你显式开闸后）**自己整理自己的记忆**——压缩同主题记忆成索引卡、隔离低价值/异常记忆、按检索质量调参、夜间梦境周期清理。所有这些动作都遵循同一条安全骨架：

> **dry-run-first（默认只产计划）→ 可逆动作需显式放行 → 破坏性动作永远只进人工审批队列，由人在审批端点充当唯一执行器。**

无人值守的循环**永远不会**自己跑破坏性删除。

---

## 1. 三层结构

```
                ┌────────────────────────────────────────────┐
                │  治理编排 Agent (/admin/agent/*)             │
                │  网关 LLM tool-use 循环（opt-in，默认 OFF）   │
                │  规划 → 调工具 → 留痕 → 破坏性动作进审批队列  │
                └───────────────┬────────────────────────────┘
                                │ 调用
                ┌───────────────▼────────────────────────────┐
                │  治理工具箱 (/admin/tools/*)                 │
                │  6 个预设工具，SAFE / LLM / 破坏性 三档       │
                │  dry-run-by-default + 容器级/全局开关         │
                └───────────────┬────────────────────────────┘
                                │ 复用同一套工具
                ┌───────────────▼────────────────────────────┐
                │  梦境子系统 (/admin/dreaming/*)              │
                │  后台调度 + 手动触发的记忆整理周期            │
                │  report-only 默认；破坏性删除二次守护         │
                └─────────────────────────────────────────────┘
```

三者共享一个**隔离的治理存储**（governance store）：agent run 账目、每步轨迹、待审批队列、梦境报告都写在这里，**结构上与用户 RAG 语料分离**（`excluded_from_rag: true`）——治理元数据永不污染检索结果。

---

## 2. 治理工具箱（6 工具 · 三档风险）

`GET /admin/tools` 返回矩阵：全局开关表 + 沙箱内存上限 + 审批有效期 + 各容器 resolved/raw 开关。`POST /admin/tools/{tool}/invoke` 执行单个工具。

| 工具 | scope | 风险档 | dry_run=true（默认） | dry_run=false（显式） |
|---|---|---|---|---|
| `manage_token_quotas` | global | **SAFE**（只读） | 真执行（dry_run 对 SAFE 是 no-op） | 同左 |
| `analyze_retrieval_latency` | container | **SAFE**（只读） | 真执行 | 同左 |
| `update_container_routing` | container | **SAFE**（加性写） | 预览合并后的 routing blob，不落盘 | 经 config_store 加性合并写入（保留已有项） |
| `compress_knowledge_cluster` | container | **LLM**（幂等附加式） | 产 plan 预览（聚类哪个簇 + 簇内来源 + **4 态决策预告**，不调 LLM） | 幂等 4 态（见 §2.2）：未变更 skip 零 LLM / 无卡建首卡 / 多孤儿廉价合并零 LLM / 内容变更重总结取代旧卡。**附加不删源**，退役走可逆快照 |
| `tune_model_parameters` | container | **LLM**（护栏写） | 预览将喂给 LLM 的信号 + 当前参数 + 护栏边界 | LLM 评估检索质量 → allow-list + 范围护栏内经 config_store 加性调参 |
| `snapshot_and_quarantine` | container | **破坏性（可逆）** | 产隔离计划预览 | 全量快照 + 隔离低价值/异常记忆到隔离文件，**零硬删**（可逆） |

风险分档语义：

- **SAFE**：既不破坏性也不需要 LLM。`update_container_routing` 是加性写但归入 SAFE「总是执行」——不会丢已有路由项。三个 SAFE 工具**总是真执行**，dry_run 对它们是无意义的（仍会用 dry_run 产出预览以保持接口一致，但读路径/加性写不改变检索输出）。
- **LLM**：`compress_knowledge_cluster` / `tune_model_parameters`。需要网关 LLM。默认 dry_run 只产**可执行预览**（真实 plan，不是参数回声），显式 `dry_run=false` 才真执行。所有 LLM 调用经 `rag_engine` 网关（HR-9：env 驱动 `LLM_*`，不硬编码任何 provider / model / base_url / key）。
- **破坏性**：仅 `snapshot_and_quarantine`。**可逆**——隔离 = 快照 + 移到隔离文件，从不硬删。即便如此，在 agent 循环里它**永远不自动执行**，只记一条 pending 审批；唯一真执行入口是 `/admin/agent/approvals/{id}/approve`（人工）。

> 大簇分批：`compress_knowledge_cluster` 对超大簇会按字节预算分批（`config:agent:compress_batch_bytes` / `TM_COMPRESS_BATCH_BYTES`，**默认 256 KiB（262144 B）**），每批送 LLM 前再 `_truncate_for_llm` 兜底，避免 request-too-large。早期版本曾对大簇返回 400，现已 map-reduce 分批修复。
> **为何 256 KiB 而非旧值 8 MiB**：用真实混合 CJK+Latin 簇内容直探网关实测——768 KiB(786432 B) 返 200 OK、1 MiB(1048576 B) 返 HTTP 400 `context_too_large`（瓶颈是小模型 token context window，不是 transport 字节上限）；CJK UTF-8 约 1.5 字节/token、纯 ASCII 约 4 字节/token，按字节估算会严重高估真实 CJK 内容能塞的量，故对 768 KiB 留 ~3× 余量取 256 KiB 为安全默认，给 system prompt + 输出 token 留余量。治理操作低频，大簇多分几批可接受；接大 context 模型可经 `TM_COMPRESS_BATCH_BYTES` 调高。

### 2.1 开关解析（容器覆盖 > 全局）

某工具对某容器是否启用，解析顺序（每步降级安全）：

1. 该容器有 per-container `enabled_map` 覆盖且点名了这个工具 → 以覆盖为准。
2. 否则看全局 `config:tools:global_enabled_map`（默认所有预设工具 ON）。
3. 工具不在全局表里（如未来新工具）→ `config:tools:new_tool_default_enabled`（默认 **false**，更安全）。

global-scope 工具（`manage_token_quotas`）忽略容器维度。改开关走 `PUT /admin/config`（写 `config:tools:global_enabled_map` 或动态键 `config:tools:container:{c}:enabled_map`），**不旁路** config_store 校验。

### 2.2 compress 幂等 4 态（v0.21.0 头号特性）

`compress_knowledge_cluster` 不再「无脑追加新卡」——它据**簇指纹**（`cluster_fingerprint` = 对排序后 `source_ids` + 内容/时间摘要确定性派生；源增删或源被原地编辑都会变指纹）与该簇已有的索引卡比对，自动落到下列四态之一。决策由纯函数 `_compress_decision` 算出，**dry_run 预览与真执行共用同一决策**（所见即所得，`result.decision` / plan 里直接预告会走哪态）：

| action（`result.action`） | 触发条件 | 调 LLM？ | 写新卡？ | 退役旧卡？ | 顶层 `status` | `reindex_required` |
|---|---|---|---|---|---|---|
| `first_card` | 该簇无既有索引卡（无 prior） | ✅ 是 | ✅ 建首卡 | — | `applied` | `true` |
| `skipped_unchanged` | 恰一张 prior 且其指纹 == 本次指纹（源/内容都没变） | ❌ 否 | ❌ 否 | ❌ 否 | **`ok`**（非 `skipped_unchanged`） | `false` |
| `consolidated` | prior ≥2 张，其中一张指纹匹配本次（内容没变，其余是历史孤儿/近重复卡，按 `source_ids` Jaccard≥0.5 兜底匹配上）→ 廉价合并 | ❌ 否 | ❌ 保留匹配卡 | ✅ 退役多余孤儿 | `applied` | `false` |
| `superseded` | 有 prior 但无一张指纹匹配（簇内容变了）→ 重新 summarize | ✅ 是 | ✅ 新卡 | ✅ 退役全部 prior | `applied` | `true` |

> ⚠️ **`status` ≠ `action`**：skip 路径的**顶层 `status` 是 `ok`**（`ToolInvokeResponse.status` 是受限枚举，`skipped_unchanged` 不在其中会令响应校验 500）；「跳过」语义只由 **`result.action='skipped_unchanged'`** 表达。同理 supersede 路径 `result.action='superseded'`、consolidate 路径 `result.action='consolidated'`。

退役**永不硬删**：被取代/合并掉的旧卡移出 active 主文件（退出 search/embed），写入 `governance/superseded-cards-<ts>.jsonl` 可逆快照（带 `metadata.status='superseded'` + `superseded_by`），任何时刻可回滚。源记忆始终保留。

三条不变量值得背下：

- **append-only + 可逆**：从不硬删——新卡追加、旧卡进 governance 快照，源永不动。
- **幂等**：无数据变更（指纹一致）→ `skipped_unchanged`，**零 LLM、零新卡**，解决早期「无变更反复 compress 不断叠加近重复卡」的问题。
- **终态唯一**：无论历史堆过多少孤儿卡，consolidate/supersede 后该簇恒只剩一张 active 当前卡。

幂等/取代默认开启（`config:agent:compress_idempotent` / `config:agent:compress_supersede`，或 env `TM_COMPRESS_IDEMPOTENT` / `TM_COMPRESS_SUPERSEDE`，默认 `true`）；两者都置 `false` 可灰度回退到旧「无脑追加」语义。

---

## 3. 梦境子系统（dreaming）

后台/手动的「记忆整理周期」。`GET /admin/dreaming/status` 看状态，`POST /admin/dreaming/trigger` 手动触发一次。

- **总闸** `config:dreaming:global_enabled`（默认 **true**，但仅在调度开启或被手动触发时才动）。
- **后台调度** `config:dreaming:scheduler_enabled`（默认 **false** = 不自动跑）；`config:dreaming:trigger_cron`（默认 `0 2 * * *` 每日凌晨 2 点）。调度器在 lifespan 接线，但开关不开就不跑——**全新部署零自治行为**。
- **批处理模型** `config:dreaming:batch_model`（状态字段，经网关可配置；**不硬编码具体模型**）。**注意**：P6 梦境本身 **report-only、不直接调用任何模型**（见 `dreaming.py` 注释 "P6 dreaming is report-only and does NOT call any model"）——它只产候选报告，索引卡压缩等真需 LLM 蒸馏的动作 defer 给治理工具箱（`compress_knowledge_cluster`，走网关配置的模型）。故 `batch_model` 仅作状态/未来用途字段，当前梦境周期不据它发起任何 LLM 调用。
- **破坏性二次守护**：`trigger` 的 `dry_run` 默认 **true**（仅产候选报告，不删）。即便传 `dry_run=false`，真删除**仍**受 `config:dreaming:prune_apply`（默认 **false**）二次守护——所以单凭一个请求体无法删数据。
- **剪枝信号**：`config:dreaming:prune_threshold`（默认 0.3，价值评分低于此入候选）、`config:dreaming:graph_prune_enabled`（默认 true，图谱孤点纳入候选）、`config:dreaming:cache_threshold`（默认 10 次访问入高频缓存）。
- **报告隔离**：`DreamReport.excluded_from_rag` 恒 true；`status` ∈ `ok` / `skipped_global_disabled`（总闸关时返回后者、不执行）。

---

## 4. 治理编排 Agent（LLM tool-use 循环）

`/admin/agent/*`。一个**通用 LLM tool-use 循环**：网关 LLM 选调哪个治理工具 → `invoke_tool` 执行 → governance_store 留痕 → 静态安全闸（`decide`）执行自治策略。它自身**不拥有任何执行原语**——所有副作用都流经 `invoke_tool`（本身 dry-run-by-default + 降级不抛）。

### 4.1 总开关（默认 OFF）

`TM_AGENT_ORCHESTRATION_ENABLED`（env，默认 `0`）。关闭时 `/admin/agent/{name}/invoke` 返回 `status:"disabled"` 不入队——**默认部署完全不受影响**（不入队、不影响 ingestion）。设 `1` 才允许 `/admin/agent` 入队。

### 4.2 自治策略（安全闸 `decide`）

| 工具类别 | 循环内行为 |
|---|---|
| SAFE 只读（`manage_token_quotas` / `analyze_retrieval_latency`） | 总是真执行（dry_run 对它们 no-op） |
| 可逆（`compress_knowledge_cluster` / `update_container_routing` / `tune_model_parameters`） | **仅当** `allow_apply=true` 时真执行；否则停在 dry-run（plan/preview） |
| 破坏性（`snapshot_and_quarantine`） | **永不**在循环里自动执行——模型若请求 apply，记一条 pending 审批后循环继续。人，通过审批端点，是唯一执行器 |

**apply 权限 = `dry_run=false` AND `allow_apply=true` 两个闸都开**。任一留默认安全值，整个 run 都停在 plan 模式。破坏性工具即便两闸全开也只进审批队列。

### 4.3 边界与安全

- **HR-9**：每次 LLM 调用经 `rag_engine.llm_chat_with_tools`（env 驱动 `LLM_*` 网关），不硬编码 provider/model/base_url/key。
- **有界**：硬步数上限 `config:agent:max_steps`（默认 6，env `TM_AGENT_MAX_STEPS`）；墙钟上限 `config:agent:run_timeout_sec`（默认 300s，env `TM_AGENT_RUN_TIMEOUT_SEC`，超时产部分报告并出局，无 traceback）；可选每日 token 预算 `TM_AGENT_DAILY_TOKEN_BUDGET`。每个工具结果回填 prompt 前都经 `_truncate_for_llm` 截断，防超大 payload 再触发 request-too-large。
- **降级不抛**：`run_agent` 从不向调用方抛异常；网关/存储故障会以降级状态 + 部分轨迹收尾。
- **通用 prompt**：system prompt 不含任何真实 container/host/domain/model 名；工作容器始终作为参数传入（R8）。
- **白名单** `config:agent:allowed_tools`（默认仅非破坏性工具）；默认 agent 名 `config:agent:default_agent_name`（默认 `dream-orchestrator`）。

### 4.4 运行生命周期

1. `POST /admin/agent/{name}/invoke` → 铸 `run_id`（`agentrun-<hex>-<ts>`）→ 原子写 run params 到 per-container inbox 文件 → 入队 `op='run-agent'` job → 记 run head → 返回 `{run_id, job_id, status:"enqueued"}`。
2. 后台 worker 把 job 解析到 `governance_agent_runner`（CLI 子进程），构建 `AgentConfig`（`config:agent:*` / `TM_AGENT_*`，env 优先），跑 `run_agent` 循环。
3. run 账目（`agent_runs` head、每步 trace、pending approvals）全写在 governance_store。`GET /admin/agent/runs` 看历史，`GET /admin/agent/approvals` 看待审批。
4. 破坏性提案停在 pending → 人 `POST /admin/agent/approvals/{id}/approve`（真执行，唯一破坏性入口）或 `/reject`（不执行）。审批有 TTL（`config:tools:approval_ttl_days`，默认 30 天），过期 pending 被存储层隐藏。

---

## 5. 配置键速查（全经 `PUT /admin/config` 热重载）

| 键 | 类型 | 默认 | 含义 |
|---|---|---|---|
| `config:dreaming:global_enabled` | bool | `true` | 梦境系统总开关 |
| `config:dreaming:scheduler_enabled` | bool | `false` | 后台自动调度（默认不自动跑） |
| `config:dreaming:trigger_cron` | str | `0 2 * * *` | 调度 cron |
| `config:dreaming:batch_model` | str | （网关配置的模型） | 批处理模型状态字段（经网关可配置，不硬编码）；P6 梦境 report-only 不直接调它，真需 LLM 时 defer 给 compress |
| `config:dreaming:prune_apply` | bool | `false` | 破坏性删除是否真生效（二次守护） |
| `config:dreaming:prune_threshold` | float | `0.3` | 低价值剪枝阈值 |
| `config:dreaming:graph_prune_enabled` | bool | `true` | 图谱孤点纳入候选 |
| `config:dreaming:cache_threshold` | int | `10` | 高频缓存阈值（访问次数） |
| `config:tools:global_enabled_map` | json | 全 ON | 工具全局开关表 |
| `config:tools:container:{c}:enabled_map` | json | （动态键，未配 = 继承全局） | 容器级工具开关覆盖 |
| `config:tools:sandbox_mem_limit` | str | `512m` | 工具沙箱内存上限 |
| `config:tools:approval_ttl_days` | int | `30` | 审批有效期（天） |
| `config:tools:new_tool_default_enabled` | bool | `false` | 新工具默认启用 |
| `config:agent:allowed_tools` | json | 仅非破坏性 | Agent 可用工具白名单 |
| `config:agent:max_steps` | int | `6` | 单次最大步数 |
| `config:agent:run_timeout_sec` | int | `300` | 运行墙钟上限（秒） |
| `config:agent:default_agent_name` | str | `dream-orchestrator` | 默认 Agent 名 |
| `config:agent:compress_batch_bytes` | int | `262144`（256 KiB） | compress 单批 prompt UTF-8 字节预算（见 §2 末；env `TM_COMPRESS_BATCH_BYTES` 优先） |
| `config:agent:compress_row_char_cap` | int | `20000` | compress 单条源记忆截断字符上限 |
| `config:agent:compress_idempotent` | bool | `true` | 指纹未变跳过 compress（§2.2 `skipped_unchanged`）；置 false 退旧追加（env `TM_COMPRESS_IDEMPOTENT`） |
| `config:agent:compress_supersede` | bool | `true` | 簇变更时取代退役旧卡（§2.2 `superseded`/`consolidated`）；置 false 退旧追加（env `TM_COMPRESS_SUPERSEDE`） |

> env 覆写（`TM_AGENT_*` 系列）优先于 `config:agent:*`，见 [SKILL.md](../SKILL.md) §env 说明 + [`api-reference.md`](./api-reference.md)。`config:agent:compress_batch_bytes` / `config:agent:compress_row_char_cap` 控制 compress 分批字节/单行字符上限（env `TM_COMPRESS_BATCH_BYTES` 优先于配置键）；`config:agent:compress_idempotent` / `config:agent:compress_supersede`（env `TM_COMPRESS_IDEMPOTENT` / `TM_COMPRESS_SUPERSEDE`）控制 §2.2 幂等 4 态。

---

## 6. 安全模型小结（背下这四条）

1. **默认全关/全只读**：调度 OFF、agent 编排 OFF、`prune_apply` OFF、`new_tool_default_enabled` OFF —— 全新部署不自动改任何数据。
2. **dry-run-first**：所有写/破坏性动作默认 `dry_run=true` 只产 plan。
3. **可逆动作双闸**：`dry_run=false` AND `allow_apply=true` 才落地。
4. **破坏性动作人工背书**：`snapshot_and_quarantine` 永远只进审批队列，人在 `/approve` 端点是唯一执行器；且它本身可逆（快照 + 隔离，零硬删）。
