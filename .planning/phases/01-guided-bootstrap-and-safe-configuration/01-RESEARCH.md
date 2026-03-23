# Phase 1 Research: Guided Bootstrap and Safe Configuration

**Project:** Transcendence Memory
**Phase:** 1
**Researched:** 2026-03-23
**Confidence:** Medium-High

## Objective

Answer the planning question for Phase 1 only:

What does the planner need to know to create strong implementation plans for bootstrap, role/topology selection, safe local configuration, rerun handling, and bootstrap-level diagnostics, without leaking into backend runtime or connection-handoff work that belongs in later phases?

## Phase Boundary Reminder

Phase 1 is the contract and operator-experience baseline. It must let users or AI operators:
- start from the OpenClaw skill or CLI
- choose `backend`, `frontend`, or `both`
- choose same-machine or split-machine
- inspect a concrete plan before mutating local state
- create role-aware non-secret config plus separate secret storage
- rerun setup safely
- use a bootstrap-level `doctor`

Phase 1 should not implement:
- backend runtime behavior
- OAuth protocol completion
- redacted connection bundle export/import
- release hardening or public issue reporting

Those belong to later phases even if some command names are introduced now.

## Planning Conclusions

### 1. Keep the skill thin and the CLI authoritative

The planning baseline should preserve the already-agreed product boundary:
- `transcendence-memory` skill is the operator-facing guide and AI-friendly index
- the CLI is the state-changing execution surface
- Phase 1 should establish the CLI contract early because later deployment, auth, and handoff phases depend on stable command semantics

Implication for planning:
- do not make the skill contain imperative deployment logic
- do make the skill references, examples, and prompts call the canonical CLI commands
- treat skill work and CLI work as separate but coordinated deliverables

### 2. Model role and topology explicitly, not infer them late

The planner should treat `role` and `topology` as first-class typed concepts, not loose strings passed around ad hoc.

Recommended Phase 1 contract:
- `role`: `backend | frontend | both`
- `topology`: `same_machine | split_machine`
- `transport_hint`: `ip_port | domain_proxy`
- `mode`: `interactive | auto_recommended`

The bootstrap flow should:
1. inspect environment
2. infer likely recommendations
3. present recommendation plus rationale
4. let user override
5. persist the selected role/topology into non-secret config

Implication for planning:
- create schema/model work before CLI prompt work
- treat the recommendation engine as deterministic and inspectable
- record recommendation reason strings so `doctor` and rerun can explain why a previous path was chosen

### 3. Use platform-native config roots and separate secret roots

Phase 1 should lock down the config/secrets layout because later phases must build on it without migration churn.

Recommended path strategy:
- use `platformdirs` for all user data roots
- keep non-secret config in a human-readable file under the platform config directory
- keep secret material in a separate file path under a secret-oriented subdirectory with permission enforcement

Recommended logical layout:

```text
<config_root>/transcendence-memory/
  config.toml
  state.json
  doctor-report.json

<config_root>/transcendence-memory/profiles/default/
  role.toml
  topology.toml

<secret_root>/transcendence-memory/
  secrets.toml
```

Platform roots:
- Linux: XDG config and state conventions
- macOS: `~/Library/Application Support/transcendence-memory/`
- Windows: `%APPDATA%\\transcendence-memory\\`

Why this is preferable in Phase 1:
- avoids repository-root leakage
- supports rerun diffing against stable files
- makes docs clearer for users and AI
- preserves a visible path contract without printing secrets

Important constraint:
- avoid OS-keyring-only behavior in Phase 1 because the user explicitly wants path-based config visibility; keyring can remain a later enhancement

### 4. Plan output should be a real mutation plan, not just a summary

The research and user context converge on one operator requirement: no black-box install behavior.

Phase 1 should therefore implement a real plan object, not a prose preview.

Recommended plan sections:
- environment findings
- chosen role/topology
- files and directories to create
- secrets path to initialize
- config keys to set or update
- warnings requiring user attention
- deferred setup items, such as domain/Nginx configuration not provided
- post-bootstrap verification commands

Planning implication:
- create a typed plan model plus renderer before writing final CLI commands
- keep plan generation dry-run-capable by default
- ensure rerun uses a diff between current local state and desired state

### 5. Rerun must be diff-based and conservative

Phase 1 should not treat rerun as a reinitialize-from-scratch event.

Recommended rerun behavior:
- detect existing local config and secret paths
- compute desired changes
- show a diff-style plan
- require confirmation before overwriting non-secret config
- never overwrite secret values silently
- preserve unknown keys when safe, but warn about schema drift

Good Phase 1 behavior:
- regenerate missing non-secret config from existing state
- repair path permissions
- add newly required defaults

Behavior to avoid in Phase 1:
- wholesale reset of configuration without explicit user intent
- automatic deletion of secret files
- silently changing selected role/topology after recommendation changes

### 6. Doctor should be bootstrap-scoped, not a fake deployment doctor

The planner should keep `doctor` constrained to what Phase 1 actually owns.

