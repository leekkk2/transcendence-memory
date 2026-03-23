# Project Research Summary

**Project:** Transcendence Memory
**Domain:** OpenClaw-compatible memory deployment platform
**Researched:** 2026-03-23
**Confidence:** MEDIUM

## Executive Summary

Transcendence Memory is not just a memory backend. It is an operator-facing deployment product for OpenClaw: a thin skill package that guides setup, a real CLI that owns configuration and orchestration, and an independently runnable backend service that exposes memory APIs. The strongest pattern across the research is clear separation of concerns: keep the skill small, move mutable behavior into the CLI, keep provider and storage access inside the backend, and treat same-machine and split-machine topologies as first-class flows rather than documentation afterthoughts.

The recommended implementation is a Python monorepo managed with `uv`, built around a FastAPI backend, a Typer CLI, shared Pydantic contracts, Docker Compose as the default cross-platform deployment path, and Linux `systemd` as a secondary native option. For persistence, the stack research is decisive: use PostgreSQL 18 with `pgvector` as the v1 system of record. That gives the project one operationally credible backend for auth, metadata, vectors, migrations, and backups. Connection handoff between machines should use a versioned redacted bundle that contains only public connection metadata and never secrets.

The main risks are not generic framework risks. They are contract and boundary failures: secret leakage through exported artifacts, skill/backend responsibility collapse, topology bugs caused by exporting local-only addresses, OAuth drift across CLI and backend, and cross-platform automation sprawl. The roadmap should therefore start with security, schema, topology, and role boundaries before building orchestration polish. If Phase 1 is weak, every later phase becomes expensive to fix.

## Key Findings

### Recommended Stack

The stack research strongly favors a Python-first monorepo with shared packages instead of a mixed-language repo or a shell-script-heavy toolchain. The most important choice is consolidating on one backend data plane: PostgreSQL 18 plus `pgvector`, not a local embedded vector store. FastAPI, SQLAlchemy, Alembic, Pydantic 2, and Typer form the core implementation layer, while Docker Compose and Caddy define the default deployment surface.

**Core technologies:**
- `Python 3.13` baseline, tested on `3.14` — one language for backend, CLI, deployment helpers, and shared schemas.
- `uv` workspaces — reproducible monorepo dependency management and shared internal packages without publish/reinstall churn.
- `FastAPI` + `Uvicorn` — typed API surface for health, auth, search, embed, and deployment-facing endpoints.
- `PostgreSQL 18` + `pgvector` — canonical v1 persistence for relational state, vectors, migrations, backups, and remote self-hosting.
- `SQLAlchemy` + `Alembic` — explicit schema control and migrations.
- `Pydantic 2` + `pydantic-settings` — one typed contract layer for config, bundles, API models, and settings.
- `Typer` — CLI control plane for `init/config`, auth, deploy, connect, export/import, and smoke-test flows.
- `HTTPX` + provider profile abstractions — consistent provider/model/base URL integration without vendor lock-in.
- `Docker Compose` + `Caddy` — standard cross-platform deployment path with simple HTTPS termination.
- `systemd` — Linux-only native deployment option, not the primary abstraction.

### Expected Features

The feature research is opinionated: the MVP is only credible if it solves secure deployment and secure connection handoff, not just local backend startup. That means topology-aware setup, explicit auth lifecycle commands, redacted bundle export/import, verification commands, and bilingual operator docs are launch scope, not polish.

**Must have (table stakes):**
- Guided `init/config` with environment detection and topology selection.
- Provider/model/base URL configuration plus `auth login/status/logout` for `apiKey + OAuth`.
- `backend deploy/health` and `frontend connect/check`.
- Secure secret handling with redacted CLI output and local secret storage conventions.
- Redacted connection bundle export/import for split-machine setups.
- End-to-end `search/embed` smoke tests.
- Chinese-first bilingual README and operator runbooks.

**Should have (competitive):**
- Plan -> confirm -> execute -> verify workflow instead of opaque install scripts.
- Recovery-first CLI output with explicit next commands and redacted diagnostics.
- OpenClaw-native orchestration that treats backend and frontend roles differently.
- AI-consumable bilingual topology playbooks and secure handoff UX.

**Defer (v2+):**
- Web admin console.
- Automatic cross-machine secret sync.
- Old private-memory migration/import tooling.
- Multi-node or Kubernetes deployment.
- Auth modes beyond `apiKey + OAuth`.
- Optional status UI/TUI, backup/restore workflows, and multi-user profiles.

### Architecture Approach

