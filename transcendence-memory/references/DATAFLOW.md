# Dataflow — Transcendence Memory

## Search Path

```mermaid
sequenceDiagram
  participant Agent as OpenClaw Agent
  participant API as Memory Endpoint
  participant Svc as Backend Service
  participant Embed as Embedding Provider
  participant Store as Persistence

  Agent->>API: POST /search {container, query, topk}
  API->>Svc: authenticated request
  Svc->>Embed: embed query text
  Svc->>Store: read matching memory vectors
  Svc-->>Agent: results[]
```

## Embed / Rebuild Path

```mermaid
sequenceDiagram
  participant Agent as OpenClaw Agent
  participant API as Memory Endpoint
  participant Svc as Backend Service
  participant FS as Workspace Files
  participant Embed as Embedding Provider
  participant Store as Persistence

  Agent->>API: POST /embed {container, background?}
  API->>Svc: authenticated request
  Svc->>FS: scan workspace text files
  Svc->>FS: chunk files
  Svc->>Embed: embed chunk text
  Svc->>Store: upsert memory records
  Svc-->>Agent: {status, chunksIndexed|jobId}
```

## Frontend vs Backend Responsibilities

### Frontend Part
- set endpoint / auth / container
- verify `/health`
- use `/search`
- trigger `/embed` when rebuild is needed

### Backend Part
- install runtime dependencies
- keep backend service healthy
- keep advertised endpoint healthy
- repair auth / provider / persistence issues

## Acceptance Rule

A rollout is only complete when the target environment passes:
1. `GET /health`
2. `POST /search`
3. `POST /embed`
