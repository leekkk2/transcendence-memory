# VETTING_REPORT — Transcendence Memory

This public-safe skill package exposes two operational surfaces:
- **Frontend / client** usage on OpenClaw hosts
- **Backend / service** deployment and repair on the host running the memory backend

## Safety / scope notes
- Builtin memory remains enabled; this skill augments retrieval and deployment workflows only.
- Business APIs require configured auth; `/health` can remain suitable for anonymous probing if the backend is configured that way.
- Config-only alignment is **not** enough; acceptance requires real `/health` + `/search` + `/embed` verification.
- Public repositories must never contain real API keys, private endpoints, or internal-only filesystem paths.

## Current architecture facts
- The skill is the operator-facing guide.
- The CLI/backend are the execution surfaces.
- Endpoint, auth, provider, and deploy behavior are configuration-driven.
- Connection handoff artifacts must stay redacted and secret-free.

## Rollout rule
Do not declare the setup successful on any client or backend until:
1. `/health` -> 200
2. `/search` -> 200 with real results
3. `/embed` -> 200 and accepted/started
