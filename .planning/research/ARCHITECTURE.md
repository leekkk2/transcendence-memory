# Architecture Research

**Domain:** OpenClaw-compatible memory deployment skill plus separate backend runtime
**Researched:** 2026-03-23
**Confidence:** MEDIUM

## Standard Architecture

### System Overview

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Operator Layer                                                               │
├──────────────────────────────────────────────────────────────────────────────┤
│  OpenClaw Agent / User   Bilingual Docs + Runbooks   Smoke Tests / CI       │
│           │                       │                        │                 │
├───────────┴───────────────────────┴────────────────────────┴─────────────────┤
│ Control Layer                                                                │
├──────────────────────────────────────────────────────────────────────────────┤
│  Lean Skill Pack  ──>  CLI / Config App  ──>  Shared Schemas + API Client   │
├──────────────────────────────────────────────────────────────────────────────┤
│ Deployment Layer                                                             │
├──────────────────────────────────────────────────────────────────────────────┤
│  Topology Detection   Docker Adapter   systemd Adapter   Secret Store        │
│  Bundle Export/Import                                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│ Runtime Layer                                                                │
├──────────────────────────────────────────────────────────────────────────────┤
│  Memory API   Auth Middleware   Search / Embed Service   Provider Adapter    │
├──────────────────────────────────────────────────────────────────────────────┤
│ Data Layer                                                                   │
│  LanceDB Path   Local Config Profiles   Secret Material   Logs / Health      │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Skill pack | Detect role/topology, explain flows, call stable commands, verify outcomes | `SKILL.md` plus `scripts/`, `references/`, `assets/`; no long-lived runtime |
| CLI/config layer | Source of truth for init/config/auth/deploy/export/import/check commands | Single packaged CLI with shared schema validation and JSON/text output modes |
| Deployment layer | Convert desired state into a running service on the current machine | Docker Compose first, Linux `systemd` as native path, platform-specific install helpers |
| Backend service | Serve `/health`, `/search`, `/embed`-style APIs and own provider/storage access | One HTTP service with auth, indexing/search logic, and local persistence |
| Shared contracts | Keep config, API, and connection bundle formats identical across layers | Shared schema package used by CLI, backend, tests, and docs examples |
| Docs/runbooks | Human and AI-readable operating guidance, topology guides, and troubleshooting | Bilingual markdown under `docs/` and skill `references/`; not executable |

## Recommended Project Structure

```text
skill/
├── SKILL.md                 # Lean orchestration entrypoint for OpenClaw
├── scripts/                 # Small wrappers that call the CLI and detect topology
├── references/              # Setup, topology, security, troubleshooting guides
└── assets/                  # Templates, sample bundles, diagrams

packages/
├── cli/                     # `init`, `config`, `auth`, `deploy`, `export`, `import`, `check`
│   ├── src/commands/
│   ├── src/platform/
│   └── src/output/
└── shared/                  # Schemas, API client, config resolver, bundle model
    ├── src/schemas/
    ├── src/config/
    └── src/api_client/

services/
└── memory-backend/          # Long-lived runtime, auth middleware, provider adapters
    ├── src/api/
    ├── src/auth/
    ├── src/search/
    ├── src/embed/
    └── src/storage/

deploy/
├── docker/                  # `compose.yaml`, env templates, health probes
├── systemd/                 # Unit files, credential templates, Linux-only helpers
└── scripts/                 # Cross-platform bootstrap and verification scripts

docs/
├── architecture/            # Diagrams, component boundaries, build-order rationale
├── operator/                # Same-machine and split-machine playbooks
└── security/                # Secret handling, redacted bundle, auth guidance

tests/
├── contract/                # Bundle/config/API schema tests
├── integration/             # CLI <-> deploy <-> backend tests
└── e2e/                     # Same-machine and split-machine acceptance tests
```

### Structure Rationale

- **`skill/`:** Keep OpenClaw-facing instructions small and stable. The skill should orchestrate, never become the backend.
- **`packages/cli/`:** Every mutable operator action should exist as a real command first. The skill then becomes a thin wrapper over something testable.
- **`packages/shared/`:** Config drift is the main failure mode in this kind of project. One shared schema package prevents that.
- **`services/memory-backend/`:** Backend runtime stays independently runnable, testable, and deployable without the skill.
- **`deploy/`:** OS and runtime specifics belong in deployment adapters, not in backend business logic or skill prose.
- **`docs/`:** Docs are a separate deliverable because this project is partly an operator workflow product, not only an API.

## Architectural Patterns

### Pattern 1: Thin Skill, Thick CLI

**What:** The skill performs environment detection, planning, confirmation, and command invocation. All state mutation happens through the CLI.
**When to use:** Always. This is the cleanest way to keep OpenClaw compatibility without embedding runtime logic into the skill.
**Trade-offs:** Slightly more upfront work in the CLI, but much lower long-term maintenance and much better test coverage.

