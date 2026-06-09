# Changelog

All notable changes to this skill plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project follows semantic versioning.

## v0.6.0 — 2026-06-09

Aligns the skill docs with server **v0.18** (RAG graceful degradation + new
operational endpoints). No behavioral change to the skill itself — docs only.

### Added

- `SKILL.md` "Operational / admin HTTP endpoints (server v0.18)" table +
  detailed schemas in `references/api-reference.md` and per-call curl in
  `references/commands.md` for: `/index-status` ·
  `/containers/{name}/index-status` (per-container index state machine),
  `/embed-multimodal` (single-media Gemini-native embedding),
  `/containers/aliases` (POST/GET/DELETE alias routing),
  `/admin/usage/*` (request analytics + cleanup), `/admin/ui/*`
  (cookie-session admin dashboard).
- `SKILL.md` Gotchas + `references/troubleshooting.md` sections for the v0.18
  graceful-degradation semantics: partial-success now returns HTTP 200 with
  `is_degraded` (= `degraded`, same value) + `fallback_source` instead of
  failing the whole search; only an all-container failure yields
  `status:"error"`.
- Troubleshooting for the v0.18 soft-skip of never-embedded `_openai` siblings
  (no more `not_initialized` noise dragging the main container down) and for
  the startup dim-consistency gate (`FATAL: EMBEDDING_DIM=X disagrees with
  LanceDB schemas`, override `TM_ALLOW_DIM_DRIFT=1`).

### Changed

- Clarified the strict `/tm` section: `/tm` remains a Claude Code slash command
  (not a bare binary), but an **optional** shell CLI `tm` now exists
  (`pipx install transcendence-memory-cli`, shipped from the server repo's
  `cli-package/`, not bundled with this skill). The two are different things;
  `tm-codex` does not exist.
- `scripts/job-ledger.py` User-Agent bumped `0.4` → `0.5` (aligns with
  `tm-search.sh`, already `0.5`).

### Notes

- Embedding-dimension references were already correct
  (`gemini-3072` default + `text-embedding-3-small`/1024 `*_openai` mirror) —
  verified, left unchanged. `skills/tm/SKILL.md` (thin alias) untouched.

## v0.5.0 — 2026-05-26

### Added

- **Behavior Conventions** section in `SKILL.md` guiding when to recall, when
  to remember, the title + trigger-words pattern, and credential-redaction
  expectations.
- `references/best-practices.md` / `best-practices.zh-CN.md` §7 Structured
  Memory Writing Conventions (title with synonyms + "When to recall me" line
  + bilingual tags).
- `references/best-practices.md` / `best-practices.zh-CN.md` §8 High-Density
  Index Cards (one consolidating card per 50–100 same-topic memories).
- `references/best-practices.md` / `best-practices.zh-CN.md` §9 Credential
  Redaction Checklist.
- `references/retrofit-playbook.md` — optional append-only SOP for upgrading
  old containers to the §7–§9 conventions and scrubbing legacy credential
  leaks.
- `hooks/common.sh::redact_secrets()` covering 10+ common secret patterns
  (`sk-*`, `pk_live_*`, `sk_live_*`, `xoxb-*`, `xoxp-*`, `ghp_*`, `gho_*`,
  `AKIA*`, `Authorization: Bearer`, URL-embedded `user:password`, PEM
  private-key blocks, JWT triple-segment tokens).
- `hooks/test/test_redact.sh` — 4 unit tests exercising the redactor with
  placeholder inputs (no real secrets in the repo).

### Changed

- `hooks/session-stop` now pipes the extracted transcript summary through
  `redact_secrets` before storing.
- `hooks/post-commit-memory` now pipes optional `COMMIT_MSG` / `CHANGED_FILES`
  env vars (and the prompt body) through `redact_secrets` before emitting
  context.

### Notes

- All examples use generic placeholder names (`your-project`, `team-alpha`,
  `my-memory-bank`, `https://your-rag.example.com`). No private identifiers.

## v0.4.1 — earlier

- Strict AI-behavior section: `/tm` is a slash command, never a shell binary.

## v0.4.0 — earlier

- Async ingestion silent-mode for KG-write endpoints; job ledger sweep.
