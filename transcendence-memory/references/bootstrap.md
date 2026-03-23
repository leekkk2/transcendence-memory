# Bootstrap Guide / 启动引导

## 中文优先

第一次使用时，优先走最短可用路径：
1. 选择 `both`
2. 选择 `same_machine`
3. 如果没有域名、Nginx 或反向代理信息，先使用 `IP + port`
4. 先运行 dry-run 看计划，再确认写入本地配置

推荐命令：
- `transcendence-memory init both --dry-run`
- `transcendence-memory init both --yes`

如果你明确知道当前机器角色，也可以使用：
- `transcendence-memory init backend`
- `transcendence-memory init frontend`

### same-machine

适合第一次跑通流程。AI 应优先推荐这个路径，除非用户明确要求 split-machine。

### split-machine

适合前后端分离部署。Phase 1 只负责本地 bootstrap 和安全配置，不负责最终的跨机器连接 bundle。

### IP + port fallback

如果没有域名、证书、反向代理或 Nginx 规划，不要阻塞流程。先用 `IP + port` 记录本地 bootstrap 状态，后续再升级。

## English

For first bootstrap, prefer:
- `both`
- `same_machine`
- `IP + port` when domain or reverse-proxy input is missing

Use dry-run first, then confirm the local bootstrap write.
