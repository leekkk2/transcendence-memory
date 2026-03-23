# Transcendence Memory

## What This Is

Transcendence Memory 是一个面向 OpenClaw 的开源记忆能力项目，包含精简的 skill 包、可开源的 backend 服务实现、部署脚本，以及面向用户和 AI 的配置与运维文档。它的目标不是把后端能力硬塞进 skill 内部，而是让 skill 作为统一入口，根据当前机器角色与环境，协助用户完成 backend 或 frontend 的部署、连接、鉴权配置与验证。

项目面向需要在单机或前后端分机环境中启用记忆检索能力的 OpenClaw 用户。文档采用中英双语、中文为主，README 会明确说明其受 `memory-lancedb-pro` 启发，并同时遵循 OpenClaw `skill-creator` 的结构最佳实践。

## Core Value

用户可以通过 OpenClaw skill 以安全、可配置、可验证的方式完成记忆后端的部署与前端接入，而且整个过程不会把敏感信息硬编码进开源仓库。

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] 提供一个符合 OpenClaw 最佳实践的 skill 包，使用 `SKILL.md` 作为入口，并将执行脚本、参考文档、资源文件拆分到 `scripts/`、`references/`、`assets/`。
- [ ] 提供可开源的 backend 服务与部署脚本，由 skill 根据当前机器角色和环境信息，协助用户完成 `backend` 或 `frontend` 的安装、配置、连接与验证。
- [ ] 支持 Linux、macOS、Windows，并支持“单机前后端同机部署”与“前后端分机部署”两种拓扑。
- [ ] 提供 CLI，至少覆盖 `init/config`、`provider set`、`auth login/status/logout`、`backend deploy/health`、`frontend connect/check`、`backend export-connection`、`frontend import-connection`、`search/embed` smoke test。
- [ ] 支持 `apiKey + OAuth` 两种 v1 鉴权方式，并允许配置 provider、model、base URL、API key 等参数。
- [ ] 在分机部署场景中，由 backend 侧生成一个可复制的 redacted connection bundle，仅包含非敏感连接信息；敏感信息保存在本机安全路径或交由用户决定如何处理，再由 frontend 机器上的 AI 完成接入。
- [ ] 所有敏感信息、私有地址、内部凭据、历史内部部署细节都不直接迁移到开源仓库，而是改写为配置模板、环境变量说明和文档化的配置方式。
- [ ] README 与项目文档采用中英双语、中文为主，并在 README 中明确引用 `memory-lancedb-pro` 作为启发来源之一。

### Out of Scope

- 自动旧数据迁移/导入能力 — v1 只提供迁移提示与说明，不在 skill 或 backend 中强耦合迁移流程。
- 多节点/高可用集群部署 — 先把单机与前后端分机的可靠路径打透。
- Web 管理后台 — v1 以 skill、CLI、文档、脚本为主。
- `apiKey + OAuth` 之外的更多鉴权模式 — 避免首版把认证矩阵做散。
- 让 skill 自身直接承载 backend runtime 能力 — skill 负责编排、部署、配置与验证，不替代 backend 服务本体。

## Context

当前已有一个私有技能原型位于 `skills-hub` 仓库中的 `skills/rag-everything-enhancer/`，其中包含内部使用的配置样例、运维说明和对集中式服务的依赖描述。本项目的核心背景是将这套能力迁移、重构并开源到独立仓库 `transcendence-memory`，同时清理所有不适合公开的敏感信息与内部耦合内容。

实现上需要同时满足两类参考约束。一类是 OpenClaw `skill-creator` 所代表的技能组织最佳实践：`SKILL.md` 保持精简，详细说明、脚本与资源按需放在 `scripts/`、`references/`、`assets/` 中。另一类是 `memory-lancedb-pro` 所体现的可配置化、CLI 化经验：provider、API key、OAuth、连接信息与运维动作需要通过清晰的命令和配置接口暴露，而不是散落在文档片段里。

本项目还需要避免一个常见误区：把“可通过 skill 安装 backend”误写成“skill 本身拥有 backend 能力”。真正的边界是 skill 负责探测环境、给出计划、执行脚本、写入配置、验证结果，并引导用户或 AI 在多机器间安全交接连接信息；backend 服务则作为仓库内的独立开源实现与部署目标存在。

## Constraints

- **Security**: 开源仓库中不得包含真实密钥、私有域名凭据、内部网络细节或其他敏感信息 — 只能提供模板、占位符和安全存储路径约定。
- **OpenClaw Packaging**: skill 目录结构必须符合 OpenClaw 技能最佳实践 — 便于 agent 加载、维护和发布。
- **Topology Support**: 必须同时支持同机部署与分机部署 — 因为用户明确要求两种使用方式都能走通。
- **Platform Support**: 必须覆盖 Linux、macOS、Windows — 首版范围已经锁定，不能只做单平台。
- **Deployment UX**: 推荐采用“环境探测 → 计划展示 → 用户确认 → 执行 → 验证”的引导式自动化 — 避免黑盒安装带来的不可控风险。
- **Auth Scope**: v1 只做 `apiKey + OAuth` — 先把主路径做稳，避免鉴权模式无限扩张。
- **Documentation**: 文档必须中英双语、中文为主，README 需要说明受 `memory-lancedb-pro` 启发 — 这是用户明确要求的对外叙事方式。
- **License**: 项目采用 MIT License — 方便传播与二次集成。

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 在 `transcendence-memory` 中独立初始化项目并承载后续规划与实现 | 迁移、开源、实现都发生在新仓库中，避免继续依附 `skills-hub` | — Pending |
| 使用单仓库承载 skill、backend、部署脚本与项目文档 | 便于统一版本管理、开源发布与跨层演进 | — Pending |
| skill 负责引导、编排、部署、配置和验证，而不是直接内嵌 backend 能力 | 保持职责清晰，符合前后端分离与 OpenClaw skill 最佳实践 | — Pending |
| skill 包内部采用 `SKILL.md + scripts/ + references/ + assets/` 结构 | 与 OpenClaw `skill-creator` 的组织方式保持一致 | — Pending |
| backend 部署完成后输出 redacted connection bundle，交由前端机器上的 AI 接入 | 支持分机部署且不泄露敏感信息 | — Pending |
| v1 CLI 覆盖配置、鉴权、部署、连接与 smoke test | 这是项目可用性和可运维性的核心入口 | — Pending |
| v1 鉴权模式固定为 `apiKey + OAuth` | 满足目标使用方式，同时控制首版复杂度 | — Pending |
| 文档采用中英双语、中文为主，README 明确引用 `memory-lancedb-pro` 的启发 | 与目标用户和开源叙事保持一致 | — Pending |
| Docker-first 作为跨平台优先路径，同时补充 Linux systemd 原生部署路径 | 在保证多平台覆盖的前提下控制实现复杂度 | — Pending |

---
*Last updated: 2026-03-23 after initialization*
