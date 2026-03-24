---
phase: 05
slug: bilingual-packaging-and-release-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `. .venv/bin/activate && python -m pytest tests/unit/test_release_compatibility.py tests/unit/test_docs_presence.py -q` |
| **Full suite command** | `. .venv/bin/activate && python -m pytest -q` |
| **Estimated runtime** | ~40 seconds quick run, ~140 seconds full suite after Phase 5 lands |

---

## Sampling Rate

- **After every task commit:** Run `. .venv/bin/activate && python -m pytest tests/unit/test_release_compatibility.py tests/unit/test_docs_presence.py -q`
- **After every plan wave:** Run `. .venv/bin/activate && python -m pytest -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-TBD-01 | TBD | TBD | VERI-03 | unit | `. .venv/bin/activate && python -m pytest tests/unit/test_docs_presence.py -q` | ❌ W0 | ⬜ pending |
| 05-TBD-02 | TBD | TBD | VERI-04 | unit | `. .venv/bin/activate && python -m pytest tests/unit/test_docs_presence.py -q` | ❌ W0 | ⬜ pending |
| 05-TBD-03 | TBD | TBD | VERI-05 | unit | `. .venv/bin/activate && python -m pytest tests/unit/test_release_compatibility.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_release_compatibility.py`
- [ ] `tests/unit/test_docs_presence.py`
- [ ] release workflow hardening checks for pinned actions

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Bilingual docs read naturally for human operators | VERI-03, VERI-04 | Quality and clarity are partly editorial | Review README and runbooks in Chinese and English |
| CI/release flow matches the eventual public host | VERI-05 | Repo hosting/publishing target may still change | Review workflow assumptions before public launch |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
