# Transcendence Memory Guides

面向人类 operator 的统一文档入口。

如果你是第一次接触这个仓库，请按下面顺序阅读，而不是随机翻 runbook。

## 1. Start Here
- `docs/guide/installation.md`

适合：
- 第一次进入仓库
- 想知道先装什么、先跑什么
- 需要 brand-new / isolated 环境启动

## 2. Deploy Backend
- `docs/guide/backend-deployment.md`

适合：
- 负责后端部署的人
- 需要判断当前机器走 Docker、宿主机 Docker 还是其他路径
- 需要知道部署完成后要交给前端哪些信息

## 3. Handoff to Frontend
- `docs/guide/frontend-handoff.md`
- `docs/guide/auth-handoff.md`

适合：
- 负责把 backend 交给前端的人
- 需要明确 bundle 之外还要交付什么
- 需要知道前端还要补哪些 auth 信息

## 4. Full Reference
如果你已经熟悉整体流程，再看这些详细 runbooks：
- `docs/backend-deploy.md`
- `docs/frontend-handoff.md`
- `docs/authentication.md`
- `docs/troubleshooting.md`

## Reading Principle
- 先读 guide，再读 runbook
- guide 负责告诉你“该做什么”
- runbook 负责告诉你“细节怎么做、失败怎么查”

## For LLM Agents
如果是 agent 自动读取，请从：
- `docs/guide/INDEX.md`
开始。
