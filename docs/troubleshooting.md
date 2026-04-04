# Troubleshooting / 故障排查

## 中文优先

### Bootstrap / local state

在 brand-new / sandbox / isolated 环境里，先做项目级开发安装：

```bash
./scripts/bootstrap_dev.sh
. .venv/bin/activate
```

然后再执行：

```bash
transcendence-memory doctor
transcendence-memory doctor --fix
python -m pytest -q
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

如果**当前设备 / 当前权限模型**下宿主机 Docker 需要 sudo，则改用：

```bash
sudo docker compose ps
sudo docker compose logs backend --tail=100
```

注意：这属于设备特定提醒，不是所有部署环境的通用默认路径。

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

- `ModuleNotFoundError: No module named 'typer'`：不要把它当成产品代码失败；先完成 `python -m pip install -e '.[dev]'` 的项目级 editable install，再重跑 pytest / CLI
- `401/403`：检查 auth header / API key
- `backend deploy` 提示当前会话不能直接用 Docker：不要立刻写成“主机没有 Docker”；先检查该设备当前上下文是否需要走 `sudo docker compose ...` 路径。这个判断是环境特定的，不应泛化成通用规则
- split-machine `backend export-connection` 提示 public/advertised endpoint：不要继续导出当前 bundle；先把 backend `config.toml` 的 `advertised_url` 改成前端真实可达的公网域名/公网 IP，再重试
- `5xx`：检查 backend 日志和 reverse proxy
- `search` 有 HTTP 200 但 body 仍报错：视为失败，不算 rollout complete
- brand-new container 搜不到内容：先确认 `/embed` 是否成功执行

## English

Start with `doctor`, `backend health`, `frontend check`, and `frontend smoke`. Treat transport success and application success as separate checks.
