# Troubleshooting / 故障排查

## 中文优先

### Bootstrap

```bash
transcendence-memory doctor
transcendence-memory doctor --fix
```

### Backend health

```bash
transcendence-memory backend health
```

常见下一步：

```bash
docker compose ps
docker compose logs backend --tail=100
systemctl status transcendence-memory-backend
journalctl -u transcendence-memory-backend -n 100 --no-pager
```

### Handoff

如果前端导入后失败：

```bash
transcendence-memory frontend check
transcendence-memory frontend smoke
```

### 人工验证积压

- Phase 2: live PostgreSQL / provider / OAuth
- Phase 3: real Docker / Linux systemd
- Phase 4: real cross-machine handoff

分别见：
- `.planning/phases/02-authenticated-backend-core/02-VERIFICATION.md`
- `.planning/phases/03-cross-platform-deployment-and-health/03-VERIFICATION.md`
- `.planning/phases/04-secure-connection-handoff-and-verification/04-VERIFICATION.md`

## English

Use `doctor`, `backend health`, `frontend check`, and `frontend smoke` first. Then follow the phase verification reports for real-environment validation gaps.
