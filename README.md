# Transcendence Memory

中文优先的技能与部署仓库，聚焦三件事：
- skill 入口
- CLI 使用
- backend / frontend handoff 与部署文档

This repository focuses on operator-facing materials only:
- skill entrypoints
- CLI usage
- backend deployment
- frontend handoff

## Scope

这里只保留对当前使用者直接有用的内容：
- 如何初始化
- 如何部署 backend
- 如何导出并交接给 frontend
- 如何配置 auth
- 如何排障

不展开项目背景、产品叙事或长期架构说明。

## Runtime Alignment

当前 operator 文档默认对接 `transcendence-memory-server/` 的真实 backend runtime。
若 skill/operator 文档与 backend runtime 文档冲突，应以当前 backend runtime 真相为准，并回写本仓库文档。

当前默认私有服务端口径：`127.0.0.1:8711`
当前服务端主链：**LanceDB-only**

## Boundaries

- `skill`：入口与说明
- `CLI`：执行面
- `backend deployment`：后端部署与健康检查
- `frontend handoff`：前后端连接交付
- `auth`：本地鉴权材料配置与检查
- secrets 不进入 bundle，不出现在普通文档示例中

## Identity First

开始任何部署、连接、排障或 smoke 之前，先确认当前机器身份：

- `frontend`
- `backend`
- `both`

初始化后，本机应存在身份文档：

- `operator-identity.md`

如果没有该文档（第一次使用、未正确初始化、意外退出、或状态损坏）：

1. 不要继续假设当前身份
2. 先补录身份
3. 执行 `transcendence-memory init <role> --dry-run`
4. 确认后执行 `transcendence-memory init <role> --yes`

身份确认后再决定文档优先级：

- `frontend` → 优先看 `docs/frontend-handoff.md`
- `backend` → 优先看 `docs/backend-deploy.md`
- `both` → 先 backend，再 frontend，再 smoke

## Local Dev

在全新或隔离环境中，先建立项目自己的开发虚拟环境，再运行 CLI / pytest。

```bash
./scripts/bootstrap_dev.sh
. .venv/bin/activate
python -m pytest -q
```

它内部会完成：
- 创建/复用 `.venv`
- 升级 `pip`
- 执行 `python -m pip install -e '.[dev]'`

如果你只是临时进入仓库直接跑 `pytest`，很容易因为没有先安装项目依赖而遇到 `ModuleNotFoundError: No module named 'typer'` 这类假阻塞。该仓库的本地验证基线默认依赖 editable install。

## Quickstart

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
# 设备特定提醒：若当前机器上的宿主机 Docker 需要 sudo，请从宿主机 shell 继续执行 sudo docker compose follow-up。
# 先把 config.toml 里的 advertised_url 改成前端可达的公网域名/公网 IP，再导出 bundle。
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

## Documentation

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

### Human-readable guides
- `docs/guide/HUMAN_GUIDE_INDEX.md`
- `docs/guide/installation.md`
- `docs/guide/backend-deployment.md`
- `docs/guide/frontend-handoff.md`
- `docs/guide/auth-handoff.md`

### Fetchable guides for LLM agents
- `docs/guide/INDEX.md`
- `docs/guide/installation.md`
- `docs/guide/backend-deployment.md`
- `docs/guide/frontend-handoff.md`
- `docs/guide/auth-handoff.md`

### Public-safe examples
- `docs/examples/rag-config.example.json`
- `docs/examples/env.snippet`
- `docs/examples/load_rag_config.sh`

## Verification Baseline

Treat rollout as incomplete until the target environment passes:
1. `GET /health`
2. `POST /search`
3. `POST /embed`
4. when typed ingest is part of the target flow, `POST /ingest-memory/objects`

## License

MIT. See `LICENSE`.