Recommended `doctor` checks for Phase 1:
- config root exists and is writable
- secret root exists and has expected permissions
- config file parses and matches schema version
- selected role/topology is internally consistent
- expected local files exist
- Docker CLI presence and version can be detected
- obvious default port conflicts can be reported
- required runtime inputs are missing or incomplete

Safe auto-fixes:
- create missing directories
- regenerate missing non-secret config from known state
- repair file permissions where possible
- normalize config keys to current schema defaults

Do not auto-fix in Phase 1:
- network exposure decisions
- domain/Nginx/reverse-proxy setup
- public URL inference for remote hosts
- service installation beyond bootstrap-local concerns

### 7. Keep networking fallback simple: IP + port first

The user explicitly wants progress even when richer networking inputs are unavailable.

Planning implication:
- build a fallback branch where the tool records `ip_port` mode and leaves domain/proxy items as optional follow-up
- the bootstrap contract should persist deferred networking work so later phases can read it
- the default path should not require Caddy/Nginx/domain decisions to succeed

### 8. Phase 1 must include basic tests, not just implementation scaffolding

The planner should not defer all tests to later phases. Because Phase 1 defines the contract, it needs basic verification now.

Recommended Phase 1 automated coverage:
- schema tests for role/topology/config models
- path resolution tests across simulated Linux/macOS/Windows contexts
- plan builder tests for new install, rerun, and diff cases
- CLI tests for `init` in dry-run mode
- CLI tests for `doctor` output classification
- secret separation tests that assert secrets do not land in non-secret config
- fallback tests for incomplete networking input resulting in `ip_port` path

Recommended manual-only checks:
- OpenClaw skill guidance reads clearly and points to canonical CLI commands
- generated plan output is understandable to a human operator

## Suggested Implementation Sequence

The planner should decompose Phase 1 in this order:

1. **Phase scaffolding and shared bootstrap contracts**
Define package layout, bootstrap schemas, role/topology enums, settings versioning, and platform path helpers.

2. **Config and secret persistence**
Implement path resolution, config file writing, secret file writing, schema validation, and permission checks.

3. **Environment detection and plan model**
Implement OS/shell/Docker/path/port detection plus a structured plan object and dry-run renderer.

4. **CLI command surface**
Implement `transcendence-memory init ...`, config inspection helpers, and `doctor` with safe auto-fix behavior.

5. **Skill-facing guidance and tests**
Add the skill entry surface and documentation glue after CLI behaviors exist, then add or finish Phase 1 tests.

This order reduces the risk of shallow CLI wrappers around unstable internal structures.

## Planner Implications

### Likely plan groups

The planner should probably create separate plans for:
- bootstrap contracts and repository scaffolding
- config/secret persistence and path resolution
- environment detection plus plan/diff rendering
- CLI `init` and `doctor`
- skill guidance plus Phase 1 tests

That split keeps files_modified and acceptance criteria narrow enough for execution.

### Must-haves the planner should preserve

- every plan must preserve the thin-skill/thick-CLI boundary
- no plan should include backend runtime implementation
- no plan should include connection bundle export/import
- at least one early plan must establish typed models and config schema versioning
- at least one plan must establish test infrastructure before the later CLI work is considered complete

### Common failure modes to guard against

- mixing secrets into the normal config file
- treating dry-run output as unstructured prose instead of a typed plan
- making `doctor` too ambitious and coupling it to not-yet-built backend behavior
- using repository-local config files because they are easier during development
- allowing rerun to overwrite user config without a diff and confirmation step

## Validation Architecture

Phase 1 should produce a validation strategy because its contract surface is small enough to make validation explicit early.

Recommended validation baseline:
- framework: `pytest`
- command runner: Typer test runner / CLI invocation helpers
- quick verification target: schema, path, dry-run, and doctor classification tests
- full verification target: all Phase 1 tests plus any skill-reference integrity checks introduced in the phase
- max feedback latency target: under 30 seconds for the quick suite

Recommended initial test files:
- `tests/unit/test_bootstrap_models.py`
- `tests/unit/test_platform_paths.py`
- `tests/unit/test_config_persistence.py`
- `tests/unit/test_plan_builder.py`
- `tests/cli/test_init_command.py`
- `tests/cli/test_doctor_command.py`
- `tests/integration/test_bootstrap_rerun.py`

Wave 0 test infrastructure should land before or alongside the first executable plan that mutates config state.

## Recommended Sources of Truth for Planning

- `.planning/phases/01-guided-bootstrap-and-safe-configuration/01-CONTEXT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`
- `.planning/research/SUMMARY.md`
- `.planning/research/STACK.md`
- `.planning/research/PITFALLS.md`

## Source Notes

- Earlier project research already locked the high-level stack: Python, `uv`, Typer, Pydantic, Docker-first, Linux `systemd` secondary.
- Earlier discussion already locked the operator-experience choices: skill-first guidance, CLI parity, non-blocking `IP + port` fallback, and bootstrap-scoped `doctor`.
- There is no existing implementation code in the repository yet, so Phase 1 plans should explicitly include repository scaffolding and test scaffolding rather than assuming reusable modules already exist.

---
*Phase research completed: 2026-03-23*
*Ready for planning: yes*
