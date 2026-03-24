# Phase 2 Research: Authenticated Backend Core

**Project:** Transcendence Memory
**Phase:** 2
**Researched:** 2026-03-24
**Confidence:** Medium-High

## Objective

Answer the Phase 2 planning question:

What does the planner need to know to create strong implementation plans for an authenticated backend, CLI auth flows, and real `search` / `embed` persistence on PostgreSQL + pgvector, while preserving the Phase 1 bootstrap/configuration contract?

## Existing Code Implications

Phase 1 already fixed the following constraints in code:
- Typer is the canonical CLI surface in `src/transcendence_memory/cli.py`
- config and secrets are stored separately via `src/transcendence_memory/bootstrap/persistence.py`
- platform-aware path handling is centralized in `src/transcendence_memory/bootstrap/paths.py`
- typed bootstrap/config models live in `src/transcendence_memory/bootstrap/models.py`

Phase 2 should therefore extend existing patterns instead of replacing them. In practice:
- auth tokens and API keys should reuse the existing secret-storage path contract
- backend connection/config state should remain compatible with the existing non-secret config model
- new backend code should be introduced as a separate package subtree, not folded into `bootstrap/`

## Official Guidance That Matters

### OAuth for CLI/native clients

The core guidance from RFC 8252 is directly relevant here:
- native apps should use Authorization Code Flow with PKCE
- loopback redirect URIs are the correct local callback pattern
- implicit-style flows are not the preferred choice for native clients

Planning implication:
- model Phase 2 OAuth as browser + PKCE + loopback redirect on `127.0.0.1`
- do not plan implicit-token-only behavior
- keep refresh/access tokens in secret storage only

### FastAPI and Python auth stack

FastAPI is well suited to a thin typed API service, but the important planning takeaway is not “use FastAPI” in the abstract; it is that request/response models, dependency injection, and auth middleware composition should be kept explicit. Authlib is the most natural fit for OAuth/OIDC client behavior in Python if the CLI and backend both need standards-based integration without inventing protocol details by hand.

Planning implication:
- separate auth service logic from route handlers
- keep route dependency injection explicit for API-key and bearer-token validation
- plan an OIDC/OAuth client adapter rather than provider-specific ad hoc code in routes

### PostgreSQL + pgvector

pgvector’s Python/SQLAlchemy support makes the Phase 2 persistence shape clear:
- store vectors in PostgreSQL
- use SQLAlchemy models and migrations
- register vector handling through the Python pgvector integration

Planning implication:
- Phase 2 must include actual database schema and migration work, not just abstract “memory service” placeholders
- vector storage should be first-class in the schema, not bolted onto a JSON blob

## Planning Conclusions

### 1. Split Phase 2 into backend foundation, persistence, auth flows, and memory API surface

Trying to implement all of Phase 2 in one plan would couple too many moving parts:
- dependency expansion
- backend application skeleton
- database schema/migrations
- API-key auth
- OAuth CLI flow
- authenticated search/embed

The planner should therefore separate:
1. backend/runtime scaffolding
2. PostgreSQL + pgvector persistence
3. API-key auth path
4. OAuth login/status/logout path
5. authenticated search/embed routes and verification

### 2. Backend package structure should stay explicit

Recommended internal shape:

```text
src/transcendence_memory/backend/
  app.py
  settings.py
  api/
    routes/
      health.py
      auth.py
      memory.py
  auth/
    api_keys.py
    oauth.py
    tokens.py
    dependencies.py
  db/
    base.py
    models.py
    session.py
```

Recommended additional project roots:
- `alembic.ini`
- `alembic/` or `migrations/`

Why this matters:
- it keeps FastAPI routing, auth policy, and persistence separate
- later deployment work in Phase 3 can target a stable backend app entrypoint
- later connection/handoff work in Phase 4 can build on explicit route contracts

### 3. Extend config contracts rather than inventing new ones

Phase 2 should not create a parallel auth-config system.

Extend the existing persistence contract with:
- backend service URL / bind address / advertised address metadata
- auth mode metadata
- non-secret OAuth provider metadata (issuer/client ID/redirect base)
- secret auth material (API key, access token, refresh token) in the secret file only

Recommended split:
- non-secret config file:
  - provider
  - model
  - base_url
  - backend bind host/port
  - auth mode
  - oauth issuer / client_id / scopes
- secret file:
  - API key
  - access token
  - refresh token
  - any client secret if later required

