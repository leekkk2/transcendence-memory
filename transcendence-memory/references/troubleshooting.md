# Troubleshooting / 故障排查

## Doctor Classifications

### auto-fixable

表示问题可以安全自动修复，例如：
- 缺少本地配置目录
- 缺少本地 secret 目录
- secret 文件权限不正确

Next action:
- `transcendence-memory doctor --fix`

### needs input

表示需要用户或 AI 提供更多输入，例如：
- 缺少配置文件但没有足够状态可重建
- 默认端口冲突
- 当前 bootstrap 选择与目标机器角色不一致

Next action:
- `transcendence-memory init both --dry-run`
- 或重新执行对应角色的 `init backend/frontend/both`

### manual follow-up

表示问题超出 Phase 1 自动修复范围，例如：
- Docker 不存在
- 需要域名、Nginx 或反向代理规划
- 需要公网暴露策略

Next action:
- 先完成本地 bootstrap
- 再根据后续 phase 的 runbook 补齐部署条件

## Rerun Guidance

重复执行 `init` 时，应该看到 diff-style plan，而不是静默覆盖原配置。

## English

`doctor` should classify findings as:
- `auto-fixable`
- `needs input`
- `manual follow-up`

Use rerun and dry-run paths before overwriting local bootstrap state.
