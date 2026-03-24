# Operations — Transcendence Memory

## Part A — Frontend operations (client hosts)

### Endpoints
- `GET /health`
- `POST /search` — `{container, query, topk}`
- `POST /embed` — `{container, background?}`

### Client quick verify
```bash
source ./load_rag_config.sh

curl -sS -i "$RAG_ENDPOINT/health"

curl -sS -X POST "$RAG_ENDPOINT/search"   -H "Content-Type: application/json"   -H "$RAG_AUTH_HEADER: $RAG_API_KEY"   -d '{"container":"'$RAG_DEFAULT_CONTAINER'","query":"RAG memory test","topk":3}'

curl -sS -X POST "$RAG_ENDPOINT/embed"   -H "Content-Type: application/json"   -H "$RAG_AUTH_HEADER: $RAG_API_KEY"   -d '{"container":"'$RAG_DEFAULT_CONTAINER'","background":true}'
```

### Client rollout acceptance
Do not report the skill/config as successful until:
- `/health` returns 200
- `/search` returns 200 with real results
- `/embed` returns 200 and accepted/started

### Important nuance
A transport-level HTTP 200 is **not enough** for `/search`.
If the JSON body still contains an error payload, the rollout is still failing from the operator perspective.

---

## Part B — Backend operations (service hosts)

### Service health
- Docker path: `docker compose ps`, `docker compose logs backend --tail=100`
- systemd path: `systemctl status transcendence-memory-backend`
- CLI path: `transcendence-memory backend health`

### Backend quick verify
```bash
curl -sS -i http://127.0.0.1:8711/health

curl -sS -X POST http://127.0.0.1:8711/search   -H "X-API-KEY: $RAG_API_KEY"   -H 'Content-Type: application/json'   --data '{"container":"client-a","query":"RAG memory test","topk":3}'

curl -sS -X POST http://127.0.0.1:8711/embed   -H "X-API-KEY: $RAG_API_KEY"   -H 'Content-Type: application/json'   --data '{"container":"client-a","background":true}'
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

## Reminder
Builtin memory stays enabled. Treat this skill as an operator pack, not a replacement memory subsystem.
