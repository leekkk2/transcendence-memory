# Backend Deploy / 后端部署

## 中文优先

### Canonical commands

```bash
transcendence-memory backend deploy
transcendence-memory backend health
```

### Docker-first

默认推荐 Docker：

```bash
docker compose ps
docker compose logs backend --tail=100
```

适合：
- Linux
- macOS
- Windows（Docker Desktop）

### Linux systemd

Linux 可使用：
- `deploy/systemd/transcendence-memory-backend.service`
- `deploy/systemd/transcendence-memory-backend.env.example`
- `deploy/systemd/README.md`

常用检查：

```bash
systemctl status transcendence-memory-backend
journalctl -u transcendence-memory-backend -n 100 --no-pager
```

### Backend acceptance

至少确认：

```bash
curl -i http://127.0.0.1:8711/health
```

以及通过客户端或 curl 验证：
- `/search`
- `/embed`

### Failure order

优先排查：
1. 服务是否真的启动
2. 环境变量 / provider / database 是否可用
3. reverse proxy 或 advertised endpoint 是否正确
4. 日志里是否有 search/embed 运行时错误

## English

Use `backend deploy` and `backend health` as the canonical operator commands. Docker-first is the default path; Linux `systemd` is the supported native alternative.
