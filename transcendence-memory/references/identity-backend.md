# Backend Identity / 后端身份

## 你是谁

你是 `backend` 机器。

## 你应该优先做什么

1. 部署 backend
2. 检查 backend health
3. 排查 Docker / systemd / logs / reverse proxy
4. 导出给 frontend 的连接信息

## 你不应该做什么

- 不要优先用 frontend 客户端视角指导当前机器
- 不要在后端未健康时就直接把问题归因到前端

## 优先文档

1. `docs/backend-deploy.md`
2. `docs/troubleshooting.md`
3. `transcendence-memory/references/OPERATIONS.md`
