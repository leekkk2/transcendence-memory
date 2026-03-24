# Linux systemd deployment

## Files

- Unit file: `deploy/systemd/transcendence-memory-backend.service`
- Env file template: `deploy/systemd/transcendence-memory-backend.env.example`

## Suggested target paths

- Unit file: `/etc/systemd/system/transcendence-memory-backend.service`
- Env file: `/etc/transcendence-memory/transcendence-memory-backend.env`

## Commands

```bash
sudo mkdir -p /etc/transcendence-memory
sudo cp deploy/systemd/transcendence-memory-backend.env.example /etc/transcendence-memory/transcendence-memory-backend.env
sudo cp deploy/systemd/transcendence-memory-backend.service /etc/systemd/system/transcendence-memory-backend.service
sudo systemctl daemon-reload
sudo systemctl enable --now transcendence-memory-backend
systemctl status transcendence-memory-backend
journalctl -u transcendence-memory-backend -n 100 --no-pager
```

## Notes

- Keep deployment and health scope only; release hardening belongs to a later phase.
- Update `WorkingDirectory=` and `EnvironmentFile=` if your installation path differs.
