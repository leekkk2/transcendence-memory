# Operations — Transcendence Memory

## Runtime boundary reminder

- `transcendence-memory/` is the public-safe operator surface
- `transcendence-memory-server/` is the current private runtime truth
- Current backend mainline is **LanceDB-only**
- Current private backend default endpoint is `127.0.0.1:8711`

When operator docs and backend runtime reality diverge, close the gap by updating the operator docs instead of inventing a parallel truth.

## Part A — Frontend operations (client hosts)

### Endpoints
- `GET /health`
- `POST /search` — `{container, query, topk}`
- `POST /embed` — `{container, background?}`
- `POST /ingest-memory/objects` — when typed operator-side ingest is part of the target flow

### Client quick verify
```bash
source ./load_rag_config.sh

curl -sS -i "$RAG_ENDPOINT/health"

curl -sS -X POST "$RAG_ENDPOINT/search" \
  -H "Content-Type: application/json" \
  -H "$RAG_AUTH_HEADER: $RAG_API_KEY" \
  -d '{"container":"'$RAG_DEFAULT_CONTAINER'","query":"RAG memory test","topk":3}'

curl -sS -X POST "$RAG_ENDPOINT/embed" \
  -H "Content-Type: application/json" \
  -H "$RAG_AUTH_HEADER: $RAG_API_KEY" \
  -d '{"container":"'$RAG_DEFAULT_CONTAINER'","background":true}'
```

### Client rollout acceptance
Do not report the skill/config as successful until:
- `/health` returns 200
- `/search` returns 200 with real results
- `/embed` returns 200 and accepted/success
- if typed ingest is in scope, `/ingest-memory/objects` also matches contract expectations

### Important nuance
A transport-level HTTP 200 is **not enough** for `/search`.
If the JSON body still contains an error payload, the rollout is still failing from the operator perspective.

---

## Part B — Backend operations (service hosts)

### Service health
- Current private runtime path: `transcendence-memory-server/scripts/run_task_rag_server.sh`
- Docker path: `docker compose ps`, `docker compose logs backend --tail=100`
- public wrapper/systemd path: `systemctl status transcendence-memory-backend`
- Eva live ops fact: current online unit is `rag-everything.service`
- CLI path: `transcendence-memory backend health`

### Backend quick verify
```bash
curl -sS -i http://127.0.0.1:8711/health

curl -sS -X POST http://127.0.0.1:8711/search \
  -H "X-API-KEY: $RAG_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{"container":"client-a","query":"RAG memory test","topk":3}'

curl -sS -X POST http://127.0.0.1:8711/embed \
  -H "X-API-KEY: $RAG_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{"container":"client-a","background":true}'
```

If the operator-side flow depends on typed objects, also verify:

```bash
curl -sS -X POST http://127.0.0.1:8711/ingest-memory/objects \
  -H "X-API-KEY: $RAG_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{"container":"client-a","objects":[]}'
```

### Common failure interpretation
- **5xx at public endpoint**
  - usually reverse proxy or backend health failure
- **401/403**
  - API key mismatch or wrong auth header
- **search 200 but body has error**
  - backend logic/runtime error, not a successful search
- **embed fails**
  - dependency/runtime/provider/persistence issue
- **typed ingest accepted but search still empty**
  - confirm embed/indexing completed and the target container is initialized

## Reminder
Builtin memory stays enabled. Treat this skill as an operator pack, not a replacement memory subsystem.

## Naming boundary reminder
When documenting or operating against Eva production reality, use `rag-everything.service` as the current live unit name.
When documenting public deployment assets, `transcendence-memory-backend` is still the correct wrapper / packaging name.
Do not collapse these two naming surfaces into one.
