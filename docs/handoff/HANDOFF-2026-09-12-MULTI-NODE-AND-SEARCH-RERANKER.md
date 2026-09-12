# Transcendence Memory 阶段性研发落档与跨机研发交接文档 (SoT)

> **交接目标执行者**：aws-eva 节点上的 AI Agent (OpenAI Codex / Claude Code / Antigravity `agy`)  
> **交接发起方**：本机 Antigravity Agent  
> **归档时间**：2026-09-12  
> **代码工作区（本机）**：`/Users/zweiteng/github/transcendence-memory-workspace`  
> **远端执行环境（aws-eva）**：`aws-eva` (`ubuntu@3.147.7.207`, aarch64 Linux)

---

## 1. 任务背景与核心目标

本次交接包含两大核心主线：
1. **客户端技能多节点自适应升级（已完成落地并推送到远端）**：
   使 `transcendence-memory` 技能客户端能够**自动适配单服务节点与多服务节点集群**，在单节点配置下零冗余开销 100% 向后兼容；在多节点配置下支持网络故障/5xx 级自适应 Failover，并支持多客户端节点环境感知与 `--node` 标签溯源。
2. **服务端与记忆浏览器搜索缺陷修复与 Reranker 升级（aws-eva 待接手开发）**：
   用户在记忆浏览器（`https://rags.zweiteng.tk/admin/ui/memory`）中直接搜索记忆完整标题（如 `aws-eva 磁盘清理转存网盘与文件索引`）时，搜索结果中缺失目标记忆；需要修复该问题，并保证搜索结果经过 **Reranker** 重新排序后给出。

---

## 2. 客户端多节点自适应升级成果 (As-Is State)

### 2.1 变更清单与代码坐标
- **仓库路径**：`transcendence-memory/` (branch: `main`)
- **远端坐标**：`git@github.com:leekkk2/transcendence-memory.git`
- **已修改并验证的文件**：
  1. `skills/transcendence-memory/scripts/tm-remember.sh`：
     - 注入动态路由脚本钩子（`~/.transcendence-memory/project-route.sh` 或 `$TM_ROUTE_SCRIPT`）。
     - 支持解析 `endpoints = [...]` 或逗号分隔端点。
     - `http_post_json` 实现连接失败（curl 6/7/28）与 5xx 自动按候选列表 Failover 切换重试。
     - 增加客户端节点标识自动推断（`node:<hostname>`），支持 `--node <name>` 显式指定与 `--no-node` 单机纯净模式。
  2. `skills/transcendence-memory/scripts/tm-search.sh`：
     - `http_post_json`、`http_get`、`http_get_auth` 全套自适应 Failover。
     - `search` 新增 `-c|--container <name>` 参数与 `--union` / `--no-union` 参数。
     - `status` 升级支持遍历多端点健康状态汇总。
     - 新增 `node`（别名 `nodes`, `info`）子命令，输出当前客户端平台、网络端点与默认容器拓扑。
  3. `skills/transcendence-memory/SKILL.md`：
     - 补充 `§6. Multi-Node Resilience & Node Attribution` 规范。
     - 更新 Built-in Commands、Wrapper Script 用法与 Gotchas 表格。
  4. `skills/transcendence-memory/references/templates/config.toml.template`：
     - 补充 `endpoints = [...]` 多节点配置样例。
  5. `tests/test_client_contract.py`：
     - 新增多端点 Failover、`--container`、`--union` 与 `--node` 打标契约测试。全部 6 个测试 `Ran 6 tests in 2.443s -> OK`。

---

## 3. 记忆浏览器搜标题缺失与 Reranker 缺陷深入排查事实 (True State & Root Cause)

