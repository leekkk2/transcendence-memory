# Phase 4: Secure Connection Handoff and Verification - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning
**Source:** Auto-derived from roadmap, prior phase outputs, current code, and existing research

<domain>
## Phase Boundary

This phase delivers the secure handoff layer between backend and frontend machines. It covers generating a versioned redacted connection bundle, ensuring only public or advertised connection metadata is exported, importing that bundle on the frontend side, resolving secrets locally, and verifying the full path with end-to-end `health`, `search`, and `embed` smoke checks.

It does not redesign deployment, authentication fundamentals, or release packaging. Those were handled in earlier or later phases.

</domain>

<decisions>
## Implementation Decisions

### Bundle and Handoff Shape
- Phase 4 should introduce a typed connection bundle model with explicit versioning.
- The bundle must contain only non-sensitive metadata needed by the receiving machine:
- backend URL / advertised endpoint
- auth mode metadata
- provider/model/base URL metadata where safe
- capability/version metadata needed for compatibility checks
- The bundle must never include API keys, access tokens, refresh tokens, or local-only secret file contents.

### Public URL and Address Safety
- Export must distinguish bind/listen addresses from advertised/public addresses.
- If the backend is configured only with a local bind address, export must not silently claim that it is safe for a remote frontend machine.
- The export path should sanitize or reject local-only addresses like `127.0.0.1` and container-local hostnames when the bundle is intended for split-machine use.
- Same-machine flow can use local addresses, but split-machine exports must either:
- use an explicitly advertised public URL
- or fail safely with actionable guidance

### Frontend Import and Local Secret Resolution
- `frontend import-connection` should persist only non-secret bundle data into normal config.
- Any secret or auth material required on the frontend must be entered or resolved locally after import; it cannot be imported from the bundle.
- `frontend check` should verify that the imported metadata, local auth state, and backend reachability line up.

### Smoke Verification
- Phase 4 should add a dedicated verification surface that exercises:
- backend health
- authenticated `embed`
- authenticated `search`
- Smoke verification should support both same-machine and split-machine scenarios, with environment-gated integration tests where real backends/providers are needed.

### Claude's Discretion
- Exact bundle field names, as long as the distinction between safe metadata and local secrets is explicit
- Exact CLI subcommand structure for backend export vs frontend import/check
- Exact smoke-test helper layout and naming

</decisions>

<specifics>
## Specific Ideas

- The backend export command should be explicit, likely `backend export-connection`.
- The frontend side should have a clear import path, likely `frontend import-connection`, plus `frontend check`.
- Bundle import/export should be easy for AI-to-AI handoff via copy/paste, but should not encourage secret copying.
- The smoke-check output should be machine-readable enough for AI guidance and human-readable enough for operators.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Scope and Phase Contract
- `.planning/PROJECT.md` — Defines the product boundary, secure redacted bundle requirement, and split-machine expectations.
- `.planning/REQUIREMENTS.md` — Defines the Phase 4 requirement set: `CONN-01..05` and `VERI-01`.
- `.planning/ROADMAP.md` — Defines the fixed Phase 4 goal and success criteria.
- `.planning/STATE.md` — Captures the known open concern around public URL and TLS contract finalization.

### Prior Phase Context
- `.planning/phases/01-guided-bootstrap-and-safe-configuration/01-CONTEXT.md` — Establishes config/secrets separation and local path behavior.
- `.planning/phases/02-authenticated-backend-core/02-CONTEXT.md` — Establishes auth model and backend route boundaries.
- `.planning/phases/02-authenticated-backend-core/02-VERIFICATION.md` — Captures the remaining human checks around real auth/provider usage that smoke verification must make easier.
- `.planning/phases/03-cross-platform-deployment-and-health/03-CONTEXT.md` — Establishes Docker/systemd deployment and health semantics Phase 4 must consume rather than replace.
- `.planning/phases/03-cross-platform-deployment-and-health/03-VERIFICATION.md` — Captures the real-environment deployment checks that affect split-machine handoff safety.

### Current Code Surfaces
- `src/transcendence_memory/cli.py` — Existing CLI surface to extend with `backend export-connection`, `frontend import-connection`, and `frontend check`.
- `src/transcendence_memory/backend/settings.py` — Existing runtime metadata source for public URL, auth mode, provider, and database-backed service settings.
- `src/transcendence_memory/deploy/health.py` — Existing health classification surface to reuse in smoke verification.
- `src/transcendence_memory/backend/api/routes/memory.py` — Existing authenticated `embed` and `search` endpoints to target for smoke checks.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/transcendence_memory/bootstrap/models.py` and `persistence.py` — existing config/secrets split and versioned config state
- `src/transcendence_memory/backend/settings.py` — existing advertised URL / auth / provider metadata source
- `src/transcendence_memory/cli.py` — existing auth and backend command groups
- `src/transcendence_memory/deploy/health.py` — existing health probing and operator command guidance

### Established Patterns
- Non-secret metadata and secret state are intentionally separated
- CLI is the canonical operator surface
- Backend routes are narrow and authenticated
- Health output is already structured and operator-oriented

### Integration Points
- Add bundle schema/helpers under a new shared or deploy-related module
- Extend CLI with backend export and frontend import/check commands
- Add smoke verification helpers that call existing health and memory routes
- Extend tests with bundle safety, import/check flows, and smoke coverage

</code_context>

<deferred>
## Deferred Ideas

- Final release compatibility policy and public docs polish — Phase 5
- Full remote TLS/certificate automation — remains outside this phase unless needed purely for metadata contracts

</deferred>

---
*Phase: 04-secure-connection-handoff-and-verification*
*Context gathered: 2026-03-24*
