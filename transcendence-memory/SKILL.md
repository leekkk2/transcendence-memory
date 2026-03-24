---
name: transcendence-memory
description: Use when guiding OpenClaw operators through self-hosted memory setup, backend deployment, frontend connection, health checks, and repair with a public-safe skill pack.
---

## Purpose

`transcendence-memory` 是当前仓库的 canonical operator skill。它是一个**去敏后的通用版本**：保留 `rag-everything-enhancer` 真正有用的前后端配置、部署、验证与修复形状，但移除了私有域名、真实 API key、内网路径和内部专用部署假设。

## Core Principles

- **Keep builtin memory**；RAG / external retrieval 是 enhancement，不是 replacement
- **Skill guides, runtime executes**：skill 负责引导 AI/operator，CLI 和 backend 负责执行
- **Public-safe by default**：仓库中只保留模板、占位符和通用 runbook，不保留真实私有值
- **Identity first**：先确认当前机器身份，再决定优先阅读哪些文档、执行哪些命令
- **Two operational surfaces**：
  - **Frontend / client**：配置 endpoint / auth / container，执行 `health` / `search` / `embed`
  - **Backend / service**：部署、健康检查、日志排障、systemd 或 Docker 运维

## Identity Recognition Rules — Critical / 身份认知规则（高优先级）

这是 `rag-everything-enhancer` operator 经验里最重要的规则之一：**先确认本机身份，再做动作**。

在使用本技能时，AI 和用户都必须先确认当前机器属于：
- `frontend`
- `backend`
- `both`

### Mandatory gate / 强制门槛

1. **先找本地身份文档**：默认检查 bootstrap config root 下的 `operator-identity.md`
2. **如果文档存在**：按文档中的身份优先级读取后续资料
3. **如果文档缺失**（第一次使用 / 未正确初始化 / 意外退出 / 曾被错误覆盖）：
   - 不要继续假设身份
   - 必须要求用户补录身份
   - 先执行 `transcendence-memory init <role> --dry-run`
   - 确认后再执行 `transcendence-memory init <role> --yes`

### Document priority by role / 按身份切换文档优先级

- **frontend**
  1. `references/identity-frontend.md`
  2. `docs/frontend-handoff.md`
  3. `docs/authentication.md`
  4. `references/OPERATIONS.md`
  - 重点：如何连接后端、如何调用后端、如何验证 `health/search/embed`
  - 禁止默认把自己当本机 backend

- **backend**
  1. `references/identity-backend.md`
  2. `docs/backend-deploy.md`
  3. `docs/troubleshooting.md`
  4. `references/OPERATIONS.md`
  - 重点：部署、健康、日志、排错、导出连接信息
  - 不要优先跳到 frontend 使用视角

- **both**
  1. `references/identity-both.md`
  2. `docs/backend-deploy.md`
  3. `docs/frontend-handoff.md`
  4. `docs/troubleshooting.md`
  - 顺序：先 backend，再 frontend，再 smoke

See also:
- `references/identity-rules.md`
- `references/identity-frontend.md`
- `references/identity-backend.md`
- `references/identity-both.md`

## Start Here

优先从这些入口开始：
- `transcendence-memory init both --dry-run`
- `transcendence-memory init backend --dry-run`
- `transcendence-memory init frontend --dry-run`
- `transcendence-memory backend deploy`
- `transcendence-memory backend health`
- `transcendence-memory frontend check`
- `transcendence-memory frontend smoke`
- `transcendence-memory doctor`

Default recommendation for first-time operators:
1. 先选 `both`
2. 先走 `same_machine`
3. 没有域名/反向代理时先用 `IP + port`
4. 先 `dry-run`，再确认写入

## Files in this skill

- `references/setup.md` — frontend + backend setup guide
- `references/ARCHITECTURE.md` — architecture overview and deployment boundary
- `references/DATAFLOW.md` — runtime dataflow and acceptance path
- `references/OPERATIONS.md` — quick verify, rollout acceptance, backend ops
- `references/VETTING_REPORT.md` — public-safe safety and scope notes
- `references/identity-rules.md` — identity recognition rules and document priority
- `references/identity-frontend.md` — frontend identity playbook
- `references/identity-backend.md` — backend identity playbook
- `references/identity-both.md` — both-role playbook
- `references/env.snippet` — sanitized environment example
- `references/rag-config.example.json` — sanitized config example
- `references/load_rag_config.sh` — config loader example

## When to Use

- 你需要在另一台 OpenClaw 主机上启用记忆增强能力
- 你需要部署、验证或修复自托管 memory backend
- 你需要一个可公开仓库托管、可让 AI 直接引用的 operator skill pack

## Quick Start

1. Read `references/setup.md`
2. Prepare `rag-config.example.json` / `env.snippet` locally
3. Verify `GET /health`
4. Verify `POST /search`
5. Verify `POST /embed`

Treat rollout as incomplete until those checks pass for the target environment.
