---
name: transcendence-memory
description: Chinese-first bootstrap skill for guiding AI operators through Transcendence Memory setup and safe local configuration.
---

## Purpose

`transcendence-memory` 是主要的 AI 引导入口。它负责解释当前机器该走哪条 bootstrap 路径，并调用规范化的 CLI 命令完成本地初始化，而不是把 backend 运行时逻辑塞进 skill 内部。

## Start Here

优先使用这些命令：
- `transcendence-memory init backend`
- `transcendence-memory init frontend`
- `transcendence-memory init both`
- `transcendence-memory config show`
- `transcendence-memory doctor`

Default recommendation for first-time users:
- choose `both`
- choose `same_machine`
- use `IP + port` if domain or reverse-proxy information is not ready yet

## References

- `references/bootstrap.md` — bootstrap flow for same-machine and split-machine
- `references/troubleshooting.md` — bootstrap doctor classifications and next actions

## Notes

- This skill guides the operator and AI. The CLI is the canonical execution surface.
- Backend runtime deployment, OAuth completion, and cross-machine handoff are later phases.
