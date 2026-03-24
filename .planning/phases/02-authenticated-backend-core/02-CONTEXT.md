# Phase 2: Authenticated Backend Core - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning
**Source:** Auto-derived from roadmap, requirements, project research, and Phase 1 implementation

<domain>
## Phase Boundary

This phase delivers the first real backend runtime for Transcendence Memory. It covers the authenticated backend service, API-key and OAuth CLI flows, PostgreSQL + pgvector persistence, and the first end-to-end `search` / `embed` operations against the configured provider.

It does not include deployment orchestration, Docker/systemd rollout UX, connection bundle export/import, remote verification handoff, or release hardening. Those remain in later phases.

</domain>

<decisions>
## Implementation Decisions

### Backend and CLI Boundary
- Keep the product boundary established in Phase 1: the backend is an independently runnable service, and the CLI is the operator control plane.
- Phase 2 should extend the existing Typer CLI instead of introducing a second command surface.
- Introduce a backend package under `src/transcendence_memory/backend/` (or equivalent internal namespace) rather than mixing runtime server code into the bootstrap modules.

### Authentication Shape
- Support both `apiKey` and OAuth in Phase 2, because both are explicit v1 requirements.
- API key support should be the simpler machine-oriented path for backend/frontend workflows and should integrate cleanly with the existing secret-file pattern from Phase 1.
- OAuth should use a browser-based native-app flow with PKCE and a loopback redirect on `127.0.0.1`, not an implicit flow.
- `auth status` and `auth logout` must be CLI-level commands and must never print refresh tokens or equivalent secrets.
- Token or API-key material must remain in secret storage only, not in non-secret config, logs, dry-run output, or summaries.

### Backend API and Persistence
- PostgreSQL + pgvector is authoritative and should not be replaced by a local embedded vector store in this phase.
- The backend should expose a health endpoint plus authenticated memory operations for `search` and `embed`.
- `embed` should call the configured provider/model, store the resulting embedding plus content/metadata in PostgreSQL, and return a stable record identifier.
- `search` should embed the query, execute vector similarity search in PostgreSQL + pgvector, and return ranked records plus metadata.

### Phase 2 Testing and Verification
- Phase 2 needs backend-focused tests, not just CLI-only tests. Include API tests, auth-state tests, and persistence tests.
- Use a mix of unit tests and integration tests; integration must prove real PostgreSQL + pgvector behavior rather than stopping at mocks.
- CLI auth output should be redacted by design so verification can assert token absence, not just happy-path success.

### Claude's Discretion
- Exact backend module layout beneath the backend package
- Exact table and column names, as long as they clearly support memory records, vectors, and auth state
- Exact request/response model names for search and embed endpoints
- Exact route prefixes and middleware composition, as long as auth and persistence boundaries stay explicit

</decisions>

<specifics>
## Specific Ideas

- Reuse the Phase 1 config/secrets contract instead of inventing a second storage mechanism for auth state.
- Extend the CLI with `auth login`, `auth status`, and `auth logout`, plus backend-facing commands that can target the new service.
- Treat OAuth provider support as OIDC-capable where possible so the CLI is not hard-wired to one vendor contract.
- Keep `search` and `embed` intentionally narrow in Phase 2: enough to prove authenticated backend behavior and persistence, not a full memory product surface.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Scope and Phase Contract
- `.planning/PROJECT.md` — Defines the core product boundary, security rules, and the v1 auth surface.
- `.planning/REQUIREMENTS.md` — Defines the Phase 2 requirement set: `AUTH-01..05` and `BACK-05`.
- `.planning/ROADMAP.md` — Defines the fixed Phase 2 goal and success criteria.
- `.planning/STATE.md` — Carries forward the phase-ordering risks and open concerns, especially OAuth scope and remote-safe auth behavior.

### Prior Phase Decisions
- `.planning/phases/01-guided-bootstrap-and-safe-configuration/01-CONTEXT.md` — Defines the skill/CLI boundary, config/secrets storage rules, rerun behavior, and doctor expectations that Phase 2 must preserve.
- `.planning/phases/01-guided-bootstrap-and-safe-configuration/01-RESEARCH.md` — Documents the Phase 1 planning assumptions and the shared package/test structure now present in the codebase.

### Research Baseline
- `.planning/research/SUMMARY.md` — Summarizes the recommended stack and explicitly calls out browser + PKCE OAuth, pgvector persistence, and secret-safe boundaries.
- `.planning/research/STACK.md` — Provides the Python/FastAPI/SQLAlchemy/Alembic/Authlib/pgvector direction that Phase 2 should now instantiate.
- `.planning/research/PITFALLS.md` — Captures the auth and secret-handling mistakes that Phase 2 must actively avoid.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/transcendence_memory/cli.py` — Canonical Typer CLI entry surface that should be extended with auth/backend commands.
- `src/transcendence_memory/bootstrap/models.py` — Typed enums and config models that already encode role/topology/provider basics.
- `src/transcendence_memory/bootstrap/persistence.py` — Existing non-secret config plus secret storage contract that should hold auth state too.
- `src/transcendence_memory/bootstrap/paths.py` — Platform-aware config and secret path helpers that Phase 2 should reuse directly.
- `tests/` — Existing pytest structure and CLI testing pattern that Phase 2 should extend instead of replacing.

### Established Patterns
- Python monorepo with `src/` layout and Typer-based CLI
- Pydantic models as the typed contract layer
- Config and secrets are already intentionally separated
- Tests run through pytest and currently validate CLI/bootstrap contracts

### Integration Points
- Add backend runtime code under `src/transcendence_memory/backend/`
- Extend `src/transcendence_memory/cli.py` with auth/backend command groups
- Extend persistence models for auth metadata and backend connection config
- Add new tests under `tests/unit`, `tests/cli`, and `tests/integration` for auth/backend flows

</code_context>

<deferred>
## Deferred Ideas

- Deployment automation and backend service rollout UX — Phase 3
- Connection bundle export/import and second-machine auth handoff — Phase 4
- Release compatibility checks and public issue-routing guidance — Phase 5

</deferred>

---
*Phase: 02-authenticated-backend-core*
*Context gathered: 2026-03-24*
