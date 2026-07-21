# Changelog

All notable changes to this skill plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project follows semantic versioning.

## v0.8.1 — 2026-06-24

Fixes Codex plugin-hook compatibility for the published plugin package.

### Changed

- **`hooks/hooks.json` Stop hook downgraded to sync compatibility**:
  `async: true` is now `async: false`. Current Codex releases parse `async` but
  skip handlers with `async: true`, which produced the startup warning
  `async hooks are not supported yet` and disabled the bundled session-summary
  stop hook for Codex users. The hook still runs; it just no longer requests an
  unsupported async execution mode.
- **plugin package version bumped**: `.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json` now publish `0.8.1`.

## v0.8.0 — 2026-06-16

Aligns the skill docs with server **v0.21.0**. The governance subsystem (6-tool
toolbox / dreaming / opt-in LLM orchestration agent + reversible dual-gate) was
already documented for server v0.20; this release backfills the two
`compress_knowledge_cluster` facts that drifted from production: its **idempotent
4-state behavior** and the corrected **batch-budget default**. All changes are
**docs-only** — no skill behavior change.

### Changed

- **compress batch budget default corrected** (`references/governance.md`,
  `references/troubleshooting.md`): `config:agent:compress_batch_bytes` /
  `TM_COMPRESS_BATCH_BYTES` default is **256 KiB (262144 B)**, not the old
  **8 MiB**. Rationale: real mixed CJK+Latin clusters hit HTTP 400
  `context_too_large` at 1 MiB while 768 KiB returns 200 — CJK UTF-8 is far more
  token-dense per byte than ASCII, so the byte budget is dropped to 256 KiB
  (~3× headroom over 768 KiB) to leave room for the system prompt + output tokens
  (map-reduce batching + `_truncate_for_llm` backstop).

### Added

- **compress idempotent 4-state** (`references/governance.md` §2.2,
  `references/api-reference.md` ToolInvokeResponse): `first_card` (no existing
  card → LLM builds the first), `skipped_unchanged` (cluster fingerprint
  unchanged → **zero LLM, zero new card**, top-level `status='ok'` +
  `result.action='skipped_unchanged'`), `consolidated` (multiple same-cluster
  orphan cards, `source_ids` Jaccard ≥ 0.5 → **zero-LLM** cheap merge, keep the
  fingerprint match, retire the rest), `superseded` (cluster content changed →
  LLM re-summarize, supersede old cards). All append-only + reversible governance
  snapshots (never a hard delete) + idempotent (no change → no accumulation).
- **dreaming `batch_model` clarification**: P6 dreaming is **report-only and does
  not call any model**; `batch_model` is a state field — real LLM distillation is
  deferred to the governance toolbox (`compress`, via the gateway-configured
  model). No hardcoded model id (HR-9).

## v0.7.0 — 2026-06-10

Aligns the skill docs + `tm-search.sh` with server **v0.19.0** (blueprint Redis
governance layer). Every v0.19 addition is **opt-in / backward-compatible**, so
the skill's own behavior is unchanged — this is a docs + wrapper-rendering update
that lets agents correctly read the new `/search` and `/query` response fields.

### Added

- **`/search` response fields** (`references/commands.md`, `references/api-reference.md`):
  `citations[]` (default ON for `/search`), per-hit + citation `lineStart`/`lineEnd`
  source line numbers (`null` on pre-P4 chunks — no schema migration, no re-embed),
  `blocked_low_score` (score-gate suppressed count), `fallback_rendered` (opt-in
  template, default `null`), `rerank_applied`, plus the request-level `score_threshold`.
- **`/query` response fields**: `top_score`, `citations` (default **OFF** for `/query`),
  `fallback_rendered`.
- **Gotchas + troubleshooting**: "empty `results` + `blocked_low_score>0` = score-gate,
  not an empty DB"; "`lineStart`/`lineEnd` is `null` on old chunks — expected".
- **`tm-search.sh`**: distilled output now renders per-hit `L<start>–<end>` line ranges
  and a `blocked_low_score` warning line.
- **`scripts/tm-remember.sh`** (new): one-shot quick-memory store wrapper for
  `POST /ingest-memory/objects` — jq-built JSON (eliminates the hand-escaped-JSON
  422 class, the dominant ingest failure mode in production usage), self-contained
  secret redaction (same pattern set as `hooks/common.sh`, no hooks/ dependency),
  WAF-friendly UA + proxy auto-fallback, `--title/--tags/--container/--id/--no-embed/--json`,
  one-line success output `stored id=... container=... embed=queued|skipped`.
- **`tm-search.sh` read-only subcommands**: `containers [pattern]` (GET `/containers`
  rendered as a name/objects/index-state table) and `jobs <id>` (GET `/jobs/{id}`
  rendered as plain-words `running`/`done`/`FAILED` from `running`/`exit_code` —
  no misleading top-level `status` field assumption).

### Notes

- Server-side v0.19 governance (Redis, config center, token metering, dreaming engine,
  governance toolbox, `/admin/*` dashboard) stays out of scope per `When NOT to Use` —
  those are operator concerns, not client-skill API surface.

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

