---
phase: 03
slug: cross-platform-deployment-and-health
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `. .venv/bin/activate && python -m pytest tests/unit/test_deploy_config.py tests/unit/test_systemd_render.py tests/cli/test_backend_health_command.py -q` |
| **Full suite command** | `. .venv/bin/activate && python -m pytest -q` |
| **Estimated runtime** | ~40 seconds quick run, ~120 seconds full suite after Phase 3 lands |

---

## Sampling Rate

- **After every task commit:** Run `. .venv/bin/activate && python -m pytest tests/unit/test_deploy_config.py tests/unit/test_systemd_render.py tests/cli/test_backend_health_command.py -q`
- **After every plan wave:** Run `. .venv/bin/activate && python -m pytest -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-TBD-01 | TBD | TBD | BACK-01 | unit/cli | `. .venv/bin/activate && python -m pytest tests/unit/test_deploy_config.py tests/cli/test_backend_deploy_command.py -q` | ❌ W0 | ⬜ pending |
| 03-TBD-02 | TBD | TBD | BACK-02 | unit | `. .venv/bin/activate && python -m pytest tests/unit/test_systemd_render.py -q` | ❌ W0 | ⬜ pending |
| 03-TBD-03 | TBD | TBD | BACK-03 | cli/integration | `. .venv/bin/activate && python -m pytest tests/cli/test_backend_deploy_command.py -q` | ❌ W0 | ⬜ pending |
| 03-TBD-04 | TBD | TBD | BACK-04 | cli/api | `. .venv/bin/activate && python -m pytest tests/cli/test_backend_health_command.py tests/api/test_backend_health_route.py -q` | ❌ W0 | ⬜ pending |
| 03-TBD-05 | TBD | TBD | VERI-02 | cli | `. .venv/bin/activate && python -m pytest tests/cli/test_backend_health_command.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_deploy_config.py` — Docker/Compose/env rendering coverage
- [ ] `tests/unit/test_systemd_render.py` — systemd unit/env template coverage
- [ ] `tests/cli/test_backend_deploy_command.py` — deploy and rerun CLI coverage
- [ ] `tests/cli/test_backend_health_command.py` — health diagnostics and next-step output coverage
- [ ] `tests/api/test_backend_health_route.py` — deeper backend health route coverage
- [ ] Optional environment-gated `tests/integration/test_compose_smoke.py` — compose-based smoke entrypoint

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker deployment works on macOS and Windows | BACK-01 | Requires Docker Desktop environments not present in CI/local planning context | Run `backend deploy` on macOS/Windows with Docker Desktop and confirm health reaches OK |
| Native Linux systemd service behaves correctly | BACK-02 | Requires a real Linux host with systemd | Install the generated unit/env files, start the service, and confirm `systemctl status` and health checks |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
