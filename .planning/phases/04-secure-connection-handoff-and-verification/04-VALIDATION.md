---
phase: 04
slug: secure-connection-handoff-and-verification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `. .venv/bin/activate && python -m pytest tests/unit/test_connection_bundle.py tests/unit/test_endpoint_sanitization.py tests/cli/test_backend_export_connection.py -q` |
| **Full suite command** | `. .venv/bin/activate && python -m pytest -q` |
| **Estimated runtime** | ~45 seconds quick run, ~130 seconds full suite after Phase 4 lands |

---

## Sampling Rate

- **After every task commit:** Run `. .venv/bin/activate && python -m pytest tests/unit/test_connection_bundle.py tests/unit/test_endpoint_sanitization.py tests/cli/test_backend_export_connection.py -q`
- **After every plan wave:** Run `. .venv/bin/activate && python -m pytest -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-TBD-01 | TBD | TBD | CONN-01 | unit/cli | `. .venv/bin/activate && python -m pytest tests/unit/test_connection_bundle.py tests/cli/test_backend_export_connection.py -q` | ❌ W0 | ⬜ pending |
| 04-TBD-02 | TBD | TBD | CONN-02 | unit | `. .venv/bin/activate && python -m pytest tests/unit/test_connection_bundle.py tests/unit/test_endpoint_sanitization.py -q` | ❌ W0 | ⬜ pending |
| 04-TBD-03 | TBD | TBD | CONN-03 | cli | `. .venv/bin/activate && python -m pytest tests/cli/test_frontend_import_connection.py -q` | ❌ W0 | ⬜ pending |
| 04-TBD-04 | TBD | TBD | CONN-04 | cli/integration | `. .venv/bin/activate && python -m pytest tests/cli/test_frontend_check.py tests/cli/test_smoke_command.py -q` | ❌ W0 | ⬜ pending |
| 04-TBD-05 | TBD | TBD | CONN-05 | unit | `. .venv/bin/activate && python -m pytest tests/unit/test_endpoint_sanitization.py -q` | ❌ W0 | ⬜ pending |
| 04-TBD-06 | TBD | TBD | VERI-01 | cli/integration | `. .venv/bin/activate && python -m pytest tests/cli/test_smoke_command.py tests/integration/test_same_machine_smoke.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_connection_bundle.py`
- [ ] `tests/unit/test_endpoint_sanitization.py`
- [ ] `tests/cli/test_backend_export_connection.py`
- [ ] `tests/cli/test_frontend_import_connection.py`
- [ ] `tests/cli/test_frontend_check.py`
- [ ] `tests/cli/test_smoke_command.py`
- [ ] `tests/integration/test_same_machine_smoke.py`
- [ ] `tests/integration/test_split_machine_bundle_flow.py`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real backend-to-frontend machine handoff | CONN-01..04 | Requires two real machines or equivalent isolated environments | Export a bundle on the backend host, transfer it, import it on the frontend host, then run frontend check |
| Real provider-backed smoke verification across hosts | VERI-01 | Requires live backend, live auth, and real provider credentials | Run the smoke command after import and verify health/embed/search end-to-end |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
