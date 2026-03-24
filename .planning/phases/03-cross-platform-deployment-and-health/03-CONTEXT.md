# Phase 3: Cross-Platform Deployment and Health - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning
**Source:** Auto-derived from roadmap, requirements, project research, implemented Phase 1/2 code, and current official Docker/systemd guidance

<domain>
## Phase Boundary

This phase delivers the first real deployment path for the backend service. It covers Docker-first deployment on supported platforms, a Linux `systemd` alternative, idempotent re-run behavior for backend deployment, and CLI health diagnostics that tell the operator exactly what to do next when deployment is unhealthy.

It does not introduce new backend memory features, connection handoff bundles, frontend linking, or release-hardening work. Those remain in later phases.

</domain>

<decisions>
## Implementation Decisions

### Support Matrix and Canonical Deployment Paths
- Docker-first remains the canonical deployment path, but the platform-specific expectation should be explicit:
- macOS and Windows: Docker Desktop is the canonical Docker runtime
- Linux: Docker Engine + Docker Compose plugin is the canonical Docker runtime
- Linux `systemd` is a supported alternative path, not a fallback afterthought
- Do not make Docker Desktop on Linux the primary recommendation because it adds a VM/custom-context layer that complicates a backend service deployment story already covered by Docker Engine and by the Linux-native `systemd` path.

### Deployment Assets and Runtime Packaging
- Phase 3 should add a real containerization surface: Dockerfile, Compose configuration, env templates, and backend startup command wiring.
- Compose must model health explicitly rather than assuming container start equals service readiness.
- Deployment config should preserve the Phase 1/2 config boundary: non-secret config remains human-readable, secret material remains separate, and deployment templates should consume those values rather than duplicating them in ad hoc files.

### Health Model
- Backend health must cover more than “process started”. Phase 3 health should distinguish:
- app reachable
- database reachable
- provider configuration present
- provider remote check optional or deferred
- CLI health output must classify failures into operator-useful buckets and include the next exact command or next exact inspection step.
- Health output should be safe for terminal use and must not echo tokens or raw credentials.

### Rerun and Idempotency
- Re-running Docker deployment should use an idempotent path such as `docker compose up -d` on generated assets rather than deleting and recreating state blindly.
- Re-running `systemd` install should preserve the existing working directory, env file, and data volume locations unless the operator explicitly changes them.
- Health and deploy commands must refuse destructive actions by default.

### Claude's Discretion
- Exact deployment file layout under `deploy/` or similar
- Exact naming of Docker image, Compose project, and systemd unit, as long as names stay consistent
- Exact CLI subcommand shape under `backend`
- Exact health status formatting, provided the next-step outputs remain concrete

</decisions>

<specifics>
## Specific Ideas

- Phase 3 should reuse the already implemented backend app instead of wrapping it with another runner layer.
- The deployment assets should be ready for both local `IP + port` use and later domain/proxy upgrades, but they should not require domain setup to function.
- The CLI should expose at least `backend deploy` and `backend health`, and likely `backend restart`, because restart is operationally adjacent to idempotent reruns and health recovery.
- Systemd support must be documented enough that a Linux user can actually follow it before Phase 5 documentation polish happens.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Scope and Phase Contract
- `.planning/PROJECT.md` — Defines the product boundary, security model, and Docker-first direction.
- `.planning/REQUIREMENTS.md` — Defines the Phase 3 requirement set: `BACK-01..04` and `VERI-02`.
- `.planning/ROADMAP.md` — Defines the fixed Phase 3 goal and success criteria.
- `.planning/STATE.md` — Carries forward open concerns about Windows/macOS deployment ergonomics and health verification gaps.

### Prior Phase Decisions and Code
- `.planning/phases/01-guided-bootstrap-and-safe-configuration/01-CONTEXT.md` — Defines the Phase 1 config/secrets contract and bootstrap/doctor behavior that deployment commands must preserve.
- `.planning/phases/02-authenticated-backend-core/02-CONTEXT.md` — Defines the backend/CLI/auth boundaries Phase 3 must deploy rather than redesign.
- `.planning/phases/02-authenticated-backend-core/02-VERIFICATION.md` — Captures the remaining real-environment checks that deployment work must make easier, not harder.
- `src/transcendence_memory/backend/app.py` — Current backend entry surface.
- `src/transcendence_memory/backend/settings.py` — Existing runtime settings contract.
- `src/transcendence_memory/cli.py` — Current CLI command surface that Phase 3 should extend.

### Research Baseline
- `.planning/research/SUMMARY.md` — Confirms Docker-first and Linux `systemd` secondary path as the intended architecture.
- `.planning/research/PITFALLS.md` — Captures cross-platform automation sprawl and secret-leakage risks.
- Official Docker docs on Compose startup order and health checks — deployment planning must use health-aware dependency wiring rather than start-order assumptions.
- Official Docker install docs for macOS, Windows, and Linux Engine/Compose plugin — used to keep the platform support matrix current.
- Official `systemd.service` guidance — used for `Restart=`, `WorkingDirectory=`, `EnvironmentFile=`, and unit layout expectations.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/transcendence_memory/backend/app.py` — FastAPI app entrypoint ready for container or service startup
- `src/transcendence_memory/backend/api/routes/health.py` — current health route that can be deepened for readiness reporting
- `src/transcendence_memory/backend/settings.py` — typed runtime settings and auth/provider/db URLs
- `src/transcendence_memory/cli.py` — existing `init`, `config`, `doctor`, and `auth` surfaces to extend with `backend deploy` / `backend health`
- `.venv` / pytest workflow and current tests — existing verification harness to extend with deployment-level tests

### Established Patterns
- Python package layout under `src/`
- Config and secrets are already separated
- CLI is the canonical execution surface
- Backend is independently runnable and should stay that way

### Integration Points
- Add deployment helpers under `src/transcendence_memory/deploy/` or equivalent
- Add Docker assets at repository root or under `deploy/docker/`
- Add Linux `systemd` assets under `deploy/systemd/`
- Extend CLI with `backend` commands rather than inventing a second operator interface

</code_context>

<deferred>
## Deferred Ideas

- Connection bundle export/import and remote frontend linking — Phase 4
- Public issue reporting links and release compatibility policy — Phase 5
- Kubernetes or HA deployment paths — explicitly out of scope for this phase

</deferred>

---
*Phase: 03-cross-platform-deployment-and-health*
*Context gathered: 2026-03-24*
