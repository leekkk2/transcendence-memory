# Identity Recognition Rules / 身份认知规则

## Why this matters

`rag-everything-enhancer` 类技能最容易出错的地方不是命令本身，而是**身份认知混淆**：

- 把 `frontend` 机器误当成 `backend`
- 在 `frontend` 身份下尝试“访问本机后端”
- 在 `backend` 身份下跳过部署与健康检查，直接按客户端方式操作

因此：**先确认身份，再决定文档优先级、命令优先级、排障方向。**

## Allowed identities

- `frontend`
- `backend`
- `both`

## Mandatory workflow

1. 先寻找本地身份文档：`operator-identity.md`
2. 如果存在：
   - 按文档中的身份继续
3. 如果不存在：
   - 视为未初始化完全、首次使用、或中途状态丢失
   - 必须要求用户补录身份
   - 执行 `transcendence-memory init <role> --dry-run`
   - 确认后执行 `transcendence-memory init <role> --yes`

## Priority by identity

### frontend

- 优先关注：
  - 如何导入连接
  - 如何连接后端
  - 如何校验 auth / `health` / `search` / `embed`
- 不要默认把本机当作本地 backend

### backend

- 优先关注：
  - backend deploy
  - backend health
  - Docker / systemd / logs / reverse proxy
  - 导出给 frontend 的连接信息
- 不要优先使用 frontend 客户端视角

### both

- 先 backend，再 frontend，再 smoke
- 不要跳过 backend 直接做 frontend 验证
