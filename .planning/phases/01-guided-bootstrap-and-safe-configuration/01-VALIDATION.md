---
phase: 01
slug: guided-bootstrap-and-safe-configuration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` or `pytest.ini` once Wave 0 scaffolding lands |
| **Quick run command** | `uv run pytest tests/unit/test_bootstrap_models.py tests/unit/test_platform_paths.py tests/cli/test_init_command.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~20 seconds quick run, ~45 seconds full suite after Wave 0 |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/test_bootstrap_models.py tests/unit/test_platform_paths.py tests/cli/test_init_command.py -q`
- **After every plan wave:** Run `uv run pytest -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-TBD-BOOT-01 | TBD | TBD | BOOT-01 | cli/unit | `uv run pytest tests/unit/test_bootstrap_models.py tests/cli/test_init_command.py -q` | ❌ W0 | ⬜ pending |
| 01-TBD-BOOT-02 | TBD | TBD | BOOT-02 | unit/cli | `uv run pytest tests/unit/test_platform_paths.py tests/unit/test_plan_builder.py tests/cli/test_init_command.py -q` | ❌ W0 | ⬜ pending |
| 01-TBD-BOOT-03 | TBD | TBD | BOOT-03 | unit/cli | `uv run pytest tests/unit/test_plan_builder.py tests/cli/test_init_command.py -q` | ❌ W0 | ⬜ pending |
| 01-TBD-BOOT-04 | TBD | TBD | BOOT-04 | integration | `uv run pytest tests/integration/test_bootstrap_rerun.py -q` | ❌ W0 | ⬜ pending |
| 01-TBD-BOOT-05 | TBD | TBD | BOOT-05 | cli/unit | `uv run pytest tests/unit/test_bootstrap_models.py tests/cli/test_init_command.py -q` | ❌ W0 | ⬜ pending |
| 01-TBD-CONF-01 | TBD | TBD | CONF-01 | unit/cli | `uv run pytest tests/unit/test_config_persistence.py tests/cli/test_init_command.py -q` | ❌ W0 | ⬜ pending |
| 01-TBD-CONF-02 | TBD | TBD | CONF-02 | unit | `uv run pytest tests/unit/test_config_persistence.py -q` | ❌ W0 | ⬜ pending |
| 01-TBD-CONF-03 | TBD | TBD | CONF-03 | unit/integration | `uv run pytest tests/unit/test_config_persistence.py tests/integration/test_bootstrap_rerun.py -q` | ❌ W0 | ⬜ pending |
| 01-TBD-CONF-04 | TBD | TBD | CONF-04 | cli | `uv run pytest tests/cli/test_init_command.py tests/cli/test_doctor_command.py -q` | ❌ W0 | ⬜ pending |
| 01-TBD-CONF-05 | TBD | TBD | CONF-05 | unit/cli | `uv run pytest tests/unit/test_platform_paths.py tests/cli/test_init_command.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures for temporary config roots, fake secret roots, and mocked environment detection
- [ ] `tests/unit/test_bootstrap_models.py` — schema coverage for role, topology, and plan models
- [ ] `tests/unit/test_platform_paths.py` — Linux/macOS/Windows path resolution coverage
- [ ] `tests/unit/test_config_persistence.py` — config versus secret persistence coverage
- [ ] `tests/unit/test_plan_builder.py` — dry-run and diff-plan generation coverage
- [ ] `tests/cli/test_init_command.py` — CLI bootstrap path coverage
- [ ] `tests/cli/test_doctor_command.py` — doctor classification and next-step output coverage
- [ ] `tests/integration/test_bootstrap_rerun.py` — rerun/idempotency coverage
- [ ] `pytest` wiring in `pyproject.toml` or equivalent — test runner and markers configured

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OpenClaw skill guidance correctly points users to canonical CLI flows | BOOT-01, BOOT-05 | Skill/operator guidance quality is partly documentation and prompt UX, not only code behavior | Read generated `SKILL.md` and related references; confirm they direct users through role/topology choice and canonical `transcendence-memory init ...` commands |
| Dry-run plan is understandable to a human operator before mutation | BOOT-03 | Readability and operator trust are hard to prove with automated assertions alone | Run the bootstrap command in dry-run mode and confirm the output clearly separates detections, planned file changes, secret-path creation, warnings, and next verification steps |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
