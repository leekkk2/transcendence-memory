# Backend Deploy / 后端部署

## 中文优先

### Docker-first

推荐命令：

```bash
transcendence-memory backend deploy
transcendence-memory backend health
```

如果部署失败，优先查看：

```bash
docker compose ps
docker compose logs backend --tail=100
```

### Linux systemd

Linux 可以走原生 `systemd` 路径，参考：
- `deploy/systemd/transcendence-memory-backend.service`
- `deploy/systemd/transcendence-memory-backend.env.example`
- `deploy/systemd/README.md`

### 人工验证

Phase 3 的真实验证仍需人工完成，见：
- `.planning/phases/03-cross-platform-deployment-and-health/03-VERIFICATION.md`

## English

Use `backend deploy` and `backend health` as the canonical operator commands. Docker-first is the primary path; Linux `systemd` is the native alternative.