The architecture research confirms the product should be built contract-first: shared schemas first, backend second, deployment adapters third, CLI fourth, skill last. The durable pattern is "thin skill, thick CLI, independent backend." One issue needs explicit correction during implementation: the architecture draft still references LanceDB/local-store patterns, but the stack recommendation is PostgreSQL plus `pgvector`. The roadmap should treat Postgres as authoritative and update architecture contracts accordingly.

**Major components:**
1. Skill package — detects machine role/topology, explains the plan, invokes stable CLI commands, and verifies outcomes.
2. CLI/config layer — source of truth for operator actions, config validation, export/import, deploy, and verification commands.
3. Shared contracts package — owns config schemas, bundle schema, API models, and compatibility metadata.
4. Deployment adapters — translate desired state into Docker Compose or Linux `systemd` runtime behavior.
5. Backend service — owns auth enforcement, provider integration, memory APIs, and persistence.
6. Docs/runbooks — separate deliverable for human and AI operators, not a substitute for contracts.

### Critical Pitfalls

1. **Secret leakage through "redacted" bundles** — solve this with an allowlist-only bundle schema, secret scanning, and strict bans on secrets in exports, examples, logs, and image metadata.
2. **Skill/backend boundary collapse** — keep the backend independently runnable, keep the skill orchestration-only, and reject role-invalid commands instead of guessing.
3. **OAuth contract drift** — normalize native CLI OAuth around browser + PKCE + loopback redirect, store token metadata structurally, and never export refresh tokens.
4. **Split-machine exports that contain local-only addresses** — model bind/listen/public URLs separately and export only public or advertised endpoints.
5. **Cross-platform automation sprawl** — make Docker-first the canonical path, keep platform specifics in thin wrappers, and document an explicit support matrix.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Security, Contracts, and Topology Baseline
**Rationale:** This must come first because most catastrophic failures are contract failures: leaked secrets, config drift, wrong machine role assumptions, and incompatible bundle formats.
**Delivers:** Shared schema package, role/topology model, public-vs-secret config split, redacted connection bundle spec, versioning rules, and generated config/docs scaffolding.
**Addresses:** Guided bootstrap foundations, secure secret handling, redacted bundle export/import requirements, topology-aware setup.
**Avoids:** Secret leakage, docs/config drift, skill/backend boundary collapse.

### Phase 2: Backend Runtime and Auth Contract
**Rationale:** Once contracts are fixed, the backend can implement them without rework. Auth and public URL handling must be correct before any frontend handoff is credible.
**Delivers:** FastAPI backend, Postgres + `pgvector` persistence, provider abstraction, `/health`, core search/embed APIs, `apiKey + OAuth` enforcement, and remote-safe export logic.
**Uses:** FastAPI, SQLAlchemy, Alembic, Pydantic, PostgreSQL 18, `pgvector`, HTTPX, Authlib.
**Implements:** Backend service, auth middleware, provider adapters, persistence layer.
**Avoids:** OAuth drift, split-machine local-address leakage, backend/runtime ambiguity.

### Phase 3: CLI Control Plane and Cross-Platform Deployment
**Rationale:** The CLI is the product surface. It should be built after backend and contracts exist so commands wrap real behavior instead of inventing it.
**Delivers:** `init/config`, `provider set`, `auth login/status/logout`, `backend deploy/health`, Docker Compose adapter, Linux `systemd` adapter, environment detection, and plan -> confirm -> execute -> verify flow.
**Addresses:** Guided bootstrap, provider/model/base URL configuration, backend deploy/health, cross-platform support.
**Avoids:** Shell sprawl, role confusion, config drift.

### Phase 4: Frontend Handoff, Verification, and Bilingual Operator Experience
**Rationale:** Frontend connection and smoke verification depend on stable backend exports and real CLI flows. Docs should be finalized only after commands and output shapes stabilize.
**Delivers:** `backend export-connection`, `frontend import-connection`, `frontend connect/check`, end-to-end `search/embed` smoke tests, same-machine and split-machine runbooks, troubleshooting, and AI-readable bilingual references.
**Addresses:** Frontend connect/check, redacted bundle UX, smoke tests, Chinese-first bilingual documentation.
**Implements:** Handoff flow, verification surface, operator documentation layer.
**Avoids:** False-positive success states, unsafe secret transfer, split-machine adoption failure.

