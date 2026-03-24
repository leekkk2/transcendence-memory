# Phase 3 Research: Cross-Platform Deployment and Health

**Project:** Transcendence Memory
**Phase:** 3
**Researched:** 2026-03-24
**Confidence:** Medium-High

## Objective

Answer the planning question for Phase 3 only:

What does the planner need to know to create strong implementation plans for Docker-first backend deployment, Linux `systemd` support, idempotent reruns, and operator-friendly health diagnostics across Linux, macOS, and Windows?

## Official Guidance That Changes Planning

### Docker Compose and health-aware startup

Current Docker Compose guidance makes one point especially important for this phase: startup order alone is not enough. Compose can express dependency ordering, but meaningful service readiness still requires explicit health checks and health-aware dependency wiring.

Planning implication:
- Phase 3 should not stop at “backend container starts”
- Compose assets must include concrete health checks
- dependent service startup should key off health/readiness rather than naive start order

### Platform support matrix

The deployment story should be platform-specific, not hand-wavy:
- macOS: Docker Desktop is the realistic operator path
- Windows: Docker Desktop with WSL2-backed workflow is the realistic operator path
- Linux: Docker Engine + Compose plugin is the better primary backend deployment path, with `systemd` as the explicit native alternative

Planning implication:
- do not write a single “Docker everywhere” story that assumes the same installation/runtime environment across all OSes
- make the support matrix explicit in code and docs
- avoid coupling Phase 3 to Docker Desktop-only behavior that does not map cleanly to Linux

### systemd unit behavior

The core `systemd.service` guidance reinforces a few concrete unit-file needs:
- use absolute `WorkingDirectory=`
- use `EnvironmentFile=` where runtime values are externalized
- use explicit `ExecStart=` and `ExecStop=`
- use a restart policy such as `Restart=on-failure` for long-running services

Planning implication:
- Phase 3’s Linux path should include a real unit file and an env file template
- plan for a script or CLI path that writes those artifacts deterministically
- do not hand-wave the systemd path as “document later”

## Existing Code Implications

Phase 2 already delivered:
- a FastAPI backend app
- runtime settings for database/provider/auth configuration
- authenticated routes
- a narrow health route

That means Phase 3 should not rebuild runtime configuration or auth. Instead it should package and operate what already exists.

Key implication:
- the deploy code should treat `src/transcendence_memory/backend/app.py` as the service entrypoint
- health logic should deepen the existing route and CLI, not replace them

## Planning Conclusions

### 1. Split Docker assets from CLI orchestration

The planner should separate:
1. container/runtime assets
2. Compose topology and health checks
3. CLI deployment and rerun logic
4. Linux systemd assets
5. deployment verification and support-matrix tests/docs

This avoids the common failure mode where the CLI grows first and later has to be rewritten when the container layout changes.

### 2. Treat health as a layered diagnostic model

Phase 3 health should distinguish:
- process reachable
- database reachable
- provider configuration present
- provider live check optional

Recommended CLI outputs should include exact follow-up commands, for example:
- `docker compose logs backend --tail=100`
- `docker compose ps`
- `systemctl status transcendence-memory-backend`
- `journalctl -u transcendence-memory-backend -n 100`

The planner should make those strings explicit in tasks and tests instead of leaving them as generic “next steps”.

### 3. Prefer deterministic artifact generation over handwritten local edits

The deployment path should generate or render:
- `.env` or env template files
- compose configuration
- systemd env file
- unit file

That gives rerun/idempotency something concrete to diff against.

Planning implication:
- at least one plan should add render/generation helpers rather than hard-coding operator edits

### 4. Rerun safety should be plan-level, not an afterthought

Phase 3 must satisfy idempotent rerun requirements explicitly.

Recommended behavior:
- `backend deploy` checks for existing deployment artifacts
- it renders desired state
- it shows whether this is create/update/no-op
- it uses idempotent operations such as `docker compose up -d`
- it avoids deleting volumes or data unless the user explicitly requests destructive cleanup

### 5. Linux systemd path should be a real alternative, not a wrapper around Docker

Because the roadmap explicitly calls out Linux `systemd` as a supported alternative, the planner should make it a real native path:
- backend app started directly through a Python/venv or equivalent launch command
- unit file, env file, and working directory all explicit
- restart policy and logs integrated with systemd/journalctl

Avoid:
- systemd unit that just shells out to Docker Compose without clear rationale

### 6. Phase 3 tests should focus on rendered artifacts and operator outputs

Real cross-platform deployment cannot be fully executed in CI or the current local environment, so the useful automated coverage should focus on:
- Docker/Compose file rendering
- systemd unit/env rendering
- CLI health classification and next-step outputs
- idempotent plan generation for reruns
- API-level health route expansion

Real Docker and systemd smoke tests are still valuable, but they will remain partly environment-gated.

## Recommended Support Matrix for Planning

### Official Phase 3 path

- **macOS:** Docker Desktop + `docker compose`
- **Windows:** Docker Desktop + `docker compose`
- **Linux:** Docker Engine + Docker Compose plugin
- **Linux alternative:** native `systemd` service path

### Explicit non-goals for Phase 3

- Docker Desktop for Linux as the main recommended path
- Kubernetes
- multi-node or HA deployment
- zero-touch remote exposure setup

## Validation Architecture

Phase 3 should keep a formal validation strategy, but much of it will be artifact- and CLI-output-based.

Recommended validation layers:
- unit tests for deploy config rendering and systemd rendering
- CLI tests for `backend deploy`, `backend health`, and rerun/no-op behavior
- API tests for deepened health route
- environment-gated integration tests for Docker/Compose smoke paths where feasible

Suggested new test files:
- `tests/unit/test_deploy_config.py`
- `tests/unit/test_systemd_render.py`
- `tests/cli/test_backend_deploy_command.py`
- `tests/cli/test_backend_health_command.py`
- `tests/api/test_backend_health_route.py`
- `tests/integration/test_compose_smoke.py`

## Recommended Sources of Truth for Planning

- `.planning/phases/03-cross-platform-deployment-and-health/03-CONTEXT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`
- `.planning/phases/02-authenticated-backend-core/02-VERIFICATION.md`
- `src/transcendence_memory/backend/app.py`
- `src/transcendence_memory/backend/settings.py`
- `src/transcendence_memory/cli.py`

## Sources Used

- Docker official docs on Compose startup order and health checks
- Docker official install guidance for Docker Desktop on macOS/Windows and Docker Engine/Compose on Linux
- `systemd.service` official guidance on unit structure and restart behavior
- local Transcendence Memory Phase 1/2 code and planning artifacts

---
*Phase research completed: 2026-03-24*
*Ready for planning: yes*
