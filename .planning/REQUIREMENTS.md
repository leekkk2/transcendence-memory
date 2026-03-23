# Requirements: Transcendence Memory

**Defined:** 2026-03-23
**Core Value:** 用户可以通过 OpenClaw skill 以安全、可配置、可验证的方式完成记忆后端的部署与前端接入，而且整个过程不会把敏感信息硬编码进开源仓库。

## v1 Requirements

### Bootstrap & Topology

- [ ] **BOOT-01**: User can invoke the packaged OpenClaw skill to choose deployment role: `backend`, `frontend`, or `both`
- [ ] **BOOT-02**: User can run guided `init/config` that detects operating system, shell, Docker availability, writable paths, and occupied ports before deployment
- [ ] **BOOT-03**: User can review a deployment plan before the skill or CLI changes local state
- [ ] **BOOT-04**: User can rerun bootstrap safely on an already configured machine without corrupting existing configuration
- [ ] **BOOT-05**: User can complete either same-machine or split-machine setup flow with role-specific instructions

### Configuration & Secrets

- [ ] **CONF-01**: User can set provider, model, and base URL through CLI commands instead of editing source files
- [ ] **CONF-02**: User can generate configuration scaffolding for the selected role and topology
- [ ] **CONF-03**: User can store sensitive configuration separately from non-sensitive configuration
- [ ] **CONF-04**: User can inspect current non-sensitive configuration without exposing secrets in CLI output
- [ ] **CONF-05**: User can override default config and secret storage paths when local environment requires different locations

### Authentication

- [ ] **AUTH-01**: User can configure API key authentication for backend and frontend workflows
- [ ] **AUTH-02**: User can complete OAuth login from CLI using a browser-based flow
- [ ] **AUTH-03**: User can check current authentication status from CLI
- [ ] **AUTH-04**: User can clear or rotate stored credentials from CLI logout or reset flow
- [ ] **AUTH-05**: User never sees refresh tokens or equivalent secrets in exported bundles, logs, or redacted summaries

### Backend Service

- [ ] **BACK-01**: User can deploy the backend service with a Docker-first path on Linux, macOS, and Windows
- [ ] **BACK-02**: Linux user can deploy the backend service with a documented `systemd` path as an alternative to Docker
- [ ] **BACK-03**: User can rerun backend deployment idempotently without breaking an existing healthy install
- [ ] **BACK-04**: User can verify backend health from CLI and receive actionable failure guidance
- [ ] **BACK-05**: Backend service can execute authenticated `search` and `embed` operations against the configured provider and persistence layer

### Connection Handoff

- [ ] **CONN-01**: Backend user can export a versioned redacted connection bundle for split-machine setup
- [ ] **CONN-02**: Redacted connection bundle includes only non-sensitive connection metadata required by the frontend machine
- [ ] **CONN-03**: Frontend user can import the redacted connection bundle and complete local secret entry or resolution
- [ ] **CONN-04**: Frontend user can connect to the backend and verify reachability plus auth compatibility from CLI
- [ ] **CONN-05**: Split-machine flow never exports backend-local bind addresses as frontend connection endpoints

### Verification & Documentation

- [ ] **VERI-01**: User can run end-to-end smoke tests that cover `health`, `search`, and `embed`
- [ ] **VERI-02**: CLI failure output tells the user the next exact command or recovery step
- [ ] **VERI-03**: Project ships a Chinese-first bilingual README that covers same-machine and split-machine usage
- [ ] **VERI-04**: Project ships bilingual operator runbooks for backend deployment, frontend connection, authentication, and troubleshooting
- [ ] **VERI-05**: OpenClaw skill package, backend service, CLI, and connection bundle versions are compatibility-checked for release

## v2 Requirements

### Operator Experience

- **OPER-01**: User can export a redacted diagnostics bundle for support and debugging
- **OPER-02**: User can use reverse-proxy and HTTPS helper templates for remote deployments
- **OPER-03**: User can view service status from an optional read-only UI or TUI

### Data & Profiles

- **DATA-01**: User can run backup and restore workflows from supported tooling
- **DATA-02**: User can maintain multiple frontend connection profiles on one machine
- **DATA-03**: User can access provider-specific tuning assistants for supported models

## Out of Scope

| Feature | Reason |
|---------|--------|
| Automatic migration/import of old private memory data | v1 is deployment-focused; migration guidance is enough without embedding legacy assumptions into OSS code |
| Web admin console | Expands auth and surface area before CLI and runbooks are proven |
| Automatic cross-machine secret sync | High leak risk across platforms; redacted bundle plus local secret entry is safer |
| Multi-node / HA / Kubernetes deployment | Would explode the ops matrix before single-node and split-machine paths are stable |
| Auth modes beyond `apiKey + OAuth` | Support matrix would sprawl too early |
| Unattended firewall, SSH, or network mutation | Too brittle and risky for v1 automation |
| Embedding backend runtime directly inside the skill package | Violates the intended boundary that the skill orchestrates but does not become the backend |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BOOT-01 | TBD | Pending |
| BOOT-02 | TBD | Pending |
| BOOT-03 | TBD | Pending |
| BOOT-04 | TBD | Pending |
| BOOT-05 | TBD | Pending |
| CONF-01 | TBD | Pending |
| CONF-02 | TBD | Pending |
| CONF-03 | TBD | Pending |
| CONF-04 | TBD | Pending |
| CONF-05 | TBD | Pending |
| AUTH-01 | TBD | Pending |
| AUTH-02 | TBD | Pending |
| AUTH-03 | TBD | Pending |
| AUTH-04 | TBD | Pending |
| AUTH-05 | TBD | Pending |
| BACK-01 | TBD | Pending |
| BACK-02 | TBD | Pending |
| BACK-03 | TBD | Pending |
| BACK-04 | TBD | Pending |
| BACK-05 | TBD | Pending |
| CONN-01 | TBD | Pending |
| CONN-02 | TBD | Pending |
| CONN-03 | TBD | Pending |
| CONN-04 | TBD | Pending |
| CONN-05 | TBD | Pending |
| VERI-01 | TBD | Pending |
| VERI-02 | TBD | Pending |
| VERI-03 | TBD | Pending |
| VERI-04 | TBD | Pending |
| VERI-05 | TBD | Pending |

**Coverage:**
- v1 requirements: 30 total
- Mapped to phases: 0
- Unmapped: 30 ⚠️

---
*Requirements defined: 2026-03-23*
*Last updated: 2026-03-23 after initialization*
