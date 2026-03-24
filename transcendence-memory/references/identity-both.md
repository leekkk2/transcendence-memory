# Both Identity / 双角色身份

## 你是谁

你是 `both` 机器。

## 推荐顺序

1. 先完成 backend 部署与健康检查
2. 再完成 frontend 配置与连接
3. 最后执行 smoke / end-to-end 验证

## 关键规则

- 不要跳过 backend 直接做 frontend 验证
- 若 `health` 没过，不要继续把问题当作前端调用问题

## 优先文档

1. `docs/backend-deploy.md`
2. `docs/frontend-handoff.md`
3. `docs/troubleshooting.md`
