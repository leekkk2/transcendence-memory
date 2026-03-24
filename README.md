# Transcendence Memory

中文优先的自托管记忆部署项目，面向 OpenClaw skill、CLI、backend 服务和跨机器 handoff 工作流。

This is a Chinese-first self-hosted memory deployment project covering the OpenClaw skill package, CLI, backend service, and cross-machine handoff workflow.

## 项目是什么 / What This Is

`Transcendence Memory` 不是一个单独的后端，也不是一个只会写文档的 skill。它是一个完整的可发布 OSS 项目，包含：

- `transcendence-memory/` OpenClaw skill 包
- `src/transcendence_memory/` Python CLI 与 backend 服务
- `deploy/docker/` 与 `deploy/systemd/` 部署资产
- `.planning/` 中的阶段化设计与验证痕迹

The project ships:

- an OpenClaw skill package under `transcendence-memory/`
- a Python CLI and backend runtime under `src/transcendence_memory/`
- deployment assets for Docker and Linux systemd
- phase-by-phase planning and verification artifacts

## 灵感来源 / Inspiration

本项目的设计受到 `memory-lancedb-pro` 的启发，尤其是在“将能力包装成 AI 可引导的技能/工具链”、“把 provider / auth / deploy 配置显式化”这两个方向上受益很大。

This project is inspired in part by `memory-lancedb-pro`, especially in the way it treats deploy/auth/provider configuration as explicit operator-facing workflows.

## 核心边界 / Product Boundary

- `skill` 是引导入口，不是 backend runtime 本体
- `CLI` 是标准执行面
- `backend` 是独立可运行服务
- `bundle export/import` 只交换非敏感信息
- secret、token、API key 始终留在本机 secret storage

## 快速路径 / Quickstart

### 同机部署 / same-machine

适合首次跑通。

```bash
transcendence-memory init both --dry-run
transcendence-memory init both --yes
transcendence-memory auth set-api-key --api-key <your-key>
transcendence-memory backend deploy
transcendence-memory backend health
```

### 分机部署 / split-machine

后端机器：

```bash
transcendence-memory init backend --topology split_machine --dry-run
transcendence-memory init backend --topology split_machine --yes
transcendence-memory backend deploy
transcendence-memory backend export-connection --topology split_machine
```

前端机器：

```bash
transcendence-memory init frontend --topology split_machine --dry-run
transcendence-memory init frontend --topology split_machine --yes
transcendence-memory frontend import-connection --bundle-json '<bundle>'
transcendence-memory frontend check
transcendence-memory frontend smoke
```

## 文档导航 / Documentation

- `transcendence-memory/SKILL.md` — OpenClaw skill 入口
- `transcendence-memory/references/bootstrap.md` — skill 级 bootstrap 指引
- `transcendence-memory/references/troubleshooting.md` — skill 级排障说明
- `docs/backend-deploy.md` — backend 部署 runbook
- `docs/frontend-handoff.md` — handoff / import / smoke runbook
- `docs/authentication.md` — API key / OAuth 认证说明
- `docs/troubleshooting.md` — CLI / deploy / handoff 排障
- `docs/release-compatibility.md` — 版本兼容矩阵说明
- `docs/release-process.md` — 发布前检查清单

## 当前发布面 / Current Release Surface

- `transcendence-memory` skill 已同步发布到单独的 `skills-hub`
- CLI 和 backend 在当前仓库维护
- Docker-first 是默认发布路径
- Linux `systemd` 是受支持的原生替代路径

## 验证现状 / Verification Status

当前仓库已经完成多个阶段的自动化测试，但仍保留真实环境人工验证项：

- Phase 2: live PostgreSQL / provider / OAuth browser flow
- Phase 3: real Docker deployment / Linux systemd deployment
- Phase 4: real cross-machine export/import/smoke

这些项在 `.planning/phases/*/XX-VERIFICATION.md` 中有明确记录。

## License

MIT. See `LICENSE`.