### Phase 5: Packaging, Compatibility, and Release Hardening
**Rationale:** Packaging and CI should harden a working surface, not mask unclear contracts. This phase protects the open-source release path.
**Delivers:** Lean skill packaging, compatibility matrix for skill/CLI/backend/bundle versions, clean-install tests, secret scanning, protected CI/CD separation, SHA-pinned actions, release smoke checks.
**Addresses:** OpenClaw-native packaging and OSS release readiness.
**Avoids:** Skill/backend version skew, unsafe automation trust boundaries, regressions in published artifacts.

### Phase Ordering Rationale

- Contracts come before features because config names, bundle fields, topology roles, and secret boundaries are the hardest mistakes to unwind later.
- Backend comes before CLI and skill because the research consistently says the skill should orchestrate stable commands, not invent runtime behavior.
- Deployment automation comes before documentation finalization because operator docs must reflect actual command surfaces and support matrices.
- Packaging and CI hardening come last because compatibility and trust controls are only meaningful once the shipped interfaces stop moving.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** OAuth/provider specifics still need implementation-level validation by supported provider, especially redirect registration, PKCE, and token lifecycle edge cases.
- **Phase 3:** Windows and macOS deployment ergonomics need concrete support-matrix validation, especially Docker Desktop, WSL2, shell wrappers, and path behavior.
- **Phase 4:** Remote deployment exposure patterns need deeper validation around Caddy, TLS metadata, custom CA handling, and real second-machine verification.

Phases with standard patterns (skip research-phase):
- **Phase 1:** Shared schema design, secret redaction rules, and monorepo contract boundaries are already well-supported by the existing research.
- **Phase 5:** CI isolation, action pinning, artifact compatibility checks, and package-install validation follow standard OSS hardening patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Mostly grounded in official docs and current versions; the overall direction is stable and specific. |
| Features | MEDIUM | Strongly aligned with project scope and competitor expectations, but still partly inferred from adjacent products rather than direct user validation. |
| Architecture | MEDIUM | The control-plane pattern is clear, but the storage layer still needs correction from LanceDB-oriented precedent to the Postgres + `pgvector` decision. |
| Pitfalls | HIGH | Risks are concrete, repeated across OSS deployment projects, and backed by official security, Docker, and OAuth guidance. |

**Overall confidence:** MEDIUM

### Gaps to Address

- **Persistence contract mismatch:** `ARCHITECTURE.md` still reflects LanceDB-era patterns, while `STACK.md` recommends PostgreSQL + `pgvector`. Planning should treat Postgres as final and update all diagrams, schemas, and acceptance criteria accordingly.
- **OAuth provider scope:** The research supports `apiKey + OAuth`, but does not yet define the exact provider matrix, redirect registrations, or when backend-side confidential clients are necessary.
- **Remote URL and TLS contract:** The bundle needs a finalized shape for public URL, auth metadata, TLS mode, optional CA hints, and compatibility flags before frontend import work starts.
- **Platform support granularity:** Linux/macOS/Windows are in scope, but the exact v1 capability matrix, especially for Windows/WSL2 and native-vs-Docker behavior, still needs explicit definition.
- **Observability depth:** Health, readiness, and smoke-test boundaries are described, but log format, diagnostic bundle shape, and failure taxonomy should be finalized during phase planning.

## Sources

### Primary (HIGH confidence)
- Local project context: `.planning/PROJECT.md` — scope, constraints, topology, packaging, and security boundaries.
- Official Python/package sources: PyPI pages for `uv`, `fastapi`, `uvicorn`, `SQLAlchemy`, `pydantic`, `pydantic-settings`, `psycopg`, `pgvector`, `httpx`, `keyring`, `argon2-cffi`, `ruff`, `pyright`, `pytest`.
- PostgreSQL and `pgvector` official docs — current release line and vector extension support.
- Docker official docs — Compose installation model, secrets, env precedence, Desktop networking, platform caveats.
- OpenClaw official docs — auth, onboarding, secrets, packaging, and CLI expectations.
- OAuth RFCs `8252` and `9700` — native-app and security best practices.

### Secondary (MEDIUM confidence)
- Mem0/OpenMemory docs — quickstart, OSS configuration, and connection UX expectations.
- Letta self-hosting docs — Docker-first topology and remote connection expectations.
- Local precedent in `skills-hub/rag-everything-enhancer` — useful for packaging and operator-flow patterns, but not authoritative for final stack choices.

### Tertiary (LOW confidence)
- Ecosystem issue/security references cited in `PITFALLS.md` — useful as cautionary examples, but not direct design authority.

---
*Research completed: 2026-03-23*
*Ready for roadmap: yes*
