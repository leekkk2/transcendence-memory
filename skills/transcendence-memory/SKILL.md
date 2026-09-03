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
- **Governance (server v0.20)**: runtime config center, a 6-tool governance toolbox (SAFE / LLM / destructive-reversible), a dreaming subsystem (background/manual memory tidy-up), and an opt-in LLM tool-use orchestration agent with human approval — all dry-run-first and off by default. See [`references/governance.md`](./references/governance.md).
- **Troubleshooting**: diagnose connection and retrieval issues

## Install

### Claude Code (recommended)

Inside a Claude Code session:

```text
/plugin marketplace add leekkk2/transcendence-memory
/plugin install transcendence-memory@transcendence-memory
```

> The `@transcendence-memory` suffix names the marketplace (set by `.claude-plugin/marketplace.json` `.name`). Always include it — Claude Code resolves plugin installs by `<plugin>@<marketplace>` per the [official docs](https://code.claude.com/docs/en/discover-plugins).

Or use the GUI: run `/plugin` to open the plugin manager → **Discover** tab → search "transcendence-memory" → Install.

**After install, restart Claude Code.** `/reload-plugins` loads hooks + skill body into context but does **not** rebuild the slash-command parser (known issue [anthropics/claude-code#37862](https://github.com/anthropics/claude-code/issues/37862)) — `/tm` / `/transcendence-memory` slash commands will only register after a full restart. The four lifecycle hooks (SessionStart / UserPromptSubmit / PostToolUse / Stop) are active immediately on next launch.

> Updating later: `/plugin update transcendence-memory@transcendence-memory` (Claude Code manages the cache).
> Or use the bundled `/tm upgrade` command, which `git pull --ff-only`s the installed clone (see Gotchas if it reports `fast-forward` failure).

### Other agents (Cursor / Codex / manual git clone)

For agents without a Claude Code-compatible plugin manager:

```bash
# Community installer (3rd-party — wraps a git clone into a stable layout)
npx skills add https://github.com/leekkk2/transcendence-memory --skill transcendence-memory
```

Or clone directly into the host agent's skill directory:

```bash
git clone https://github.com/leekkk2/transcendence-memory.git \
  ~/.agents/skills/transcendence-memory
```

> Cursor's directory is `~/.cursor/skills/`; consult your agent's docs for the canonical path. `/tm upgrade` auto-detects the install root from a list of well-known paths.

## Principles

- **Retrieval has exactly one correct path — HTTP only (STRICT).** Recalling / searching memory goes **only** through this skill's backend over HTTP: the configured `endpoint`'s `/search` or `/query` (preferred wrapper: `bash scripts/tm-search.sh search <query>`). **Never `docker exec` into any local database to look for memories** — not `supabase_db_*`, not a `claude-mem` postgres, not `memory-app` / `memory-copilot`, not any app's local `supabase` / `psql`. Those are *other projects' private stores* with no relationship to this skill's backend; querying them is both wrong (no data there) and a cross-project contamination violation. If `scripts/tm-search.sh` is unavailable, fall back to inline `curl` against the configured `endpoint` (see the curl escape hatch in the slash-command STRICT block below) — still pure HTTP, never a container shell.
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

### 5. Semantic Memory ID (主动提炼语义化关键词 ID)

记忆存储时，**严禁使用无意义的时间戳/随机字符串**（如 `mem-1788444306-4556`）。
AI 在调用记忆命令时，**必须主动从该条记忆的决策、实体与动作中提炼 2~4 个关键词**，作为语义化 ID：
- **格式要求**：`--id <topic>-<action>-<date>`（小写 kebab-case，如 `--id redis-port-conflict-20260903`）。
- **自动化兜底**：`tm-remember.sh` 会在未指定 `--id` 时自动从 `--title` 和 `--tags` 提炼语义 slug，但 AI **应显式主动提炼并传入 `--id`**，确保 ID 的语义准确度和全局可溯源性。
- **示例**：
  - ✅ 好：`bash scripts/tm-remember.sh "..." --title "..." --tags "..." --id "alishell-proxy-timeout-fix-20260903"`
  - ❌ 坏：省略 `--id` 导致回退到随机时间戳 `mem-1788444306-4556`。

## AI Behavior — `/tm` is a slash command, not a bare shell binary (STRICT)

`/tm` is a Claude Code **slash command** invoked through the `SlashCommand` tool.
It is NOT a shell binary, so passing the slashed form to a shell always fails:

```bash
$ /tm search "..."         # ❌ no such file or directory ( /tm is a slash command )
$ tm-codex search "..."    # ❌ command not found ( no such binary )
$ tm search "..."          # ❌ command not found — UNLESS the user installed
                           #    `pipx install transcendence-memory-cli` (optional, not shipped here)
```

A separate, **optional** shell CLI named `tm` does exist (`pipx install transcendence-memory-cli`, shipped from the server repo's `cli-package/`). It is a *different thing* from the `/tm` slash command and is **not** bundled with this skill — only present if the user installed it themselves. Do not assume it exists, and never conflate `/tm <cmd>` (the slash command, this section) with the installed `tm <cmd>` binary. There is no `tm-codex` binary. The AI MUST use one of these paths only (all pure HTTP — never a shell into a DB):

1. **Preferred — bundled wrapper script** (works on any agent — Claude / Gemini / Codex — in or out of Claude Code):
   ```bash
   bash scripts/tm-search.sh search <query>     # semantic recall over the configured container
   bash scripts/tm-search.sh query <q>          # multimodal RAG query
   bash scripts/tm-search.sh status             # one-line health probe
   bash scripts/tm-search.sh containers [pat]   # list containers (name/objects/index state)
   bash scripts/tm-search.sh jobs <id>          # one job's state in plain words
   bash scripts/tm-remember.sh "text" [--title t] [--tags a,b]   # quick memory store (jq-built JSON + secret redaction)
   ```
   It reads `~/.transcendence-memory/config.toml`, builds the JSON body zsh-glob-safely (jq + heredoc, never bare braces), adds a WAF-compatible User-Agent, honors `*_PROXY` with auto-fallback to direct, and lazily absorbs a cold-start backend on first call — so agents don't need the optional `tm` CLI installed, and never need a (nonexistent) `tm-codex` binary. (No separate warm-up SOP — warm-up is handled inside the script.)

2. **`SlashCommand` tool** (when running inside Claude Code):
   ```
   SlashCommand({ command: "/tm search <query>" })
   ```

3. **Escape hatch — inline curl** (only when the wrapper is unavailable):
   ```bash
   ENDPOINT="$(grep '^endpoint' ~/.transcendence-memory/config.toml | cut -d'"' -f2)"
   API_KEY="$(grep '^api_key' ~/.transcendence-memory/config.toml | cut -d'"' -f2)"
   CONTAINER="$(grep '^container' ~/.transcendence-memory/config.toml | cut -d'"' -f2)"
   curl -sS -X POST "$ENDPOINT/search" \
     -H "X-API-KEY: $API_KEY" -H "Content-Type: application/json" \
     -d "{\"container\":\"$CONTAINER\",\"query\":\"<query>\",\"topk\":5}"
   ```

If the AI catches itself about to invoke `Bash({command: "/tm ..."})` (slash-command
form passed to a shell), STOP and switch to one of the paths above. The same applies
to the long-form alias `/transcendence-memory <command>`. (`Bash({command: "tm ..."})`
only works if the user installed the optional `transcendence-memory-cli` package — it
is not part of this skill, so prefer the wrapper script or `SlashCommand` above.)

> The `Example` column in the command table below shows the slash-command form.
> Invoke via the `SlashCommand` tool. For raw HTTP fallback, see `references/api-reference.md`.

## AI Behavior — async ingestion silent-mode (v0.4.1+, STRICT)

Any call that returns an integer `pid` / `job_id` from a server v0.15.0+ KG-write endpoint (`/tm upload`, raw `POST /documents/text`, `POST /documents/upload`) is **fire-and-forget**. HTTP already returned — the task is handed off. The AI **MUST**:

1. **Never poll `/jobs/{id}` to wait for completion — this rule scopes ONLY to the KG-build jobs above** (`/documents/*`, `/tm upload`). No `until` loops, no sleep-loops, no blocking waits for those. (`/embed` async jobs are an index rebuild, **not** a KG-build job, and MAY be polled via `GET /jobs/{id}` — the `until ... sleep` polling templates in `references/*` are scoped to `/embed`, not to these KG-build jobs.)
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
| `remember <text>` | Store one memory quickly (preferred wrapper: `bash scripts/tm-remember.sh "<text>"` — jq-built JSON, no hand-escaping 422s, built-in secret redaction) | `/tm remember Port conflicts caused the deployment failure` |
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

### Operational / admin HTTP endpoints (server v0.18, no `/tm` shortcut)

These have no `/tm` command — call them directly over HTTP (all need auth). Full request / response schemas in [`references/api-reference.md`](./references/api-reference.md) and [`references/commands.md`](./references/commands.md).

| Method + path | Purpose |
|---|---|
| `GET /index-status` · `GET /containers/{name}/index-status` | Per-container index state machine (`stale`/`indexing`/`ready`/…) + object counts + embed backlog summary — tells you whether a sibling is actually embedded before you union it |
| `POST /embed-multimodal` (multipart) | Embed one media file (image/audio/video) via Gemini-native multimodal embedding → one LanceDB vector row, recallable by `/search`. Requires the container to route to a `gemini_native` profile |
| `POST /containers/aliases` · `GET /containers/aliases` · `DELETE /containers/aliases/{alias}` | Manage container-name alias routing (alias → canonical); admin only |
| `GET /admin/usage/{summary,endpoints,containers,timeseries}` · `POST /admin/usage/cleanup` | Request-usage analytics (call counts / latency / per-container / time buckets) + retention cleanup |
| `GET /admin/ui` · `POST /admin/ui/{login,logout}` · `GET /admin/ui/me` | Cookie-session admin dashboard SPA (browser-facing; agents rarely call directly) |

### Governance / dreaming / orchestration-agent endpoints (server v0.20, no `/tm` shortcut)

Self-hosted autonomous memory-governance subsystem. **All dry-run-first and safe by default** — a fresh deploy never mutates data on its own. Full request/response schemas in [`references/api-reference.md`](./references/api-reference.md#治理与梦境端点v020);命令速查 in [`references/commands.md`](./references/commands.md#治理--梦境--编排-agentv020); overview + safety model in [`references/governance.md`](./references/governance.md).

| Method + path | Purpose |
|---|---|
| `GET /admin/config` · `PUT /admin/config` | Runtime config center — enumerate / batch-write known config keys (hot-reload). Sensitive keys never echo a value (only `configured`). The single place to toggle tools / dreaming schedule / agent limits |
| `GET /admin/tools` · `POST /admin/tools/{tool}/invoke` | Governance toolbox: matrix of 6 preset tools (SAFE / LLM / destructive-reversible) + per-container enable map; invoke one (`dry_run=true` default; SAFE always real, LLM/destructive need `dry_run=false`) |
| `GET /admin/dreaming/status` · `POST /admin/dreaming/trigger` | Dreaming subsystem: background/manual memory tidy-up cycle. Trigger is report-only by default; real deletes additionally gated by `config:dreaming:prune_apply` |
| `POST /admin/agent/{name}/invoke` · `GET /admin/agent/runs` | LLM tool-use orchestration agent (opt-in behind `TM_AGENT_ORCHESTRATION_ENABLED`, default OFF). Reversible tools apply only when `dry_run=false` AND `allow_apply=true` |
| `GET /admin/agent/approvals` · `POST …/{id}/approve` · `POST …/{id}/reject` | Human approval queue — `/approve` is the **only** place a destructive governance tool runs for real; the unattended loop never executes destructive tools itself |

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
| `/health` / `/search` 回 `200` 但服务其实没就绪 | 冷启动（切换/重启后）body 携带 `degraded:true` / `per_container_status: timeout\|not_initialized` / `initialized:false`，**200 ≠ 成功** | **解析 body**，命中冷启动信号就把同一查询短间隔重发几次直到 ok（`tm-search.sh` 已自动做）。`curl --retry` 抓不到（200 在它眼里就是成功） |
| 单容器查询无故 `degraded:true` | 默认 `union:false`；但一旦走 union，存在却未 embed 的 sibling（如 `*_openai`）会把整次检索拖成 degraded | 主容器结果其实正常——本次显式传 `"union":false` 跳过 sibling，或先给 sibling 跑一次 `/embed` 再 union（v0.18 起 server 会自动**软跳过**未 embed 的 sibling，见下条） |
| union 时仍看到 `not_initialized` sibling 噪音 / 整次检索失败 | v0.18：从未 embed（无 `chunks` 表）的 sibling 在 union 解析阶段被**软跳过**，不再拖累主容器；旧行为是把它算进 `per_container_status` 致 `degraded`/`error` | 让 sibling 先 `/embed` 一次即可下次自动恢复双轨；只要主容器出结果，本次就照常返回。判断某容器是否真就绪用 `GET /containers/{name}/index-status`（`state` 字段） |
| 部分容器失败但本应有结果，却被当成整体失败 | v0.18 优雅降级：只要**任一容器**（尤其主容器）有结果就 200 返回，body 标 `is_degraded:true`（= 旧 `degraded`，同值双写）+ `fallback_source:"partial_containers"`；**全部失败才** `status:"error"`。部分成功 **不再**弹错误文案（`message` 为 null） | 读 `is_degraded` / `degraded`（任选，同值）判断结果完整性，照常渲染 `results`；只有 `status==="error"` 才当真失败。详 `references/troubleshooting.md` 降级段 |
| `/search` 返回空 `results` 但 `blocked_low_score>0` | v0.19.0 score-gate：服务端配了 `similarity_threshold` 或请求传了 `score_threshold`，命中分低于阈值被丢弃 | 这是阈值过严，**不是库空、不是冷启动**——放宽/去掉 `score_threshold` 重查，或运维下调 `similarity_threshold`（dashboard 热重载）。默认不开 → 该字段恒 0 |
| 想给检索结果加"源文件第几行"定位却拿不到行号 | v0.19.0 行号溯源：`results[].lineStart`/`lineEnd` + `citations[]` 才有；**P4 前 ingest 的老 chunk 恒 `null`** | 读 `lineStart`/`lineEnd`（判 `!=null` 再用）；老记忆无行号是预期（零 re-embed 向后兼容），新 ingest 自动带 |
| `fallback_rendered` 非 null / 答案像"模板话术" | v0.19.0 opt-in 兜底模板：score-gate 全拦或全容器降级、且运维配了 `fallback_template` 时渲染 | **别当高置信检索结果**呈现；默认未配模板时此字段恒 `null`，无需关注 |
| 服务**拒绝启动**，日志打 `FATAL: EMBEDDING_DIM=X disagrees with LanceDB schemas` | 启动期 dim 一致性闸（v0.18 已在 prod）：`.env` 的 `EMBEDDING_DIM` 与已落库容器的 vec 列维度不符——历史上曾静默错配致 `/search` 连续 14h 报 dim 错。守卫宁可不启动也不放行 | 把 `EMBEDDING_DIM`/`EMBEDDING_MODEL` 对齐已存维度，或用新 model 重建受影响容器；**确在迁移途中**才临时 `TM_ALLOW_DIM_DRIFT=1` 跳过。这是 server 端 env，不在本 skill 配置 |
| 有全局代理时直连超时 / 或反过来代理不通 | endpoint 常被 Cloudflare fronting：某些机器上 env 代理才是快且可靠的路径（GFW 区直连可能 ~12s 超时），另一些机器反之 | 别预设"代理 = 问题"。`tm-search.sh` 默认走 `*_PROXY`、连接失败再自动回退直连；`TM_NO_PROXY=1` 强制直连 |

> **黄金法则**：HTTP 200 ≠ 业务完成。所有写路径（`/embed` / `/documents/*` / `/upload`）都是 fire-and-forget；只有 `/search` 同步。冷启动时连读路径的 200 都可能携带 degraded body——务必解析。

## First-Time Setup

On first use, read `references/setup.md` to complete configuration.

The core flow has only two steps:
1. Get a **connection token** from the server (through the `/export-connection-token` endpoint or from an administrator)
2. Run `/tm connect <token>` to finish setup automatically

Or run `/tm connect --manual` and enter the values step by step.

To verify connectivity afterwards, prefer `bash scripts/tm-search.sh status` (a zero-dependency health probe that runs on any agent — Claude / Gemini / Codex — and parses the body for cold-start signals, so a degraded `200` is not mistaken for success). No binary needs to be installed for this — the wrapper script is enough; the optional `tm` CLI (`transcendence-memory-cli`) is a separate convenience, and there is no `tm-codex` binary.

> After configuration is complete, `references/setup.md` no longer needs to be loaded into context.

## Reference Documents

| Topic | File | When to load |
|---|---|---|
| First-time setup (token decode, config.toml, verify) | [`references/setup.md`](./references/setup.md) | First use only |
| Full HTTP API (request / response / error schemas, field-alias table) | [`references/api-reference.md`](./references/api-reference.md) | When you need exact field types |
| **Per-command curl / options matrix** | [`references/commands.md`](./references/commands.md) | When invoking any `/tm <command>` — full HTTP body, options, response schema |
| **Governance framework (v0.20)** — toolbox / dreaming / orchestration agent + dry-run-first safety model | [`references/governance.md`](./references/governance.md) | When driving `/admin/config` · `/admin/tools` · `/admin/dreaming/*` · `/admin/agent/*` |
| Architecture (dual-path model, container isolation, multi-embedding routing) | [`references/ARCHITECTURE.md`](./references/ARCHITECTURE.md) | When understanding how it works internally |
| Troubleshooting (connect / 401 / 403 / empty search / empty query / cold-start / union degraded / WAF 403) | [`references/troubleshooting.md`](./references/troubleshooting.md) | When something doesn't work |
| Operations (bulk ingest, persistent queue, automatic memory, platform support, multi-embedding ops) | [`references/OPERATIONS.md`](./references/OPERATIONS.md) | When operating at scale |
| Best practices — English / 中文 (two-path model, dedicated containers, dual-track embeddings) | [`references/best-practices.md`](./references/best-practices.md) · [`references/best-practices.zh-CN.md`](./references/best-practices.zh-CN.md) | Before designing memory layout |
| Retrofit playbook (back-filling fuzzy index cards onto legacy ASCII-id memories) | [`references/retrofit-playbook.md`](./references/retrofit-playbook.md) | When migrating old memories for recall |

Auth methods: `X-API-KEY: <api-key>` or `Authorization: Bearer <api-key>`.

> **Cannot connect / 401 / 403 / 空响应** → 先看本文 `## Gotchas`；展开的失败矩阵在 [`references/troubleshooting.md`](./references/troubleshooting.md)；大批量 ingest / persistent queue / `/jobs/{id}` polling / automatic memory / 平台支持在 [`references/OPERATIONS.md`](./references/OPERATIONS.md)。

## Files in This Skill

> `references/*.md` are listed in the **Reference Documents** table above. The
> non-reference files in this skill:

| File | Purpose | When to load |
|------|------|---------|
| `references/templates/config.toml.template` | Config file template | During first-time setup |
| `scripts/tm-search.sh` | Preferred retrieval wrapper: `search` / `query` / `status` / `containers` / `jobs` over HTTP (config load, zsh-glob-safe JSON, proxy auto-fallback, lazy cold-start warm-up) | Primary path for recall + health probe + read-only admin peeks |
| `scripts/tm-remember.sh` | Preferred quick-store wrapper: `POST /ingest-memory/objects` with jq-built JSON (kills the hand-escaping 422 class), self-contained secret redaction, `--tags/--title/--no-embed/--json` | Primary path for `/tm remember`-style single-memory writes |
| `scripts/batch-ingest.py` | Bulk ingest script (built-in `--redact`) | For large memory imports |
| `scripts/job-ledger.py` | Async job ledger: `add` / `sweep` / `list` for background KG build jobs | Used by `/tm jobs`, `/tm upload`, and the SessionStart hook |
| `scripts/sync-skill.sh` | One-way canonical→installed mirror (anti-drift); run after editing the canonical skill | Maintenance only |

The lifecycle hooks below live at the **plugin/repo root** (`../../hooks/`, one level up from this skill dir) and are auto-registered **only in the Claude Code plugin install** (a bare skill install has none of them — including auto credential redaction; use `batch-ingest.py --redact` there):

| File (at `../../hooks/`) | Purpose | When active |
|------|------|---------|
| `hooks/common.sh` | Shared bash library for all hooks (config loading, API calls, JSON escaping) | Plugin install only — auto-loaded by hooks |
| `hooks/session-start` | SessionStart hook: health check + memory recall injection | Plugin install only — auto-registered |
| `hooks/prompt-inject` | UserPromptSubmit hook: recall-keyword / long-prompt triggered memory injection | Plugin install only — auto-registered |
| `hooks/post-commit-memory` | PostToolUse hook: instruct agent to store git commit summary | Plugin install only — auto-registered |
| `hooks/session-stop` | Stop hook: auto-store session summary memory | Plugin install only — auto-registered |

## Governance subsystem — server-side env switches (v0.20)

The v0.20 governance toolbox / dreaming / orchestration agent are configured **server-side** — most knobs live in the runtime config center (`config:dreaming:*` / `config:tools:*` / `config:agent:*`, hot-reloaded via `PUT /admin/config`; full list with defaults in [`references/governance.md`](./references/governance.md) §5). The orchestration **agent has one master env gate**:

- `TM_AGENT_ORCHESTRATION_ENABLED` — default `0` (OFF). When off, `POST /admin/agent/{name}/invoke` returns `status:"disabled"` and never enqueues, so a default deploy runs no autonomous loop. Set `1` (server `.env`) to allow agent runs.
- `TM_AGENT_MAX_STEPS` (default 6) / `TM_AGENT_RUN_TIMEOUT_SEC` (default 300) / `TM_AGENT_DAILY_TOKEN_BUDGET` (blank = no extra cap) bound each run; env wins over the matching `config:agent:*` key.

These are **server `.env` concerns**, not this skill's `config.toml` — the skill only *calls* the endpoints. LLM routing stays on the sanctioned gateway (HR-9, `LLM_*`); no new model env is introduced.

## When NOT to Use

- Deploying the backend service -> use the `transcendence-memory-server` repository
- Managing Docker, systemd, or Nginx -> use the `transcendence-memory-server` repository
- Troubleshooting server-side problems such as 5xx errors, storage issues, or logs -> use the `transcendence-memory-server` repository
- Configuring Embedding, LLM, or VLM models -> this is a server-side concern and does not need to be handled by the skill
