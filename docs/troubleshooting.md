# Troubleshooting / 故障排查

## 中文优先

### Bootstrap / local state

```bash
transcendence-memory doctor
transcendence-memory doctor --fix
```

如果 `doctor` 报告缺少 `operator-identity.md`：

- 不要继续假设当前机器是 frontend / backend / both
- 先补录身份
- 然后重新执行：

```bash
transcendence-memory init <role> --dry-run
transcendence-memory init <role> --yes
```

### Backend health

```bash
transcendence-memory backend health
docker compose ps
docker compose logs backend --tail=100
```

Linux systemd:

```bash
systemctl status transcendence-memory-backend
journalctl -u transcendence-memory-backend -n 100 --no-pager
```

### Frontend / handoff

```bash
transcendence-memory frontend check
transcendence-memory frontend smoke
```

### Common next steps

- `401/403`：检查 auth header / API key
- `5xx`：检查 backend 日志和 reverse proxy
- `search` 有 HTTP 200 但 body 仍报错：视为失败，不算 rollout complete
- brand-new container 搜不到内容：先确认 `/embed` 是否成功执行

## English

Start with `doctor`, `backend health`, `frontend check`, and `frontend smoke`. Treat transport success and application success as separate checks.
