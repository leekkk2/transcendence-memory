# Transcendence Memory

> **Long-term memory for AI coding agents. Self-hosted, multi-modal, works across sessions.**

[Chinese Documentation](README.zh-CN.md)

Transcendence Memory is an agent skill that gives any AI coding CLI persistent memory — search past decisions, store key insights, and query a knowledge graph built from your documents.

## Why

AI conversations are ephemeral. This skill lets your agent:
- **Remember** — persist decisions, lessons learned, and context across sessions
- **Recall** — semantic search to recover past state in new conversations
- **Reason** — multimodal RAG queries over PDFs, images, and code with LLM-generated answers
- **Reuse** — cross-project knowledge sharing via container isolation

## Install

One-line install:

```bash
npx skills add https://github.com/leekkk2/transcendence-memory --skill transcendence-memory
```

Or use the plugin marketplace inside a Claude Code session:

```
/plugin marketplace add leekkk2/transcendence-memory
/plugin install transcendence-memory
```

Restart the session after installation, then use the `/tm` command.

## Quick Start

### 1. Deploy the backend

You need a running [transcendence-memory-server](https://github.com/leekkk2/transcendence-memory-server):

```bash
git clone https://github.com/leekkk2/transcendence-memory-server.git
cd transcendence-memory-server
cp .env.example .env   # edit with your API keys
docker compose up -d --build
```

### 2. Connect

Get a connection token from the server, then tell your agent:

```
/tm connect eyJlbmRwb2ludCI6Imh0dHBz...
```

Or connect manually:

```
/tm connect --manual
```

The agent will write `~/.transcendence-memory/config.toml` with your endpoint, API key, and container name.

### 3. Use

```
/tm search what was the database migration strategy
/tm remember port 5432 conflicts with local postgres, use 5433
/tm query summarize the authentication architecture
/tm upload ./design-doc.pdf
/tm status
```

## Built-in Commands

| Command | Description |
|---------|-------------|
| `/tm connect <token>` | Import connection token |
| `/tm connect --manual` | Manual endpoint/key/container setup |
| `/tm status` | Check connection and server health |
| `/tm search <query>` | Semantic memory search |
| `/tm remember <text>` | Quick-store a memory |
| `/tm embed` | Rebuild search index |
| `/tm query <question>` | Multimodal RAG query (LLM answer) |
| `/tm upload <file>` | Upload PDF/image/MD to knowledge graph |
| `/tm containers` | List all containers |
| `/tm batch <file.jsonl>` | Bulk import memories |
| `/tm auto on` | Enable automatic memory on git commits |
| `/tm auto off` | Disable automatic memory |
| `/tm auto status` | Show auto-memory configuration |

## Automatic Memory

When enabled, transcendence-memory automatically stores a one-line summary after every git commit. This is powered by lifecycle hooks that integrate with the host AI coding CLI.

```
/tm auto on       # enable
/tm auto off      # disable
/tm auto status   # check
```

Each auto-commit memory is tagged `auto-commit` and follows this format:

```
[commit abc1234] fix: resolve port conflict | files: M docker-compose.yml, M .env.example
```

### Supported platforms

| Platform | Hook mechanism | Status |
|----------|---------------|--------|
| Claude Code | `hooks/hooks.json` (SessionStart + PostToolUse) | Supported |
| Cursor | `hooks/hooks-cursor.json` (camelCase events) | Supported |
| Copilot CLI | Claude Code compatible | Supported |
| Augment Code | Claude Code compatible | Supported |
| Gemini CLI | `hooks/adapter.py` (AfterTool) | Adapter ready |
| Windsurf | `hooks/adapter.py` (post-tool-use) | Adapter ready |
| Vibe CLI | `hooks/adapter.py` (post-tool-call) | Adapter ready |
| Cline / Roo Code | `hooks/adapter.py` (JSON stdin/stdout) | Adapter ready |

The `hooks/adapter.py` normalizes input from all platforms into a unified format. For platforms without native hook support, add transcendence-memory instructions to the platform's rules file.

## Architecture

```
Your Agent + this skill
    |
    | HTTPS + API Key
    v
transcendence-memory-server
    |-- LanceDB vector search (text memories)
    |-- LightRAG knowledge graph (entity/relation extraction)
    └-- RAG-Anything (PDF/image/table multimodal parsing)
```

This skill is a **stateless client** — all data lives on your server. The skill provides the agent with instructions and curl templates to interact with the API.

## Project Structure

```
skills/transcendence-memory/
  SKILL.md                    # Main skill entry (agent reads this)
  references/
    setup.md                  # First-time configuration guide
    api-reference.md          # Complete API reference
    ARCHITECTURE.md           # System architecture
    OPERATIONS.md             # Verification checklist
    troubleshooting.md        # Diagnostic guide
    templates/
      config.toml.template    # Config file template
  scripts/
    batch-ingest.py           # Batch import (zero deps, Python stdlib)
hooks/
  hooks.json                  # Claude Code hook config
  hooks-cursor.json           # Cursor hook config
  run-hook.cmd                # Cross-platform polyglot wrapper
  session-start               # SessionStart handler
  post-commit-memory          # PostToolUse handler (git commit)
  auto-memory-prompt.md       # Agent instructions for auto-memory
  adapter.py                  # Multi-platform hook adapter
```

## Related

- **Server**: [transcendence-memory-server](https://github.com/leekkk2/transcendence-memory-server) — the backend that stores, indexes, and retrieves memories
- **API Docs**: Auto-generated at `http://your-server:8711/docs` (FastAPI Swagger UI)

## License

MIT
