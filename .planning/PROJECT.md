# Transcendence Memory

## What This Is

Transcendence Memory 是一个面向 OpenClaw 的开源记忆 operator 项目，包含一个**去敏后的通用 skill pack**、可开源的 backend 服务与 CLI、部署脚本，以及面向用户和 AI 的配置与运维文档。目标不是再讲“迁移兼容故事”，而是把真正可公开、可部署、可验证的前后端工作流直接沉淀成当前仓库的 canonical surface。

项目面向需要在单机或前后端分机环境中启用记忆检索能力的 OpenClaw 用户。文档采用中英双语、中文为主，README 明确说明其受 `memory-lancedb-pro` 启发，同时 skill 与 runbook 直接服务于配置、部署、验证与修复。

## Core Value

用户可以通过公开仓库中的 skill、CLI、backend 与 runbook，以安全、可配置、可验证的方式完成记忆后端部署与前端接入，而且整个过程不会把敏感信息硬编码进仓库。

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] 提供一个符合 OpenClaw 最佳实践的 skill 包，使用 `SKILL.md` 作为入口，并把 setup / architecture / dataflow / operations / vetting 文档组织为可直接被 AI 引用的公共文档面。
- [ ] 提供可开源的 backend 服务与部署脚本，由 skill、CLI 和 runbook 协同引导用户完成 `backend` 或 `frontend` 的安装、配置、连接与验证。
- [ ] 支持 Linux、macOS、Windows，并支持“单机前后端同机部署”与“前后端分机部署”两种拓扑。
- [ ] 提供 CLI，至少覆盖 `init/config`、`provider set`、`auth login/status/logout`、`backend deploy/health`、`frontend check/smoke`、`backend export-connection`、`frontend import-connection`。
- [ ] 支持 `apiKey + OAuth` 两种 v1 鉴权方式，并允许配置 provider、model、base URL、API key 等参数。
- [ ] 在分机部署场景中，由 backend 侧生成一个可复制的 redacted connection bundle，仅包含非敏感连接信息；敏感信息保存在本机安全路径。
- [ ] 所有敏感信息、私有地址、内部凭据、历史内部部署细节都不直接出现在仓库中，只保留模板、占位符和公共 runbook。
- [ ] README 与项目文档采用中英双语、中文为主，并在 README 中明确引用 `memory-lancedb-pro` 作为启发来源之一。

### Out of Scope

- 自动旧数据迁移/导入能力
- 多节点/高可用集群部署
- Web 管理后台
- `apiKey + OAuth` 之外的更多鉴权模式
- 让 skill 自身直接承载 backend runtime 能力

## Context

当前仓库要做的不是“给一个尚未发布的产品补迁移兼容说明”，而是把内部原型中真正有价值的 operator 形状整理为**当前仓库自己的公开主文档面**。换句话说：`transcendence-memory/` 下的 skill 就是当前产品的 canonical public skill，仓库根下的 `docs/`、`deploy/`、`src/` 共同构成其可部署、可验证的执行面。

实现上需要同时满足两类参考约束：
1. OpenClaw `skill-creator` 风格的技能组织方式：`SKILL.md` 保持精炼，详尽内容拆到 `references/` 和示例文件中。
2. `memory-lancedb-pro` 所体现的可配置化、CLI 化经验：provider、auth、deploy、health、handoff 必须是显式的 operator 工作流。

## Constraints

- **Security**: 公共仓库中不得包含真实密钥、私有域名凭据、内部网络细节或其他敏感信息。
- **OpenClaw Packaging**: skill 目录结构必须符合 OpenClaw 技能最佳实践。
- **Topology Support**: 必须同时支持同机部署与分机部署。
- **Platform Support**: 必须覆盖 Linux、macOS、Windows。
- **Deployment UX**: 推荐采用“环境探测 → 计划展示 → 用户确认 → 执行 → 验证”的引导式自动化。
- **Auth Scope**: v1 只做 `apiKey + OAuth`。
- **Documentation**: 文档必须中英双语、中文为主。
- **License**: 项目采用 MIT License。

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| `transcendence-memory/` 下的 skill 就是当前 canonical public skill | 避免继续把产品写成“迁移说明层” | Accepted |
| skill 负责引导、编排、部署、配置和验证，而不是直接内嵌 backend 能力 | 保持职责清晰，符合前后端分离与 OpenClaw skill 最佳实践 | Accepted |
| skill 包内部采用 `SKILL.md + references/ + assets/ + _meta.json` 结构 | 与 OpenClaw 技能组织方式保持一致 | Accepted |
| backend 部署完成后输出 redacted connection bundle，交由前端机器上的 AI 接入 | 支持分机部署且不泄露敏感信息 | Accepted |
| v1 CLI 覆盖配置、鉴权、部署、连接与 smoke test | 这是项目可用性和可运维性的核心入口 | Accepted |
| Docker-first 作为跨平台优先路径，同时补充 Linux systemd 原生部署路径 | 在保证多平台覆盖的前提下控制实现复杂度 | Accepted |

---
*Last updated: 2026-03-24 after scope realignment*
