# Phase 5 Research: Bilingual Packaging and Release Hardening

**Project:** Transcendence Memory
**Phase:** 5
**Researched:** 2026-03-24
**Confidence:** Medium-High

## Objective

Answer the Phase 5 planning question:

What does the planner need to know to create strong implementation plans for bilingual release documentation, compatibility checks, and CI/release hardening around an OSS package that includes a CLI, backend, OpenClaw skill, and connection bundle contract?

## Key Current-State Observations

- Root `README.md` is still almost empty.
- There is no `LICENSE` file yet even though the project-level decision is MIT.
- The skill package already exists in-repo and must be treated as the canonical public operator surface.
- There is no `.github/workflows/` directory yet.
- Verification reports already exist for Phases 2, 3, and 4 and should be surfaced by the release docs rather than rediscovered manually.

## Packaging Conclusions

### 1. Root README and runbooks are not polish; they are release-critical artifacts

Phase 5 should not treat docs as “later cleanup”. The root README is currently insufficient to describe:
- what this project is
- how to choose same-machine vs split-machine
- how to use the canonical in-repo skill package
- how to verify deployment/auth/handoff

The planner should therefore include at least one docs-first plan that replaces the root README and adds Chinese-first bilingual runbooks.

### 2. Compatibility needs a machine-readable manifest

`VERI-05` is not satisfied by prose alone.

Recommended compatibility artifact:
- a machine-readable manifest or matrix covering:
  - CLI version
  - backend version
  - skill package version
  - connection bundle version
  - minimum compatible combinations

This should be checked in CI and read by docs/tests.

### 3. Release hardening should assume GitHub-hosted OSS norms

Current official GitHub guidance consistently pushes toward:
- pinning third-party GitHub Actions by full commit SHA
- explicit dependency review / supply-chain checks
- secret scanning / push protection concepts
- stronger artifact integrity practices

Planning implication:
- Phase 5 should include GitHub Actions workflow files as the primary CI hardening target
- use pinned actions, not floating third-party tags
- include compatibility validation and test execution in the workflow

### 4. Docs should route to the right level of detail

Recommended docs structure:
- `README.md` — project overview, quickstart, topology choice, verification entry points
- `docs/backend-deploy.md`
- `docs/frontend-handoff.md`
- `docs/authentication.md`
- `docs/troubleshooting.md`
- `docs/release-compatibility.md`

This prevents the root README from becoming a monolith while still satisfying the roadmap requirement.

## Validation Architecture

Phase 5 should validate:
- docs presence and core sections
- compatibility manifest schema and values
- workflow file presence and hardening expectations
- root license presence

Suggested new test/check files:
- `tests/unit/test_release_compatibility.py`
- `tests/unit/test_docs_presence.py`
- optional script/check for pinned GitHub Actions refs

## Recommended Plan Split

The planner should likely split Phase 5 into:
1. root packaging basics: `README`, `LICENSE`, docs skeleton
2. operator runbooks and topology/auth/handoff docs
3. compatibility manifest and compatibility tests
4. CI/release hardening workflows and release checklist

## Sources Used

- Current repository state
- Current repository-local skill state
- Official GitHub documentation on Actions security hardening, dependency review, secret scanning / push protection concepts, and artifact integrity guidance

---
*Phase research completed: 2026-03-24*
*Ready for planning: yes*