**Example:**
```bash
tmemory init --role backend --topology split
tmemory provider set openai --model text-embedding-3-large
tmemory auth login
tmemory backend deploy --target docker
tmemory backend export-connection --output ./connection.bundle.json
```

### Pattern 2: Shared Contract Package

**What:** API payloads, config profiles, and connection bundles are defined once and imported everywhere.
**When to use:** Any time the backend, CLI, tests, and docs all speak the same object model.
**Trade-offs:** Adds one more package boundary, but removes duplicated parsing and silent drift.

**Example:**
```python
from pydantic import BaseModel, AnyHttpUrl
from typing import Literal


class ConnectionBundle(BaseModel):
    schema_version: Literal["v1"]
    public_base_url: AnyHttpUrl
    auth_mode: Literal["apiKey", "oauth"]
    default_container: str
    tls_mode: Literal["system", "custom_ca", "insecure"]
    ca_path_hint: str | None = None
```

### Pattern 3: Deploy Adapters Behind a Stable Interface

**What:** The CLI selects a platform adapter such as Docker or `systemd`, but the backend service is unaware of how it is started.
**When to use:** Required for Linux, macOS, and Windows support without hard-coding one deployment path into the runtime.
**Trade-offs:** Slight abstraction overhead, but much cleaner multi-platform support.

**Example:**
```python
adapter = deployment_registry.resolve(target="docker", platform=os_name)
adapter.install()
adapter.configure(resolved_profile)
adapter.start()
adapter.healthcheck()
```

## Data Flow

### Same-Machine Deployment

```text
[User / OpenClaw Agent]
    ↓
[Skill]
    ↓ invoke stable command set
[CLI]
    ↓ writes non-sensitive config
[Local Profile Store]
    ↓ writes sensitive material
[Secret Store / Protected File]
    ↓ selects deployment target
[Docker or systemd Adapter]
    ↓ starts service
[Backend Service]
    ↓ opens storage and provider clients
[LanceDB + Embedding Provider]
    ↓
[CLI smoke tests: health/search/embed]
    ↓
[Skill reports success/failure]
```

### Split-Machine Deployment

```text
Backend host
[User / Agent]
    ↓
[Skill]
    ↓
[CLI init/config/auth/deploy]
    ↓
[Deploy Adapter]
    ↓
[Backend Service]
    ↓ export non-sensitive connection metadata
[Redacted Connection Bundle]
    ↓ out-of-band transfer chosen by user
Frontend host
[Skill]
    ↓
[CLI import-connection]
    ↓
[Local frontend profile]
    ↓ local-only secret entry or OAuth login
[Frontend check/search]
    ↓
[Remote Backend Service]
```

### Secure Handoff: Redacted Connection Bundle

```text
[Backend runtime config]
    ↓ filtered through shared bundle schema
[CLI backend export-connection]
    ↓ strips secrets and internal-only values
[connection.bundle.json]
    ↓ copy via chat/file/secure share
[CLI frontend import-connection]
    ↓ validates schema + version + required fields
[Frontend local profile]
    ↓ prompts for missing secret material locally
[Frontend runtime uses remote backend]
```

**Bundle should include:**
- `schema_version`
- `public_base_url`
- `auth_mode`
- `default_container` or namespace hint
- TLS mode and optional CA path hint or fingerprint
- backend feature/version metadata needed for compatibility checks

**Bundle must not include:**
- provider API keys
- OAuth refresh tokens or client secrets
- backend local bind addresses not meant for remote use
- private filesystem paths
- raw secret-store contents

### Runtime Request Flow

```text
[OpenClaw host]
    ↓ HTTPS request using imported profile
[Backend API]
    ↓ auth check
[Search / Embed Service]
    ↓
[Embedding Provider]
    ↓
[LanceDB]
    ↓ results / status
[Backend API response]
```

### Configuration State

```text
[Shared Schemas]
    ↓ validate
[CLI Commands]
    ↓ read/write
[Public Profile Store]     [Secret Store]
    ↓                           ↓
[Deployment Adapter]       [Backend Runtime]
    ↓                           ↓
[Running Service] ←─────────────┘
```

### Key Data Flows

1. **Operator flow:** Skill -> CLI -> deployment/backend -> verification. This is the primary control path.
2. **Runtime flow:** OpenClaw host -> backend API -> provider/storage -> response. The skill is not in this path after deployment.
3. **Handoff flow:** Backend CLI export -> redacted bundle -> frontend CLI import -> local secret rehydration.
4. **Docs flow:** Docs explain commands and topologies, but never act as the source of truth for config formats.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-1k users or a handful of personal deployments | Single backend service, local LanceDB path, in-process background tasks, Docker-first deployment |
| 1k-100k users or many concurrent workspaces | Split indexing/rebuild into a worker process, add job queue, move reverse proxy/auth caching in front of API, strengthen observability |
| 100k+ users or multi-tenant platform usage | Separate query API from ingest workers, use remote/object-backed storage strategy, formal secret manager, more explicit tenancy isolation |

### Scaling Priorities

