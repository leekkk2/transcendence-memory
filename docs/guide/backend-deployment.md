# Backend Deployment Guide

## For LLM Agents

Use this guide when you need to deploy the backend and prepare a frontend handoff.

### Canonical commands
```bash
transcendence-memory backend deploy
transcendence-memory backend health
```

### Docker-first default
Use the standard path first:
```bash
docker compose ps
docker compose logs backend --tail=100
```

### Environment-specific reminder
On some hosts, Docker exists but the current session cannot access the Docker daemon directly.
In that case, the host may require a sudo Docker path such as:
```bash
sudo docker compose ps
sudo docker compose logs backend --tail=100
```
Treat this as a host/session-specific reality, not as a universal default.

### After backend deploy
You must not hand off only a backend URL.
After deployment, export a redacted bundle and also pass the CLI's printed handoff instructions to the frontend operator.

```bash
transcendence-memory backend export-connection --topology split_machine --output bundle.json
```

The deploy-side operator should hand off:
1. `bundle.json`
2. auth mode
3. remaining local auth material the frontend must provide
4. exact frontend next-step commands

## Acceptance
At minimum verify:
```bash
curl -i http://127.0.0.1:8711/health
```
Then verify the relevant business paths:
- `/search`
- `/embed`
- `/ingest-memory/objects` when typed ingest matters

## Next guide
- Frontend handoff: `docs/guide/frontend-handoff.md`
- Auth handoff: `docs/guide/auth-handoff.md`
