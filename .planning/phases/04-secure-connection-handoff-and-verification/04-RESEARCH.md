# Phase 4 Research: Secure Connection Handoff and Verification

**Project:** Transcendence Memory
**Phase:** 4
**Researched:** 2026-03-24
**Confidence:** Medium

## Objective

Answer the Phase 4 planning question:

What does the planner need to know to create strong implementation plans for redacted connection bundle export/import, public-endpoint safety, frontend verification, and end-to-end smoke testing without leaking secrets or local-only addresses?

## Existing Code Implications

The codebase already has:
- backend auth and memory routes
- deployment and health helpers
- a CLI with `auth` and `backend` command groups
- a config/secrets split established in Phase 1

That means Phase 4 should build on current operators:
- export bundle metadata from existing runtime/config state
- import non-secret bundle data into frontend config
- keep all secret resolution local to the receiving machine
- verify via existing `/health`, `/embed`, and `/search` surfaces

## Planning Conclusions

### 1. Bundle model should be a first-class typed contract

Do not treat the connection bundle as a loosely structured dict dumped to JSON.

Recommended bundle sections:
- `bundle_version`
- `generated_at`
- `topology`
- `backend`
  - `advertised_url`
  - `health_path`
  - `memory_paths`
- `auth`
  - `mode`
  - `required_local_inputs`
- `provider`
  - `provider`
  - `model`
  - `base_url`
- `compatibility`
  - `backend_version`
  - `bundle_version`

This gives Phase 5 a stable compatibility surface later.

### 2. Export safety must validate destination suitability

The most important planning rule in this phase is simple:
- same-machine export can tolerate local endpoints
- split-machine export must reject local-only endpoints unless an advertised/public endpoint is configured

Recommended export validation:
- reject `127.0.0.1`
- reject `localhost`
- reject Docker-internal names for split-machine bundles
- allow those values only when topology is same-machine

### 3. Import should never carry auth secrets across machines

The import flow should:
- parse and validate bundle version
- persist non-secret metadata to config
- prompt or instruct for local secret resolution
- update frontend-local auth mode metadata only after local secret setup

Do not:
- write tokens from the bundle
- treat bundle import as auth completion

### 4. Smoke tests should reuse the current service contract

Phase 4 should not invent a new verification API.

Use the existing:
- `/api/v1/health`
- `/api/v1/memory/embed`
- `/api/v1/memory/search`

Recommended smoke stages:
1. health reachable
2. auth works
3. embed works
4. search returns expected shape

### 5. Split-machine flow needs a frontend profile concept

The frontend import path should likely persist an imported connection profile, even if only one profile exists initially.

Why:
- import is semantically different from backend bootstrap
- it keeps bundle state separate from backend-only config
- later multi-profile support can build on a stable shape

## Validation Architecture

Phase 4 validation should center on:
- bundle redaction tests
- public endpoint sanitization tests
- CLI export/import/check tests
- smoke command tests with mocked backend/provider paths
- environment-gated integration tests for real same-machine and split-machine flows

Suggested new test files:
- `tests/unit/test_connection_bundle.py`
- `tests/unit/test_endpoint_sanitization.py`
- `tests/cli/test_backend_export_connection.py`
- `tests/cli/test_frontend_import_connection.py`
- `tests/cli/test_frontend_check.py`
- `tests/cli/test_smoke_command.py`
- `tests/integration/test_same_machine_smoke.py`
- `tests/integration/test_split_machine_bundle_flow.py`

## Recommended Plan Split

The planner should likely split Phase 4 into:
1. shared bundle schema and sanitization
2. backend export command
3. frontend import/check command path
4. smoke verification helpers and CLI

That is enough separation to keep write scopes and test responsibilities clear.

## Sources Used

- Local phase requirements and roadmap
- Phase 2 and Phase 3 verification reports
- Current CLI, backend settings, and health/memory route implementations

---
*Phase research completed: 2026-03-24*
*Ready for planning: yes*
