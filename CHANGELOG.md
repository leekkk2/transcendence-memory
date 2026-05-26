# Changelog

All notable changes to this skill plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project follows semantic versioning.

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
