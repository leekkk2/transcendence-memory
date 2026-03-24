# Roadmap: Transcendence Memory

## Overview

This roadmap turns Transcendence Memory into a thin OpenClaw skill backed by a thick CLI and an independently runnable backend. The delivery order follows the product boundary and the main failure modes: establish safe role-aware bootstrap and config first, then ship authenticated backend behavior on PostgreSQL + pgvector, then layer in Docker-first deployment with Linux `systemd` as the secondary path, then secure redacted connection handoff, and finally harden the bilingual OSS package for release.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Guided Bootstrap and Safe Configuration** - Users choose machine role and topology, then create secure role-aware local configuration without opaque state changes.
- [ ] **Phase 2: Authenticated Backend Core** - Users can authenticate and run real memory operations against the independent backend backed by PostgreSQL + pgvector.
- [ ] **Phase 3: Cross-Platform Deployment and Health** - Users can deploy and operate the backend reliably through the Docker-first path, with Linux `systemd` as a secondary option.
- [ ] **Phase 4: Secure Connection Handoff and Verification** - Users can move only redacted connection metadata across machines and prove the end-to-end path works.
- [x] **Phase 5: Bilingual Packaging and Release Hardening** - Users get a coherent OpenClaw-ready OSS release surface with bilingual guidance and compatibility protection. (completed 2026-03-24)

## Phase Details

### Phase 1: Guided Bootstrap and Safe Configuration
**Goal**: Users can start from the packaged OpenClaw skill or CLI, choose the right machine role and topology, and establish safe local configuration before any deployment work begins.
**Depends on**: Nothing (first phase)
**Requirements**: BOOT-01, BOOT-02, BOOT-03, BOOT-04, BOOT-05, CONF-01, CONF-02, CONF-03, CONF-04, CONF-05
**Success Criteria** (what must be TRUE):
  1. User can launch the packaged OpenClaw skill or CLI, choose `backend`, `frontend`, or `both`, and receive same-machine or split-machine guidance before anything changes locally.
  2. User can run guided `init/config` that detects operating system, shell, Docker availability, writable paths, and occupied ports, then review a plan before local state changes are applied.
  3. User can generate role-aware configuration scaffolding and set provider, model, and base URL from CLI commands instead of editing repository files.
  4. User can keep secrets separate from non-sensitive configuration, inspect current non-sensitive settings safely, override config or secret storage paths, and rerun bootstrap without corrupting an existing setup.
**Plans**: TBD

### Phase 2: Authenticated Backend Core
**Goal**: Users can authenticate through the CLI and use the independent backend for real memory operations with PostgreSQL + pgvector as the authoritative persistence layer.
**Depends on**: Phase 1
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, BACK-05
**Success Criteria** (what must be TRUE):
  1. User can configure API key authentication for backend and frontend workflows using the supported configuration surface.
  2. User can complete OAuth login from CLI through a browser-based flow, then check current auth status and clear or rotate stored credentials from CLI.
  3. User can execute authenticated `search` and `embed` operations against the backend, and those operations persist through PostgreSQL + `pgvector`.
  4. User never sees refresh tokens or equivalent secrets in logs, redacted summaries, or exported artifacts produced by auth-enabled workflows.
**Plans**: TBD

### Phase 3: Cross-Platform Deployment and Health
**Goal**: Users can deploy the backend service predictably on supported machines and recover quickly when runtime health checks fail.
**Depends on**: Phase 2
**Requirements**: BACK-01, BACK-02, BACK-03, BACK-04, VERI-02
**Success Criteria** (what must be TRUE):
  1. User can deploy the backend service with the Docker-first path on Linux, macOS, and Windows.
  2. Linux user can follow a documented `systemd` path as a supported alternative to Docker.
  3. User can rerun backend deployment on a healthy install without breaking the running service or corrupting persisted configuration and data.
  4. User can run backend health checks from CLI and receive the next exact command or recovery step when the service is not healthy.
**Plans**: TBD

### Phase 4: Secure Connection Handoff and Verification
**Goal**: Users can connect frontend and backend machines through a redacted handoff flow and verify end-to-end behavior without leaking secrets or local-only addresses.
**Depends on**: Phase 3
**Requirements**: CONN-01, CONN-02, CONN-03, CONN-04, CONN-05, VERI-01
**Success Criteria** (what must be TRUE):
  1. Backend user can export a versioned redacted connection bundle that contains only the non-sensitive metadata the frontend machine needs.
  2. Split-machine exports use public or advertised connection endpoints and never expose backend-local bind addresses as frontend connection targets.
  3. Frontend user can import the redacted bundle, provide local secrets or auth material, and verify backend reachability plus auth compatibility from CLI.
  4. User can run end-to-end smoke tests that cover `health`, `search`, and `embed` across same-machine and split-machine flows.
**Plans**: TBD

### Phase 5: Bilingual Packaging and Release Hardening
**Goal**: Users can consume a releaseable OpenClaw-ready OSS package with bilingual operator guidance and version-compatibility protection across shipped surfaces.
**Depends on**: Phase 4
**Requirements**: VERI-03, VERI-04, VERI-05
**Success Criteria** (what must be TRUE):
  1. User can follow a Chinese-first bilingual README for both same-machine and split-machine setup flows.
  2. Operator can use bilingual runbooks for backend deployment, frontend connection, authentication, and troubleshooting without relying on internal-only knowledge.
  3. Release checks reject incompatible combinations of the OpenClaw skill package, CLI, backend service, and connection bundle versions before publication or upgrade guidance is emitted.
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Guided Bootstrap and Safe Configuration | 0/TBD | Not started | - |
| 2. Authenticated Backend Core | 0/TBD | Not started | - |
| 3. Cross-Platform Deployment and Health | 0/TBD | Not started | - |
| 4. Secure Connection Handoff and Verification | 0/TBD | Not started | - |
| 5. Bilingual Packaging and Release Hardening | 0/TBD | Complete    | 2026-03-24 |
