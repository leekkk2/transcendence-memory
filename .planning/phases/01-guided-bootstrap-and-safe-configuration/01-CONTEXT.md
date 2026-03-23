# Phase 1: Guided Bootstrap and Safe Configuration - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase defines how users begin with Transcendence Memory, choose a machine role and topology, preview intended changes, generate safe local configuration, and recover from bootstrap/configuration problems. It covers the skill-led guidance flow, the canonical CLI entrypoints, config versus secret separation, idempotent re-run behavior, and bootstrap-level diagnostics.

It does not expand into backend runtime implementation, detailed OAuth provider behavior, redacted connection bundle exchange, or release-site integrations. Those belong to later phases.

</domain>

<decisions>
## Implementation Decisions

### Entry Surface and Bootstrap Flow
- The `transcendence-memory` OpenClaw skill is the primary entrypoint for users and AI operators.
- The skill should guide the operator through setup using skill documentation and structured prompts, then invoke the CLI for actual state changes.
- The CLI is the canonical execution surface. The baseline command family starts with `transcendence-memory init backend`, `transcendence-memory init frontend`, and `transcendence-memory init both`.
- Bootstrap should perform environment detection first, then recommend a role and topology based on the detected machine state, while still letting the user make the final choice.
- The default novice path should recommend `both` plus same-machine deployment so users can reach a working setup with the least friction.
- When the user does not provide domain or reverse-proxy information, bootstrap should continue with a working `IP + port` path instead of blocking, then clearly show the upgrade path for domain and proxy setup later.

### Plan, Confirm, Execute, Verify
- Bootstrap must follow a visible workflow: `detect -> recommend -> choose -> plan -> confirm -> execute -> verify`.
- The plan view should group intended actions into prereq checks, file/path changes, secret storage creation, deployment/runtime actions, and post-setup verification.
- Read-only detection and dry-run planning may run without confirmation.
- Any action that installs packages, starts containers or services, writes outside the selected config area, or changes externally visible network settings requires explicit user confirmation.
- Reverse-proxy or domain-related setup should be a guided branch rather than part of the default path. If those inputs are missing, the installer should complete the local/IP-based path and record what remains optional.
- Verification at the end of Phase 1 should focus on bootstrap completeness: chosen role/topology recorded, config scaffolding created, secret storage separated, and next commands made obvious.

### Configuration and Secret Storage
- Use one human-readable non-secret config file as the canonical local state for role, topology, endpoints, provider, model, paths, and defaults.
- Store secrets separately from the normal config file. The bootstrap contract should assume a local-only secret path with locked-down permissions rather than mixing secrets into the main config.
- The CLI should show users where config and secret files are stored, but never print secret values.
- Default storage locations should follow platform conventions instead of repository-root files:
- Linux: XDG-style config location
- macOS: `~/Library/Application Support/...`
- Windows: `%APPDATA%/...`
- CLI flags should allow overriding both config and secret storage paths when needed.
- Generated configuration should be role-aware. `backend`, `frontend`, and `both` should share a stable schema but scaffold different sections and comments by default.

### Re-run, Doctor, and Bootstrap-Level Testing
- Re-running `init` should detect existing local state, calculate a diff-style plan, and ask before overwriting non-secret config or changing secret paths.
- Safe, non-destructive fixes such as creating missing directories, regenerating missing non-secret config, fixing file permissions, and revalidating path choices may be offered automatically or through `doctor --fix`.
- `doctor` in this phase is a bootstrap/configuration doctor, not a full backend runtime doctor. It should cover prereqs, config validity, writable paths, missing secret files, obvious port conflicts, and Docker availability.
- `doctor` output should classify findings as `auto-fixable`, `needs input`, or `manual follow-up`, and it should provide the next exact command whenever possible.
- Phase 1 should include simple test coverage for role selection, topology branching, dry-run planning, secret separation, idempotent re-run behavior, and fallback to `IP + port` when richer networking inputs are absent.

### Claude's Discretion
- Exact prompt wording in the skill and CLI
- Exact file names within the selected config directory, as long as secret and non-secret state remain separated
- Exact formatting of plan output, confirmation prompts, and `doctor` diagnostics
- Exact test helper naming and bootstrap test layout

</decisions>

<specifics>
## Specific Ideas

- The user wants the skill itself to be the main installation and guidance surface for AI-assisted setup.
- The user explicitly wants command-line parity via `transcendence-memory init backend|frontend|both`.
- Docker or automation scripts should be the preferred way to install or deploy wherever possible.
- If the setup flow requires domain, reverse proxy, or Nginx information, the AI should ask for it; if the user does not provide it, the flow should keep moving with `IP + port`.
- The project should include simple tests that validate the bootstrap experience, not just code correctness.
- The user wants a `doctor` command for common setup problems; issue-reporting links to GitHub can be added later when the repository is publicly published.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Scope and Phase Contract
- `.planning/PROJECT.md` — Defines the product boundary, security expectations, packaging rules, bilingual documentation requirements, and the rule that the skill orchestrates but does not become the backend.
- `.planning/REQUIREMENTS.md` — Defines the Phase 1 requirement set: `BOOT-01..05` and `CONF-01..05`.
- `.planning/ROADMAP.md` — Defines the fixed Phase 1 goal and success criteria for guided bootstrap and safe configuration.

### Research Baseline
- `.planning/research/SUMMARY.md` — Summarizes the recommended product pattern: thin skill, thick CLI, independent backend, Docker-first topology, and secret-safe bootstrap.
- `.planning/research/FEATURES.md` — Captures table-stakes expectations for guided bootstrap, topology-aware setup, secure secret handling, and operator-facing CLI flows.
- `.planning/research/PITFALLS.md` — Captures risks to avoid during planning, especially secret leakage, role confusion, local-only endpoint export, and cross-platform automation sprawl.
- `.planning/research/STACK.md` — Provides the recommended stack assumptions for CLI/config tooling and cross-platform deployment helpers.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None yet — the repository currently contains planning artifacts only and no implementation code, scripts, or packaged skill assets.

### Established Patterns
- Planning is contract-first: user-facing boundaries and safety rules are expected to be fixed before runtime implementation begins.
- The project already commits to a thin skill, thick CLI, independent backend model, so Phase 1 should not create logic that collapses those boundaries.
- Docker-first plus Linux `systemd` secondary path is already established, so bootstrap logic should prepare for both without making Linux-native behavior the default everywhere.

### Integration Points
- Future skill package entrypoint under a dedicated skill directory with `SKILL.md`, `scripts/`, `references/`, and `assets/`.
- Future CLI command surface rooted at `transcendence-memory ...`.
- Future local config and secret storage outside the repository root, using platform-appropriate paths and override flags.

</code_context>

<deferred>
## Deferred Ideas

- Full backend runtime remediation beyond bootstrap/config validation — belongs with Phase 3 deployment and health work.
- Redacted connection bundle UX and second-machine import flow details — belong in Phase 4.
- Published GitHub issue link integration for `doctor` or support output — add after the repository has a stable public issue URL, likely in Phase 5.

</deferred>

---
*Phase: 01-guided-bootstrap-and-safe-configuration*
*Context gathered: 2026-03-23*