1. **First bottleneck:** Embedding and reindex latency. Fix with background jobs before splitting the entire backend.
2. **Second bottleneck:** Local disk and single-process write contention around the vector store. Fix with clearer write ownership and worker separation.

## Anti-Patterns

### Anti-Pattern 1: Skill as Runtime

**What people do:** Put deployment logic, config mutation, and long-lived service behavior directly into `SKILL.md` or large shell snippets.
**Why it's wrong:** You cannot test it well, version it cleanly, or reuse it outside OpenClaw.
**Do this instead:** Keep the skill small and route all actions through a real CLI and backend package.

### Anti-Pattern 2: Per-Layer Config Drift

**What people do:** Skill examples, CLI flags, backend env vars, and docs all define slightly different names or shapes.
**Why it's wrong:** Split-machine setup breaks first because export/import contracts no longer match runtime expectations.
**Do this instead:** Define config and bundle schemas once in `packages/shared/` and generate examples from that source.

### Anti-Pattern 3: Secret Leakage Through Bundles

**What people do:** Export whatever the backend currently uses, including keys, tokens, or internal addresses.
**Why it's wrong:** The bundle becomes the security boundary failure that blocks open-sourcing and safe sharing.
**Do this instead:** Export only public connection metadata and require local secret entry or local OAuth login on the receiving machine.

### Anti-Pattern 4: Frontend Directly Touches Storage or Providers

**What people do:** Let the OpenClaw host talk to LanceDB files or embedding providers directly.
**Why it's wrong:** It destroys the backend boundary, complicates auth, and makes split-machine support fragile.
**Do this instead:** Keep provider calls and storage access owned by the backend service.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Embedding provider API | Backend outbound HTTP client via provider adapter | Provider credentials stay backend-local unless frontend auth to backend separately requires user secrets |
| OAuth/OIDC provider | CLI login flow plus backend-side token verification/introspection | Frontend machine should acquire its own token locally; never import refresh tokens in the bundle |
| Container runtime | Deployment adapter | Docker Compose is the default cross-platform path because it models services, networks, volumes, configs, and secrets cleanly |
| Linux service manager | Deployment adapter | `systemd` is Linux-specific and should be optional, not the only path |
| Secret store | CLI/config abstraction | Prefer OS-provided secure storage or protected local files outside version control |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Skill <-> CLI | Subprocess invocation with stable command flags and machine-readable output | This is the most important seam to keep stable |
| CLI <-> Shared contracts | In-process package import | Shared schemas are the source of truth |
| CLI <-> Deployment layer | Adapter interface | Platform-specific logic stays here |
| CLI <-> Backend | Local health probes and admin commands | The CLI should verify the deployed runtime, not reimplement it |
| Frontend host <-> Backend host | HTTPS with imported bundle plus local auth material | Supports both same-machine and split-machine paths |
| Docs <-> Everything else | References only | Docs explain behavior; they do not define contracts |

## Suggested Build Order

1. **Shared contracts first** - define config schema, connection bundle schema, API request/response models, and profile directory layout.
2. **Backend bootstrap second** - implement config loading, auth middleware, health endpoint, and storage/provider abstractions.
3. **Search/embed runtime third** - add the actual memory operations behind the stable backend contract.
4. **Deployment adapters fourth** - Docker first for all platforms, then Linux `systemd` support as a second adapter.
5. **CLI fifth** - wire `init/config/auth/backend deploy/export/frontend import/check` onto shared contracts and deployment adapters.
6. **Skill sixth** - keep it lean by calling the CLI only after the CLI contract is real and stable.
7. **Docs and runbooks last, then iterate** - finalize same-machine, split-machine, and security guides once command/output shapes stop moving.

**Why this order matters:** if the skill is built before the CLI and shared schemas, logic will be duplicated in prose and shell snippets. If split-machine docs are written before the bundle schema exists, the most security-sensitive flow will drift immediately.

## Sources

- Local project context: `/Users/zykj/gitlab/transcendence-memory/.planning/PROJECT.md`
- Local precedent: `/Users/zykj/gitlab/skills-hub/skills/rag-everything-enhancer/SKILL.md`
- Local precedent: `/Users/zykj/gitlab/skills-hub/skills/rag-everything-enhancer/references/ARCHITECTURE.md`
- Local precedent: `/Users/zykj/gitlab/skills-hub/skills/rag-everything-enhancer/references/DATAFLOW.md`
- Local packaging guidance: `/Users/zykj/.codex/skills/.system/skill-creator/SKILL.md`
- Docker Docs, "How Compose works": https://docs.docker.com/compose/intro/compose-application-model/
- The Twelve-Factor App, "III. Config": https://12factor.net/config
- LanceDB docs via Context7 and official docs describing local filesystem and remote connection modes: `/lancedb/lancedb`, https://www.lancedb.com/docs/
- systemd docs on `Environment=` / `EnvironmentFile=` and why environment variables are poor secret transport: https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html

---
*Architecture research for: OpenClaw-compatible memory deployment skill plus backend runtime*
*Researched: 2026-03-23*