### 4. API-key auth and OAuth should share a common auth abstraction

The planner should avoid route-specific auth branching scattered throughout the code.

Recommended abstraction:
- a common auth dependency layer that can validate either:
  - `X-Transcendence-API-Key`
  - `Authorization: Bearer <access-token>`

CLI auth commands should then manage local secret state, while backend dependencies validate incoming credentials.

Why this matters:
- `auth status` and `auth logout` become CLI concerns
- backend route protection becomes a dependency/middleware concern
- later frontend handoff can reuse the same auth-mode metadata

### 5. Keep `/health` separate from authenticated memory operations

Phase 2 must prove real backend behavior, but `/health` should remain simpler than `/search` and `/embed`.

Recommended approach:
- `/health` reports service readiness and basic dependency state
- `/search` and `/embed` are authenticated

This keeps diagnostics readable and avoids overloading health checks with user auth semantics.

### 6. `embed` and `search` should be intentionally narrow in v1 Phase 2

To satisfy `BACK-05`, the backend must perform real provider-backed embedding and vector-backed search. But the planner should keep the memory API narrow:

Recommended initial contract:
- `POST /api/v1/memory/embed`
  - input: text content + optional metadata
  - output: stored record ID, provider/model used, vector dimension
- `POST /api/v1/memory/search`
  - input: query text + optional `limit`
  - output: ranked records with score and metadata

Avoid broad CRUD or memory-management surface area in Phase 2.

### 7. Phase 2 testing must include real integration against PostgreSQL + pgvector

Unit tests are not sufficient here because the phase promise includes real persistence.

Recommended testing layers:
- unit tests:
  - auth helpers
  - token redaction
  - config/auth metadata models
- API tests:
  - FastAPI app route protection
  - health endpoint behavior
  - auth status/logout command behavior
- integration tests:
  - PostgreSQL + pgvector insert/search path
  - authenticated embed/search flow
  - CLI browser-flow callback handling using mocked provider responses

Planning implication:
- at least one early plan should add Phase 2 test scaffolding and dependencies
- later implementation plans must each include concrete verification commands

### 8. Avoid these Phase 2 mistakes

- do not store tokens in the non-secret config file
- do not implement OAuth as a provider-specific one-off shell script
- do not fake `search` / `embed` with in-memory placeholders and call the phase complete
- do not defer migrations/schema until after route work
- do not make the CLI directly perform vector search instead of going through the backend

## Dependency and Library Implications

Phase 2 planning should expect additions such as:
- `fastapi`
- `uvicorn`
- `sqlalchemy`
- `alembic`
- `psycopg`
- `pgvector`
- `httpx`
- `authlib`

Possibly:
- `python-multipart` if needed by route parsing
- `pytest-asyncio` and `anyio` if async tests are used

## Validation Architecture

Phase 2 should absolutely keep a formal validation strategy because auth and persistence regressions are high-cost.

Recommended validation baseline:
- framework: `pytest`
- quick run target: auth/config model tests plus route-level tests that do not require full DB bring-up
- full run target: all unit tests plus PostgreSQL-backed integration tests
- token hygiene checks should assert absence of refresh-token content in CLI output and serialized non-secret config

Suggested new test files:
- `tests/unit/test_auth_models.py`
- `tests/unit/test_api_key_auth.py`
- `tests/unit/test_oauth_redaction.py`
- `tests/api/test_health_route.py`
- `tests/api/test_auth_routes.py`
- `tests/api/test_memory_routes.py`
- `tests/integration/test_pgvector_memory.py`
- `tests/integration/test_oauth_cli_flow.py`

## Recommended Sources of Truth for Planning

- `.planning/phases/02-authenticated-backend-core/02-CONTEXT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`
- `.planning/phases/01-guided-bootstrap-and-safe-configuration/01-CONTEXT.md`
- `.planning/research/SUMMARY.md`
- current Phase 1 implementation under `src/transcendence_memory/`

## Sources Used

- RFC 8252 (OAuth 2.0 for Native Apps) — loopback redirect and PKCE guidance
- Authlib documentation — standards-based OAuth/OIDC client integration patterns
- FastAPI official security documentation — route dependency and auth structure patterns
- pgvector Python / SQLAlchemy documentation — vector column integration and Postgres-backed search patterns
- local project research and implemented Phase 1 code

---
*Phase research completed: 2026-03-24*
*Ready for planning: yes*
