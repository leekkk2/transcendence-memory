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
- **Two operational surfaces**：
  - **Frontend / client**：配置 endpoint / auth / container，执行 `health` / `search` / `embed`
  - **Backend / service**：部署、健康检查、日志排障、systemd 或 Docker 运维

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
