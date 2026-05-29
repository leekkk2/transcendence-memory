---
name: transcendence-memory
description: Use when the user mentions memory search, RAG retrieval, knowledge queries, embedding rebuild, document upload, connection tokens, or invokes "/tm" / "transcendence-memory" — including indirect recall like "what did we decide last time", "上次怎么处理的", "之前的方案". Covers searching, storing, multimodal RAG queries, and troubleshooting against a self-hosted memory backend.
allowed-tools: Bash, Read, Write, Grep, Glob
argument-hint: "[command] [args...]"
---

## What This Skill Does

Provides self-hosted long-term memory for AI agents by connecting to the [transcendence-memory-server](https://github.com/leekkk2/transcendence-memory-server) backend.

Core capabilities:
- **Connect**: complete authentication in one step with a connection token or manual configuration
- **Text memory**: manage structured memories through lightweight CRUD endpoints
- **Multimodal RAG**: upload documents (PDF, image, or Markdown) or raw text into the RAG-Anything pipeline, then ask natural-language questions and get LLM-generated answers
- **Container management**: list and delete containers
- **Troubleshooting**: diagnose connection and retrieval issues

## Install

```bash
npx skills add https://github.com/leekkk2/transcendence-memory --skill transcendence-memory
```

Or inside a Claude Code session:

```text
/plugin marketplace add leekkk2/transcendence-memory
/plugin install transcendence-memory
/reload-plugins
```

After `/reload-plugins`, the four lifecycle hooks (SessionStart / UserPromptSubmit / PostToolUse / Stop) and the `/tm` slash commands are immediately available — no session restart required.

## Principles

- **Keep builtin memory**: server-side memory augments the agent's builtin memory instead of replacing it
- **Zero dependency**: no extra package installation is required; the agent can do everything with native tools such as curl, file I/O, and the Python standard library
- **Progressive loading**: read `references/setup.md` during first-time setup, then this file is enough for day-to-day use
- **Two paths, no auto-bridge**: `/ingest-memory/objects` writes to LanceDB (served by `/search`); `/documents/text` and `/documents/upload` write to the RAG-Anything knowledge graph (served by `/query`). Data ingested through one path is **not** auto-promoted to the other. When you need both `/search` snippets and `/query` synthesis, you must dual-write. See `references/best-practices.md`.

## Behavior Conventions

These are the conventions the skill expects agents to follow when reading or
writing memories. They protect search recall and prevent credential leaks.

### 1. When to recall

- At session start, when the upcoming work obviously depends on prior decisions.
- When the user mentions verbs like "before / last time / previously / 上次 /
  之前 / 我们之前怎么做的".
- Before answering any question that references project history, prior
  decisions, or recurring SOPs.

### 2. When to remember

- After a high-value conclusion is reached (decision, lesson, SOP, postmortem,
  resolved bug root cause).
- After completing a sprint, shipping a feature, or closing an incident.
- **Never** for transient context — file diffs, debug traces, raw tool output,
  ephemeral REPL output.

### 3. Title + trigger-words pattern

Agents that recall memory later use **fuzzy natural-language phrases**, not
the original ASCII id. When writing a high-value memory, structure it as:

1. **Title with synonyms** — at least 2-3 of the verbs / nouns a future
   searcher might type, mixing English and the working language.
2. **A "When to recall me" line** listing verbs + entities + likely question
   phrasings.
3. **Bilingual tags** — mix technical ids (`deploy`, `auth`) and natural-
   language terms (`部署`, `登录`).

See `references/best-practices.<lang>.md` §7 for the full template, and §8 for
the index-card pattern that consolidates many memories around one fuzzy entry
point.

### 4. Credential redaction (auto)

The skill auto-redacts common secret patterns through the PostToolUse and Stop
hooks via `redact_secrets()` in [`hooks/common.sh`](../../hooks/common.sh). If
you ingest memories programmatically through another path (custom script,
batch importer, manual `curl`), call `redact_secrets()` yourself or pass
`--redact` to `scripts/batch-ingest.py`. Patterns covered:

- API keys: `sk-...`, `xoxb-...`, `xoxp-...`, `ghp_...`, `gho_...`,
  `pk_live_...`, `sk_live_...`, `AKIA...`
- `Authorization: Bearer ...` headers
- URL-embedded credentials: `scheme://user:password@host`
- PEM private-key blocks: `-----BEGIN ... PRIVATE KEY-----`
- JWT-like triple-segment tokens

Sample memory structure:

```
[Decision / 决策 · Release SOP · 部署 / launch — sprint port conflict]

When to recall me: deploy 部署 launch sprint port conflict docker compose
端口 冲突 -- what was the resolution?

Decision: ...
Tags: deploy, docker, port-conflict, 部署, 端口冲突
```

See `references/best-practices.<lang>.md` §9 for the full redaction checklist.

## AI Behavior — `/tm` is a slash command, NEVER a shell binary (STRICT)

`/tm` is a Claude Code **slash command** invoked through the `SlashCommand` tool.
It is NOT a shell binary. The following will always fail with `command not found`:

```bash
$ tm search "..."          # ❌ command not found
$ tm remember "..."        # ❌ command not found
$ /tm search "..."         # ❌ no such file or directory
```

The AI MUST use one of these two paths only:

1. **Preferred — `SlashCommand` tool** (when running inside Claude Code):
   ```
   SlashCommand({ command: "/tm search <query>" })
   ```

2. **Fallback — direct HTTP via Bash + curl** (when `SlashCommand` is unavailable
   or the AI is outside Claude Code):
   ```bash
   ENDPOINT="$(grep '^endpoint' ~/.transcendence-memory/config.toml | cut -d'"' -f2)"
   API_KEY="$(grep '^api_key' ~/.transcendence-memory/config.toml | cut -d'"' -f2)"
   CONTAINER="$(grep '^container' ~/.transcendence-memory/config.toml | cut -d'"' -f2)"
   curl -sS -X POST "$ENDPOINT/search" \
     -H "X-API-KEY: $API_KEY" -H "Content-Type: application/json" \
     -d "{\"container\":\"$CONTAINER\",\"query\":\"<query>\",\"topk\":5}"
   ```

If the AI catches itself about to invoke `Bash({command: "tm ..."})` or
`Bash({command: "/tm ..."})`, STOP and switch to one of the two paths above.
The same applies to the long-form alias `/transcendence-memory <command>`.

> The `Example` column in the command table below shows the slash-command form.
> Invoke via the `SlashCommand` tool. For raw HTTP fallback, see `references/api-reference.md`.

## AI Behavior — async ingestion silent-mode (v0.4.1+, STRICT)

Any call that returns an integer `pid` / `job_id` from a server v0.15.0+ KG-write endpoint (`/tm upload`, raw `POST /documents/text`, `POST /documents/upload`) is **fire-and-forget**. HTTP already returned — the task is handed off. The AI **MUST**:

1. **Never poll `/jobs/{id}` to wait for completion.** No `until` loops, no sleep-loops, no blocking waits.
2. **Pipe the server response to the ledger and end the turn**:
   ```bash
   echo '<server-response-json>' | python3 <skill-path>/scripts/job-ledger.py add
   ```
3. **Stay silent on success.** The SessionStart hook sweeps the ledger next session; **only failures surface** one warning line to the user. When the user mentions this skill (or memory / RAG / KG) again mid-session, silently run `python3 <skill-path>/scripts/job-ledger.py sweep` — **never report success**, only surface failures.
4. User-initiated inspection: `/tm jobs`.

❌ Don't tell the user "ingestion succeeded, doc is queryable now" right after enqueue — only enqueued; KG isn't built yet. ❌ Don't treat empty `/query` immediately after enqueue as failure — expected; the doc becomes recallable in a later session.

> Fire-and-forget by design. If everything is fine, the user never hears about it.

## Built-in Commands

These commands can be invoked through `/transcendence-memory <command>` or the short form `/tm <command>`. **Full HTTP / curl / argument schemas for every command live in [`references/commands.md`](./references/commands.md)** — keep this table for at-a-glance discovery, jump to the reference when you need to call one.

| Command | Purpose | Example |
|------|------|------|
| `connect <token>` | Import a connection token and write local config | `/tm connect eyJlbmRw...` |
| `connect --manual` | Enter endpoint, api_key, and container manually | `/tm connect --manual` |
| `status` | Check connection status and server health | `/tm status` |
| `search <query>` | Run semantic search over memories | `/tm search architecture decision from the last deployment` |
| `search --match <pattern> <query>` | Search across all containers whose name fuzzy-matches `<pattern>` | `/tm search --match my-project docker compose` |
| `search --all <query>` | Search across **every** container at once | `/tm search --all release notes` |
| `remember <text>` | Store one memory quickly | `/tm remember Port conflicts caused the deployment failure` |
| `update <id> <text>` | Update an existing memory's text in the current container | `/tm update mem-001 New corrected content` |
| `embed` | Rebuild the index for the current container | `/tm embed` |
| `query <question>` | Run a multimodal RAG query and get an LLM-generated answer | `/tm query What is the overall project architecture?` |
| `upload <file>` | Upload a file into the knowledge graph | `/tm upload ./design.pdf` |
| `containers [pattern]` | List containers, optionally filtered by a fuzzy pattern | `/tm containers my-project` |
| `batch <file.jsonl>` | Bulk import memories | `/tm batch memories.jsonl` |
| `jobs` | List background knowledge-graph build jobs (pending / failed / done) | `/tm jobs` |
| `auto on` | Enable automatic memory on git commits | `/tm auto on` |
| `auto off` | Disable automatic memory | `/tm auto off` |
| `auto status` | Show auto-memory configuration | `/tm auto status` |
| `upgrade` | Pull latest skill scripts from the upstream repo | `/tm upgrade` |

## Gotchas — 最常踩的坑（写新代码前先扫一遍）

| 症状 | 真因 | 修复 |
|---|---|---|
| `Bash({command: "tm ..."})` 报 `command not found` | `/tm` 是 slash command，**不是** shell binary | 用 `SlashCommand({command: "/tm ..."})`，或本文 `## AI Behavior — /tm is a slash command` 的 curl fallback |
| `/documents/text` 或 `/upload` 后立即 `/query` 返空 | KG 构建异步 (server v0.15.0+)；HTTP 200 ≠ 完成 | **不要 polling**；写 ledger 后结束本轮，下个 session 再 query。详 `## AI Behavior — async ingestion silent-mode` |
| `/tm remember` 写入后 `/query` 找不到 | `/ingest-memory/objects` 只写 LanceDB；`/query` 只看 KG | 需要双轨召回时 **dual-write**，详 `references/best-practices.md §1.2` |
| `/search` 的 `results[]` 找不到入库时给的 `id` | 服务端不回流 client `id`；引用 key 是 `taskId + chunkId` | 按 `taskId` / `chunkId` / 文本前缀匹配；详 `references/commands.md` `search` §Response schema |
| 自写 Python / Node 客户端调 endpoint 全部 403 | Cloudflare 默认拦 `python-urllib` / `node-fetch` / `Go net/http` UA | 显式 `User-Agent: transcendence-memory-skill/0.4`（任何非默认值都行） |
| `update` / `delete` 之后 `/search` 看不到改动 | LanceDB index 没 rebuild | `/tm embed` 刷新（异步入队，duplicate calls 自动 coalesce） |
| `/jobs/{pid}` 取不到 `.status` 字段 | 顶层没有 `status`；字段是 `running` / `exit_code` | 直接读 `running` / `exit_code`；或用 `/tm jobs` 走本地 ledger |
| 明文 `sk-...` / `ghp_...` / `xoxb-...` 进了 memory | hooks 已自动 redact，但 batch / 自定义脚本绕过 | 调 `redact_secrets()`（`hooks/common.sh`）或 `batch-ingest.py --redact` |
| `/tm upgrade` 报 `fatal: Not possible to fast-forward` | 本地有 cherry-pick shadow 或 divergence | `git tag backup/pre-upgrade-$(date +%Y%m%d) HEAD && git reset --hard origin/main`（完全可回退） |
| recall / search 查不到老知识但记得写过 | 标题用了 ASCII id 不是模糊自然语言 | 按本文 `## Behavior Conventions §3` 的 Title + trigger-words 模板写；老记忆 retrofit 用索引卡补一层（`references/best-practices.<lang>.md §8`） |

> **黄金法则**：HTTP 200 ≠ 业务完成。所有写路径（`/embed` / `/documents/*` / `/upload`）都是 fire-and-forget；只有 `/search` 同步。

## First-Time Setup

On first use, read `references/setup.md` to complete configuration.

The core flow has only two steps:
1. Get a **connection token** from the server (through the `/export-connection-token` endpoint or from an administrator)
2. Run `/tm connect <token>` to finish setup automatically

Or run `/tm connect --manual` and enter the values step by step.

> After configuration is complete, `references/setup.md` no longer needs to be loaded into context.

## Reference Documents

| Topic | File | When to load |
|---|---|---|
| Full HTTP API (request / response / error schemas) | [`references/api-reference.md`](./references/api-reference.md) | When you need exact field types |
| **Per-command curl / options matrix** | [`references/commands.md`](./references/commands.md) | When invoking any `/tm <command>` — full HTTP body, options, response schema |
| Architecture (dual-path model, container isolation, multi-embedding routing) | [`references/ARCHITECTURE.md`](./references/ARCHITECTURE.md) | When understanding how it works internally |
| Troubleshooting (connect / 401 / 403 / empty search / empty query / WAF 403) | [`references/troubleshooting.md`](./references/troubleshooting.md) | When something doesn't work |
| Operations (bulk ingest, persistent queue, automatic memory, platform support, multi-embedding ops) | [`references/OPERATIONS.md`](./references/OPERATIONS.md) | When operating at scale |
| Best practices (two-path model, dedicated containers, dual-track embeddings) | [`references/best-practices.md`](./references/best-practices.md) | Before designing memory layout |

Auth methods: `X-API-KEY: <api-key>` or `Authorization: Bearer <api-key>`.

> **Cannot connect / 401 / 403 / 空响应** → 先看本文 `## Gotchas`；展开的失败矩阵在 [`references/troubleshooting.md`](./references/troubleshooting.md)；大批量 ingest / persistent queue / `/jobs/{id}` polling / automatic memory / 平台支持在 [`references/OPERATIONS.md`](./references/OPERATIONS.md)。

## Files in This Skill

> `references/*.md` are listed in the **Reference Documents** table above. The
> non-reference files in this skill:

| File | Purpose | When to load |
|------|------|---------|
| `references/templates/config.toml.template` | Config file template | During first-time setup |
| `scripts/batch-ingest.py` | Bulk ingest script | For large memory imports |
| `scripts/job-ledger.py` | Async job ledger: `add` / `sweep` / `list` for background KG build jobs | Used by `/tm jobs`, `/tm upload`, and the SessionStart hook |
| `hooks/common.sh` | Shared bash library for all hooks (config loading, API calls, JSON escaping) | Auto-loaded by hooks |
| `hooks/session-start` | SessionStart hook: health check + memory recall injection | Auto-registered |
| `hooks/prompt-inject` | UserPromptSubmit hook: recall-keyword / long-prompt triggered memory injection | Auto-registered |
| `hooks/post-commit-memory` | PostToolUse hook: instruct agent to store git commit summary | Auto-registered |
| `hooks/session-stop` | Stop hook: auto-store session summary memory | Auto-registered |

## When NOT to Use

- Deploying the backend service -> use the `transcendence-memory-server` repository
- Managing Docker, systemd, or Nginx -> use the `transcendence-memory-server` repository
- Troubleshooting server-side problems such as 5xx errors, storage issues, or logs -> use the `transcendence-memory-server` repository
- Configuring Embedding, LLM, or VLM models -> this is a server-side concern and does not need to be handled by the skill
