---
name: tm
description: >-
  Short alias for `transcendence-memory`. Use when the user types `/tm` or
  invokes `Skill(skill: "tm")`. Provides the same long-term memory capability
  — semantic search, memory storage, multimodal RAG queries, container
  management — backed by the self-hosted transcendence-memory-server. This
  alias exists because Claude Code skill frontmatter does not support
  `aliases:` natively, so the canonical name `transcendence-memory` and the
  short form `tm` are exposed as two SKILL.md files pointing at the same
  engine.
allowed-tools: Bash, Read, Write, Grep, Glob
---

## What this alias does

`tm` is the **short alias** for the `transcendence-memory` skill. They share the same configuration (`~/.transcendence-memory/config.toml`), the same backend, the same commands.

> **Important — `/tm` is a slash command, NOT a shell binary.** If you find yourself about to run `Bash({command: "tm ..."})` or `Bash({command: "/tm ..."})`, that will fail with `command not found`. Invoke via the `SlashCommand` tool instead — e.g. `SlashCommand({ command: "/tm search <query>" })`. For the curl-based HTTP fallback, see the canonical SKILL.md's "AI Behavior — `/tm` is a slash command" section.

## How to execute

Read the canonical SKILL.md and follow its instructions verbatim:

```
Read the file: skills/transcendence-memory/SKILL.md
```

(Resolve relative to this skill's parent directory: `<plugin-root>/skills/transcendence-memory/SKILL.md`. When installed via `/plugin install`, the plugin root is `~/.claude/plugins/cache/transcendence-memory/transcendence-memory/<version>/`.)

That file documents the complete command set:

| Command | Purpose |
|---------|---------|
| `connect <token>` / `connect --manual` | Authenticate |
| `status` | Health check |
| `search <query>` / `search --match <pattern> <q>` / `search --all <q>` | Semantic search |
| `remember <text>` | Quick memory store |
| `update <id> <text>` | Update an existing memory |
| `embed` | Rebuild index |
| `query <question>` | Multimodal RAG with LLM-synthesized answer |
| `upload <file>` | Add document to knowledge graph |
| `containers [pattern]` | List containers |
| `batch <file.jsonl>` | Bulk ingest |
| `jobs` | List background knowledge-graph build jobs |
| `auto on` / `auto off` / `auto status` | Toggle automatic memory hooks |
| `upgrade` | Pull latest skill scripts |

## Why this exists

Claude Code's skill frontmatter does **not** support `aliases:` field (verified via official `Frontmatter reference`). To let users invoke either `/transcendence-memory remember ...` or the shorter `/tm remember ...` (and the equivalent `Skill(skill: "tm", ...)` agent calls), this alias skill mirrors the canonical entry.

## Maintenance

If the canonical SKILL.md changes, this alias does **not** need editing — it always defers to the canonical file at runtime. Only update this file if the deferral mechanism itself changes (e.g. the canonical path moves).

## Do not duplicate state

Do not write a separate `config.toml`, do not call distinct endpoints, do not maintain a parallel command map. This file is intentionally thin to avoid drift.