### 3.1 目标记忆客观事实核对
- **目标记忆完全存在**：
  - 容器：`main`
  - ID：`aws-eva-2026-09-20260911-324`
  - 标题：`aws-eva 磁盘清理转存网盘与文件索引 @ 2026-09-11 实战`
  - 标签：`backup, restore, rclone, gitlab, transcendence-memory, aws-eva, 备份, 恢复, 归档, 磁盘清理`
  - 正文详细记录了 2026-09-11 aws-eva 磁盘清理（98% 降至 71%，释放 39.3GB）的所有备份文件 SHA-256 哈希与 rclone 恢复命令。

### 3.2 为什么在记忆浏览器中搜标题找不到？
1. **纯向量检索局限性**：
   - 记忆浏览器（`dashboard/src/pages/Memory.tsx`）发起的请求是：
     `POST /search {"container": "main", "query": "aws-eva 磁盘清理转存网盘与文件索引", "topk": 20}`
   - 后端仅执行 LanceDB 向量相似度查询（Dense Vector Embedding）。由于历史记忆中包含大量提及 `eva`、`磁盘清理`、`claude-mem 迁移`、`dr-migration` 的技术卡片，向量模型计算出的 L2 距离在 0.71~0.84 之间，有超过 20 条其他记忆排在前面，导致精确包含该标题的目标记忆被挤出 top 20。
2. **Reranker 未激活 / 未生效**：
   - 真实 API 响应显示：`"rerank_applied": false`。
   - 在 `scripts/task_rag_server.py` 的 `search` 实现中，`_resolve_search_rerank` 依赖请求体中的 `req.rerank` 以及当前 profile 中是否配置并启用了 reranker。前端没有显式传递 `rerank: true`，且当前服务端环境可能未将 reranker 配置为全局默认或者 reranker 模型不可达。
3. **缺少标题精确匹配 / 混合检索 (Hybrid Search)**：
   - 用户输入完整的记忆标题时，期望精确匹配标题的记忆应该拥有最高的召回优先级。单纯依赖 Dense Embedding 很容易造成语义漂移或被高频关键词稀释，必须在检索链路中引入**标题精准优先/关键词 FTS/BM25 混合检索 + Reranker 重排序**。

---

## 4. aws-eva 接手 Agent 研发行动指南 (Next Steps)

### 4.1 服务端与记忆浏览器改造任务
1. **开启并完善 Reranker 排序**：
   - 检查 `transcendence-memory-server` 的 `config/profiles.yaml` 与环境变量中关于 `reranker` 的配置（如 `BAAI/bge-reranker-v2-m3` 或本地重排服务）。
   - 确保 `/search` 接口在 `req.rerank` 为 None 或默认情况下，如果配置了 Reranker 则自动执行 `_apply_search_rerank`，或者记忆浏览器请求时显式传递 `rerank: true`。
   - 确保返回结构包含通过 reranker 重新打分排序的列表（`rerankScore` 从大到小降序）。
2. **支持标题精准提升或混合检索 (Title Boost / Hybrid Retrieval)**：
   - 在 `_run_single_search` 或 `search` 编排中，增加对 `title` 字段的精准/前缀/模糊匹配加权（Title Boost），如果查询词与记忆标题高度重合，确保其进入重排候选集（Candidate Pool），再由 Reranker 给出最终排序。
3. **前端记忆浏览器适配 (`dashboard/src/pages/Memory.tsx`)**：
   - 前端搜索请求可支持携带 `rerank: true`；
   - 优化卡片展示，清晰呈现 `rerankScore` 与相关性指示。

---

## 5. 凭证、主机与工作区拓扑

- **主机别名**：`aws-eva`（SSH: `ssh aws-eva` 或 `ssh ubuntu@evashell.zweiteng.tk`）
- **公网 IP**：`3.147.7.207`
- **工作区规划目录**：`/home/ubuntu/workspace/transcendence-memory-workspace`
  - `transcendence-memory/`（客户端技能仓库）
  - `transcendence-memory-server/`（服务端仓库）
- **AI Agent 规范**：已同步 `AGENTS.md` / `CLAUDE.md` / `GEMINI.md` 规则体系。
