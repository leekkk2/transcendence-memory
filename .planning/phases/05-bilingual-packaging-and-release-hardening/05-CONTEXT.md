# Phase 5: Bilingual Packaging and Release Hardening - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning
**Source:** Auto-derived from roadmap, current repository state, prior phase verification reports, current repository skill-package state, and current official GitHub release hardening guidance

<domain>
## Phase Boundary

This phase turns the project into a releaseable OSS package. It covers a Chinese-first bilingual root README, operator runbooks for deployment/connection/auth/troubleshooting, a version compatibility contract across CLI/backend/skill/bundle, and CI/release hardening checks that can reject unsafe or incompatible releases.

It does not add new product capabilities. It packages, documents, and protects what earlier phases already built.

</domain>

<decisions>
## Implementation Decisions

### Documentation Surface
- The root `README.md` should become the primary OSS landing page and must be Chinese-first bilingual.
- README should explicitly mention that the project was inspired in part by `memory-lancedb-pro`, as already required at the project level.
- README should cover both same-machine and split-machine usage, but it should not duplicate all runbook detail; it should route into focused docs.
- Operator runbooks should be split by topic rather than mixed into one monolithic document:
- backend deployment
- frontend handoff/import
- authentication
- troubleshooting

### Packaging and Release Boundary
- The OSS package boundary is wider than the OpenClaw skill itself. Phase 5 should document and verify:
- root project package
- CLI/runtime code
- skill package under `transcendence-memory/`
- bundle version compatibility
- A release compatibility manifest should exist in-repo so release checks do not depend on tribal knowledge or manual diffing.

### CI and Hardening
- Release hardening should assume a future public GitHub-hosted path even though the current repository does not yet have a remote configured.
- CI workflows should follow current GitHub hardening guidance:
- pin third-party actions by full commit SHA
- run dependency/review-style checks
- include secret-leak and compatibility checks
- keep release automation explicit rather than implicitly pushing from arbitrary branch state
- Secret scanning and push-protection guidance should be reflected in docs and CI checks, but Phase 5 should not pretend that hosted secret-scanning features exist locally.

### Claude's Discretion
- Exact docs folder structure beneath `docs/`
- Exact compatibility manifest format, as long as it clearly covers skill/CLI/backend/bundle compatibility
- Exact workflow file split under `.github/workflows/`

</decisions>

<specifics>
## Specific Ideas

- The skill package already exists in-repo, so Phase 5 should account for the repository-local canonical skill surface.
- Root docs are currently minimal, so README and runbooks are the main Phase 5 functional deliverables.
- Current Phase 2/3/4 verification reports already define the real-environment checks that runbooks should surface rather than hide.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Scope and Phase Contract
- `.planning/PROJECT.md` — Defines Chinese-first bilingual docs, MIT license, and the public OSS packaging intent.
- `.planning/REQUIREMENTS.md` — Defines the Phase 5 requirement set: `VERI-03..05`.
- `.planning/ROADMAP.md` — Defines the fixed Phase 5 goal and success criteria.
- `.planning/STATE.md` — Carries forward the pending human-verification todos and the current project state.

### Prior Phase Verification Reports
- `.planning/phases/02-authenticated-backend-core/02-VERIFICATION.md` — Lists the real auth/provider/manual verification gaps that public docs must explain.
- `.planning/phases/03-cross-platform-deployment-and-health/03-VERIFICATION.md` — Lists the real Docker/systemd verification steps that release docs must surface.
- `.planning/phases/04-secure-connection-handoff-and-verification/04-VERIFICATION.md` — Lists the real cross-machine handoff and smoke checks that docs must preserve.

### Current Publication and Package Surfaces
- `README.md` — Current minimal root landing page that Phase 5 must replace with a full bilingual OSS entry point.
- `transcendence-memory/SKILL.md` — Current in-repo canonical skill package entry point.
- `transcendence-memory/references/bootstrap.md` and `transcendence-memory/references/troubleshooting.md` — Existing skill-level docs that Phase 5 should align with, not contradict.
- `deploy/docker/backend.env.example`, `deploy/systemd/README.md` — Existing deploy assets that Phase 5 runbooks must reference.

### Hardening Guidance
- Official GitHub docs for GitHub Actions security hardening, including pinning actions by full commit SHA.
- Official GitHub docs for dependency review / supply-chain checks.
- Official GitHub docs for secret scanning and push protection concepts.
- Official GitHub docs for artifact attestations and release integrity guidance.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `transcendence-memory/` skill package already exists and is the repository-local canonical skill surface
- `deploy/docker/` and `deploy/systemd/` already provide concrete operator targets
- verification reports in `.planning/phases/02-*`, `.planning/phases/03-*`, `.planning/phases/04-*` already enumerate the real manual checks docs should reference

### Established Patterns
- Chinese-first bilingual style is already present in the skill references
- CLI is the canonical operator surface
- Verification is already documented via phase reports rather than hidden in code comments

### Integration Points
- Add root docs under `docs/`
- Add release/compatibility manifests under a stable path such as `docs/release/` or `compat/`
- Add CI workflows under `.github/workflows/`
- Extend root README and MIT license in repo root

</code_context>

<deferred>
## Deferred Ideas

- Automated publication to external registries or skill hubs
- Advanced SBOM/attestation publication to registries beyond the initial CI proof path
- Multi-channel release orchestration across multiple remotes

</deferred>

---
*Phase: 05-bilingual-packaging-and-release-hardening*
*Context gathered: 2026-03-24*
