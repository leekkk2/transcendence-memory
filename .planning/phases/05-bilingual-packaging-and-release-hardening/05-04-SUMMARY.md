---
phase: 05-bilingual-packaging-and-release-hardening
plan: 04
subsystem: tooling
tags: [github-actions, ci, release, hardening]
requires:
  - phase: 05-01
    provides: root release docs
  - phase: 05-02
    provides: runbook set
  - phase: 05-03
    provides: compatibility manifest
provides:
  - CI workflow
  - release-check workflow
  - release process doc
affects: [phase-05, ci, release]
tech-stack:
  added: []
  patterns: [sha-pinned-actions, explicit-release-gates]
key-files:
  created: [.github/workflows/ci.yml, .github/workflows/release-checks.yml, docs/release-process.md]
  modified: [tests/unit/test_release_compatibility.py]
key-decisions:
  - "GitHub Actions are pinned by full SHA."
  - "Release process documents current manual verification backlog instead of pretending it is complete."
patterns-established:
  - "Release hardening is explicit and test-backed."
requirements-completed: [VERI-05]
duration: 13min
completed: 2026-03-24
---

# Phase 5 Plan 04 Summary

**Pinned GitHub workflows and documented release gates for OSS publication**

## Performance

- **Duration:** 13 min
- **Started:** 2026-03-24T14:23:00+08:00
- **Completed:** 2026-03-24T14:36:00+08:00
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added CI and release-check workflows.
- Pinned GitHub Actions by full commit SHA.
- Added a release-process doc tied to the real Phase 2/3/4 verification backlog.

## Task Commits

1. **Plan 05-04 implementation** - `c867e18` (feat)

## Files Created/Modified
- `.github/workflows/ci.yml`
- `.github/workflows/release-checks.yml`
- `docs/release-process.md`
- `tests/unit/test_release_compatibility.py`

## Decisions Made
- Used full SHA pins for official actions instead of floating tags.

## Deviations from Plan

### Auto-fixed Issues

**1. Made workflow manifest usage explicit**
- **Found during:** local Phase 5 test execution
- **Issue:** release workflow ran the compatibility test but did not explicitly reference `release-compatibility.json`, so the test contract was weaker than intended
- **Fix:** added an explicit `test -f compat/release-compatibility.json` step
- **Files modified:** `.github/workflows/release-checks.yml`
- **Verification:** Phase 5 test suite passed afterward
- **Committed in:** `c867e18`

---

**Total deviations:** 1 auto-fixed
**Impact on plan:** Improved release-hardening clarity without changing scope.

## Issues Encountered

None beyond the workflow manifest-path tightening above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The project now has the release packaging/hardening surface required by the roadmap.

---
*Phase: 05-bilingual-packaging-and-release-hardening*
*Completed: 2026-03-24*
