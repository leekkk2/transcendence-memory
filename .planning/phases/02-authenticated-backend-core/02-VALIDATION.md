---
phase: 02
slug: authenticated-backend-core
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `. .venv/bin/activate && python -m pytest tests/unit/test_auth_models.py tests/unit/test_api_key_auth.py tests/api/test_health_route.py -q` |
| **Full suite command** | `. .venv/bin/activate && python -m pytest -q` |
| **Estimated runtime** | ~45 seconds quick run, ~120 seconds full suite after Phase 2 lands |

---

## Sampling Rate

- **After every task commit:** Run `. .venv/bin/activate && python -m pytest tests/unit/test_auth_models.py tests/unit/test_api_key_auth.py tests/api/test_health_route.py -q`
- **After every plan wave:** Run `. .venv/bin/activate && python -m pytest -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-TBD-01 | TBD | TBD | AUTH-01 | unit/api | `. .venv/bin/activate && python -m pytest tests/unit/test_api_key_auth.py -q` | ❌ W0 | ⬜ pending |
| 02-TBD-02 | TBD | TBD | AUTH-02 | integration | `. .venv/bin/activate && python -m pytest tests/integration/test_oauth_cli_flow.py -q` | ❌ W0 | ⬜ pending |
| 02-TBD-03 | TBD | TBD | AUTH-03 | cli/api | `. .venv/bin/activate && python -m pytest tests/api/test_auth_routes.py -q` | ❌ W0 | ⬜ pending |
| 02-TBD-04 | TBD | TBD | AUTH-04 | cli/unit | `. .venv/bin/activate && python -m pytest tests/unit/test_oauth_redaction.py tests/api/test_auth_routes.py -q` | ❌ W0 | ⬜ pending |
| 02-TBD-05 | TBD | TBD | AUTH-05 | unit/integration | `. .venv/bin/activate && python -m pytest tests/unit/test_oauth_redaction.py tests/integration/test_oauth_cli_flow.py -q` | ❌ W0 | ⬜ pending |
| 02-TBD-06 | TBD | TBD | BACK-05 | integration/api | `. .venv/bin/activate && python -m pytest tests/api/test_memory_routes.py tests/integration/test_pgvector_memory.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_auth_models.py` — auth and token-state model coverage
- [ ] `tests/unit/test_api_key_auth.py` — API-key validation coverage
- [ ] `tests/unit/test_oauth_redaction.py` — token redaction and secret-storage coverage
- [ ] `tests/api/test_health_route.py` — health route behavior
- [ ] `tests/api/test_auth_routes.py` — auth status/login/logout route or CLI-adapter coverage
- [ ] `tests/api/test_memory_routes.py` — authenticated embed/search route coverage
- [ ] `tests/integration/test_pgvector_memory.py` — PostgreSQL + pgvector integration coverage
- [ ] `tests/integration/test_oauth_cli_flow.py` — browser-based OAuth CLI flow coverage with mocked provider responses
- [ ] FastAPI/backend test helpers and fixtures — app client, DB session fixture, secret-path fixture

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OAuth browser flow is understandable to the operator | AUTH-02 | Browser launch and loopback UX is difficult to fully validate with automated assertions alone | Run the CLI login flow manually, confirm it opens a browser, completes the local callback, and leaves only redacted status output |
| CLI auth status output is safe and operator-friendly | AUTH-03, AUTH-05 | Output quality and redaction clarity are partly UX concerns | Run `auth status` after login and verify that provider/account metadata appears but refresh tokens do not |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
