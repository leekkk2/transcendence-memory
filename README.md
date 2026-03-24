# Transcendence Memory

中文优先的自托管记忆 operator 仓库，面向 OpenClaw skill、CLI、backend 服务，以及前后端分离部署场景。

This is a Chinese-first self-hosted memory operator repository covering the OpenClaw skill pack, CLI, backend service, and split-machine deployment flows.

## 项目是什么 / What This Is

`Transcendence Memory` 的目标是提供一套**可公开托管、可让 AI 直接引用、可用于实际部署**的记忆能力工具链：

- `transcendence-memory/`：canonical OpenClaw skill pack
- `src/transcendence_memory/`：Python CLI 与 backend runtime
- `deploy/docker/`、`deploy/systemd/`：部署资产
- `docs/`：前后端配置、认证、连接与排障 runbook

它不是“只有说明文档的 skill”，也不是“把 backend 塞进 skill 里”的单体包。skill 负责引导，CLI 和 backend 负责执行。

## 灵感来源 / Inspiration

本项目受 `memory-lancedb-pro` 启发，尤其是在：
- 把 deploy / auth / provider 配置显式化
- 让 AI/operator 通过技能和 runbook 完成部署与验证

## 核心边界 / Product Boundary

- `skill` 是 operator 入口，不是 runtime 本体
- `CLI` 是标准执行面
- `backend` 是独立可运行服务
- `frontend handoff` 只交换非敏感信息
- API key、token、secret 始终留在本机安全存储
- builtin memory 保持启用

## 快速路径 / Quickstart

### same-machine

适合第一次跑通：

```bash
transcendence-memory init both --dry-run
transcendence-memory init both --yes
transcendence-memory auth set-api-key --api-key <your-key>
transcendence-memory backend deploy
transcendence-memory backend health
transcendence-memory frontend smoke
```

### split-machine

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

### Skill package
- `transcendence-memory/SKILL.md`
- `transcendence-memory/references/setup.md`
- `transcendence-memory/references/ARCHITECTURE.md`
- `transcendence-memory/references/DATAFLOW.md`
- `transcendence-memory/references/OPERATIONS.md`
- `transcendence-memory/references/VETTING_REPORT.md`

### Operator runbooks
- `docs/backend-deploy.md`
- `docs/frontend-handoff.md`
- `docs/authentication.md`
- `docs/troubleshooting.md`
- `docs/release-compatibility.md`
- `docs/release-process.md`

### Public-safe examples
- `docs/examples/rag-config.example.json`
- `docs/examples/env.snippet`
- `docs/examples/load_rag_config.sh`

## 验证基线 / Verification Baseline

Treat rollout as incomplete until the target environment passes:
1. `GET /health`
2. `POST /search`
3. `POST /embed`

## License

MIT. See `LICENSE`.
