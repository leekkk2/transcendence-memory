# Architecture — Transcendence Memory

```mermaid
flowchart TD
  subgraph Clients[OpenClaw client hosts]
    Agent[OpenClaw Agents]
    Skill[Transcendence Memory Skill
(config + usage + acceptance)]
  end

  Agent -->|HTTPS + Auth| Gateway[Advertised Memory Endpoint]
  Skill -->|configure/use| Agent

  subgraph Backend[Self-hosted backend machine]
    Gateway --> API[Memory API]
    Ops[Deploy + Operate + Repair] --> API
    API --> Search[Search Flow]
    API --> Embed[Embed Flow]
    API --> Store[(Configured persistence)]
  end
```

## Current Shape

- **Frontend / client**
  - configure endpoint/auth/container
  - call `/health`, `/search`, `/embed`
  - keep builtin memory enabled
- **Backend / service**
  - deploy and repair the backend service
  - manage reverse proxy or direct endpoint exposure
  - operate persistence, auth, and logs

## Contract

- `GET /health` — health check
- `POST /search` — authenticated query
- `POST /embed` — authenticated rebuild / ingest

## Deployment Boundary

- `skill` is the operator-facing guide
- `CLI` is the canonical execution surface
- `backend` is the independently runnable service
- exported frontend connection artifacts must stay redacted and secret-free

## Operating Rule

Builtin memory stays enabled. This project provides a public-safe operator pack plus deployable backend surfaces.
