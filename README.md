# Transcendence Memory

> **Long-term memory for AI coding agents. Self-hosted, multi-modal, works across sessions.**

Transcendence Memory is an agent skill that gives any AI coding CLI persistent memory — search past decisions, store key insights, and query a knowledge graph built from your documents.

## Why

AI conversations are ephemeral. This skill lets your agent:
- **Remember** — persist decisions, lessons learned, and context across sessions
- **Recall** — semantic search to recover past state in new conversations
- **Reason** — multimodal RAG queries over PDFs, images, and code with LLM-generated answers
- **Reuse** — cross-project knowledge sharing via container isolation

## Compatibility

Works with any AI coding CLI that supports the AgentSkills `SKILL.md` format:

| Platform | Install |
|----------|---------|
| **Claude Code** | `/install-skill https://github.com/leekkk2/transcendence-memory` |
| **OpenClaw** | `claw skill install transcendence-memory` |
| **Codex CLI** | Copy to `~/.codex/skills/transcendence-memory/` |
| **Any Agent** | Load `SKILL.md` as system instructions |

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
```

## Related

- **Server**: [transcendence-memory-server](https://github.com/leekkk2/transcendence-memory-server) — the backend that stores, indexes, and retrieves memories
- **API Docs**: Auto-generated at `http://your-server:8711/docs` (FastAPI Swagger UI)

## License

MIT
