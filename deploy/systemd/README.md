# Linux systemd deployment

## Status

These files are now aligned to the current canonical backend runtime:
`transcendence-memory-server/scripts/run_task_rag_server.sh`.

They are **operator-facing deployment assets / packaging wrapper**, not Eva's live unit record.
Current Eva live reality has been confirmed separately:
- live unit on Eva: `rag-everything.service`
- live `ExecStart`: `/home/ubuntu/.openclaw/workspace/scripts/run_task_rag_server.sh`
- live listen: `0.0.0.0:8711`

Treat `transcendence-memory-backend` as the public wrapper name for the verified private runtime, and do not describe it as Eva's current live unit name unless production reality changes and is re-verified.

## Files

- Unit file: `deploy/systemd/transcendence-memory-backend.service`
- Env file template: `deploy/systemd/transcendence-memory-backend.env.example`

## Suggested target paths

- Unit file: `/etc/systemd/system/transcendence-memory-backend.service`
- Env file: `/etc/transcendence-memory/transcendence-memory-backend.env`

## Canonical runtime assumptions

- Working directory should point at the deployed `transcendence-memory-server/` checkout
- Service entrypoint is `./scripts/run_task_rag_server.sh`
- Runtime listens on `0.0.0.0:8711` and is typically reverse-proxied as `rag.zweiteng.tk -> 127.0.0.1:8711`
- Current backend chain is **LanceDB-only**
- `RAG_API_KEY` and `EMBEDDING_API_KEY` must be present in the environment file
- If overriding embedding endpoint, set both `EMBEDDING_BASE_URL` and `EMBEDDINGS_BASE_URL` to the same value

## Commands

```bash
sudo mkdir -p /etc/transcendence-memory
sudo cp deploy/systemd/transcendence-memory-backend.env.example /etc/transcendence-memory/transcendence-memory-backend.env
sudo cp deploy/systemd/transcendence-memory-backend.service /etc/systemd/system/transcendence-memory-backend.service
sudo systemctl daemon-reload
sudo systemctl enable --now transcendence-memory-backend
systemctl status transcendence-memory-backend
journalctl -u transcendence-memory-backend -n 100 --no-pager
curl -i http://127.0.0.1:8711/health
```

## Notes

- Update `WorkingDirectory=` and `EnvironmentFile=` if your installation path differs.
- If you intentionally want runtime data to land in monorepo-root `tasks/rag/...`, set `WORKSPACE=/path/to/skills-workspace` in the env file. Otherwise leave it unset and let the script default to the server repo root.
- The remaining production gap is whether Eva's **actual** long-running process manager state matches this wrapper exactly; until verified, document live differences in root-level long-running state files rather than inventing certainty here.
