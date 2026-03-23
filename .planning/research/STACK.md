# Stack Research

**Domain:** OpenClaw-compatible memory deployment platform (lean skill package + backend service + deployment automation + auth/config CLI)
**Researched:** 2026-03-23
**Confidence:** MEDIUM

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| Python | 3.13.x baseline, test on 3.14.x | One language for backend, CLI, deployment scripts, and skill-side helpers | This keeps the repo operationally simple and matches the strongest open-source AI/backend tooling ecosystem. Python 3.14 is the newest feature line, but 3.13 is the safer baseline for a greenfield self-hosted project that depends on a mixed runtime stack. | MEDIUM |
| uv | 0.10.12 | Package manager, lockfile, workspace manager, tool runner | `uv` is the 2026 default for Python monorepos that want reproducible installs without Poetry/pip-tools sprawl. Official docs show workspaces, lockfiles, tool management, and broad platform support. | HIGH |
| uv workspaces | built into `uv` | Monorepo structure for shared packages | Use one repo with workspace members such as `packages/core`, `packages/backend`, `packages/cli`, and `skill/`. This is the cleanest way to share typed config models, auth code, and connection-bundle schemas without publishing internal wheels. | HIGH |
| FastAPI | 0.135.1 | HTTP API for memory, auth, health, and deployment endpoints | FastAPI remains the standard Python API framework for AI-adjacent backends: async, OpenAPI-native, typed, and explicitly supports API-key and OAuth/OpenID-style security primitives. | HIGH |
| Uvicorn | 0.41.0 | ASGI server for the backend | It is the default production/development server around FastAPI, supports Python 3.14, and keeps the runtime lean. | HIGH |
| PostgreSQL | 18.3 / 18.x | Primary system of record | For this project, Postgres is a better default than a dedicated vector DB because it gives you relational state, JSONB, transactions, full-text search, backups, and mature self-hosting in one service. PostgreSQL 18 is current and adds OAuth authentication support at the database layer. | HIGH |
| pgvector | 0.8.2 | Vector similarity inside Postgres | This is the right default for v1 because vectors and metadata stay in the same database. The current release supports Postgres 13+, ships PG18 install paths, and supports HNSW/IVFFlat-style indexing. | HIGH |
| Docker Compose | Compose v2 plugin / current Docker Desktop | Main deployment path across macOS, Windows, Linux | Docker docs explicitly recommend Docker Desktop for macOS/Windows/Linux, and the Compose plugin for Linux. This is the standard self-hosted path for small open-source services in 2026. | HIGH |
| Caddy | 2.10.x | Reverse proxy, TLS termination, public entrypoint | Caddy is the best fit for a small open-source deployment product: automatic HTTPS, simple config, cross-platform binaries, and no runtime dependencies. It is simpler than Nginx and less label-centric than Traefik. | MEDIUM |
| systemd | distro-current | Native Linux service management path | `systemd` is the standard native Linux supervisor. Use it only for the Linux host install path, with generated unit templates and env files, not as the primary cross-platform abstraction. | HIGH |
| TOML config | stdlib `tomllib` + generated files | Human-editable non-secret config format | TOML aligns with Python tooling, is easy for users to edit, and fits well for provider profiles, model defaults, base URLs, backend URLs, and auth-mode flags. | MEDIUM |

### Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| SQLAlchemy | 2.0.48 | ORM and SQL layer | Use for backend persistence. It is the stable default for Python services that need explicit schema control and first-class Postgres support. | HIGH |
| Alembic | 1.18.4 | Database migrations | Use for all schema changes. It stays aligned with SQLAlchemy and now supports TOML-first configuration cleanly. | HIGH |
| Pydantic | 2.12.5 | Request/response/config models | Use everywhere typed data crosses boundaries: API models, CLI config, connection bundles, provider profiles. Do not write new code against `pydantic.v1`. | HIGH |
| pydantic-settings | 2.13.1 | Env-file and settings loading | Use for backend settings and layered config loading from env vars, `.env`, and secret-file references. | HIGH |
| Psycopg | 3.3.3 | PostgreSQL driver | Use `psycopg[binary]` for Docker/dev convenience; use plain `psycopg` with system `libpq` if you want fully distro-native Linux packaging. | HIGH |
| pgvector-python | 0.4.2 | Python integration for pgvector | Use with SQLAlchemy/Psycopg to map vector columns and queries without writing raw adapter glue. | HIGH |
| Typer | 0.24.1 | Cross-platform CLI framework | This is the right CLI framework for `init`, `config`, `provider set`, `auth login/status/logout`, `backend deploy/health`, `frontend connect/check`, and smoke-test commands. It scales cleanly into nested subcommands. | HIGH |
| Authlib | 1.6.9 | OAuth 2.0 / OpenID Connect client/server pieces | Use for backend OAuth validation/integration and for CLI login flows. Official docs cover FastAPI, HTTPX, and OIDC/JOSE components. | HIGH |
| HTTPX | 0.28.1 | Provider HTTP client | Use this instead of hard-coding vendor SDKs as your main abstraction. It works for OpenAI-compatible APIs, custom `base_url`, API-key auth, OAuth bearer tokens, timeouts, retries, and smoke tests. | MEDIUM |
| platformdirs | 4.9.4 | Cross-platform config/cache/state paths | Use in the CLI for correct config and state locations on Windows, macOS, and Linux. | HIGH |
| keyring | 25.7.0 | Secure local secret storage for CLI users | Use only on the operator machine for API keys, refresh tokens, and session secrets. Do not make containerized backend auth depend on keyring. Headless/container backends should use env vars or mounted secret files instead. | HIGH |
| argon2-cffi | 25.1.0 | Hashing stored API-key material | Use to hash backend-managed API keys before persistence. Do not store raw API keys in Postgres. | HIGH |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Ruff 0.15.7 | Linting and formatting | One tool replaces Flake8 + isort + Black sprawl. Use it in CI and pre-commit. |
| Pyright 1.1.408 | Static type checking | Use strict mode in `packages/core`, `packages/backend`, and `packages/cli`. Shared typed models are a major part of this repo's safety story. |
| Pytest 9.0.2 | Unit/integration tests | Use for CLI tests, FastAPI tests, migration tests, and redacted connection-bundle contract tests. |
| GitHub Actions | CI | Standard OSS CI path. Run `uv sync`, Ruff, Pyright, Pytest, Docker image build smoke checks, and compose-based health checks. |

## Installation

```bash
# install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows:
# powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# choose the baseline interpreter
uv python install 3.13
uv python pin 3.13

# runtime dependencies
uv add fastapi "uvicorn[standard]" sqlalchemy alembic pydantic pydantic-settings \
  "psycopg[binary]" pgvector typer authlib httpx platformdirs keyring argon2-cffi

# development dependencies
uv add --dev ruff pyright pytest pytest-asyncio

# lock and sync
uv lock
uv sync
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| PostgreSQL 18 + pgvector 0.8.2 | Qdrant | Choose Qdrant only if vector search is the product bottleneck and you expect vector-only tuning, distributed ANN concerns, or very large dedicated vector workloads to dominate over transactional simplicity. |
| FastAPI 0.135.1 | Litestar | Use Litestar only if the team already has deep internal experience and shared infrastructure around it. For this repo, FastAPI's ecosystem gravity is stronger. |
| Typer 0.24.1 | Click | Use Click only if you need low-level CLI control and do not care about FastAPI-like ergonomics or typed command signatures. |
| Caddy 2.10.x | Traefik | Use Traefik if the deployment target becomes many dynamic Docker services with label-based discovery. For this project, the service graph is small and static. |
| Docker Compose v2 | Kubernetes + Helm | Use Kubernetes only after you actually need multi-node scheduling, autoscaling, or regulated cluster operations. It is the wrong default for this repo's v1 scope. |
| uv 0.10.12 | Poetry | Use Poetry only if your contributor base is already locked into it and you cannot change workflow. Otherwise `uv` is simpler, faster, and now covers the monorepo/workspace story directly. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| LanceDB as the default server-side primary store | It is a reasonable local or embedded store, but it is not the best default for a multi-machine, service-oriented, self-hosted memory backend with auth, remote access, and standard ops expectations. | PostgreSQL 18 + pgvector |
| Chroma or SQLite-based vector stores as the production default | Good for demos, weak as the default operational story for a backend service that needs remote clients, migrations, backups, and concurrent access. | PostgreSQL 18 + pgvector |
| Docker Compose standalone binary | Docker marks it as legacy/backward-compatibility only. | Docker Desktop or the Docker Compose plugin |
| Plaintext API keys or OAuth refresh tokens in config files | This leaks secrets into repo state, shell history, backups, and copied connection bundles. | `keyring` for local CLI secrets; env vars or mounted secret files for servers |
| Bash-only deployment automation | It breaks the Windows story and weakens the promise of one CLI across platforms. | Typer-based CLI as the control plane, with thin `.sh` and `.ps1` wrappers only when needed |
| Vendor SDK lock-in as the main provider abstraction | This makes `provider`, `model`, `base_url`, API-key, and OAuth handling inconsistent across commands and environments. | Typed provider profiles + `httpx` + optional thin adapters |
| Celery/Redis in v1 | Extra moving parts with no evidence yet that deployment or smoke-test workflows need a distributed job system. | In-process tasks first; add a queue only when ingestion/retry volume proves it necessary |
| Kubernetes as the first deployment target | Too much operational surface area for a Docker-first, single-host or split-host open-source project. | Docker Compose first, Linux `systemd` second |

## Stack Patterns by Variant

**If the user is on macOS or Windows:**
- Use Docker Desktop + Compose as the only supported runtime path.
- Run `postgres`, `backend`, and `caddy` as containers.
- Keep local CLI secrets in `keyring`; never expect desktop users to hand-manage raw token files unless they opt out.

**If the user is on Linux and wants the native path:**
- Install PostgreSQL 18 and `pgvector` from distro/community packages where available, otherwise build `pgvector` against the host Postgres.
- Run the Python backend from a `uv`-managed environment.
- Generate `systemd` units with `EnvironmentFile=`, `Restart=on-failure`, `WorkingDirectory=`, and dedicated state/log directories.
- Keep Caddy native too; do not mix native backend with container-only reverse proxy unless there is a clear ops reason.

**If the user is doing split-machine frontend/backend deployment:**
- Generate a redacted connection bundle in TOML or JSON containing backend URL, auth mode, public provider aliases, default model names, and optional public TLS metadata.
- Never include API keys, refresh tokens, OAuth client secrets, or private network-only values in that bundle.
- Store the bundle schema in a shared Python package used by both backend and CLI.

**If the project must support many model providers and OpenAI-compatible endpoints:**
- Define a typed `ProviderProfile` model with fields such as `provider`, `base_url`, `api_mode`, `auth_mode`, `model`, `embedding_model`, `audience`, and `scopes`.
- Store non-secret provider config in TOML.
- Store secrets separately: CLI in `keyring`, backend in env vars or mounted secret files referenced by `pydantic-settings`.
- Normalize requests through `httpx`; only introduce vendor-specific SDKs behind adapters when a provider truly needs them.

**If the OpenClaw skill package is meant to stay lean:**
- Keep `SKILL.md` short and move all real execution into shared Python CLI entrypoints.
- Put only thin launcher scripts and references in the skill directory.
- Do not duplicate business logic inside the skill package.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| Python 3.13.x | FastAPI 0.135.1, Uvicorn 0.41.0, SQLAlchemy 2.0.48, Typer 0.24.1 | Recommended production baseline. Test 3.14 in CI, but do not require it for contributors on day one. |
| FastAPI 0.135.1 | Pydantic 2.x, Uvicorn 0.41.x | FastAPI's current package metadata requires Python 3.10+ and Pydantic 2. Do not build new code on `pydantic.v1`. |
| SQLAlchemy 2.0.48 | Alembic 1.18.4, Psycopg 3.3.3 | Standard relational stack for Postgres-backed Python services. |
| PostgreSQL 18.x | pgvector 0.8.2, pgvector-python 0.4.2 | Current `pgvector` docs explicitly show PG18 install/build paths. |
| Docker Compose v2 | Docker Desktop current or Docker Engine + Compose plugin | Do not document the standalone Compose binary as the default. |
| keyring 25.7.0 | `platformdirs` 4.9.4 on the CLI side | Fine for local user secrets; not a dependable container runtime secret backend. |

## Prescriptive Recommendation

Build this as a Python monorepo managed by `uv`, with a shared core package, a FastAPI backend, and a Typer CLI. Use PostgreSQL 18 plus `pgvector` as the single database. Make Docker Compose the default deployment path on all platforms, and offer Linux `systemd` units as a native opt-in path. Put Caddy in front when the service is exposed over HTTPS.

For configuration, separate non-secrets from secrets on purpose. Store provider names, model names, base URLs, backend URLs, auth modes, and feature flags in TOML. Store API keys and OAuth refresh/access tokens in `keyring` on the CLI machine, and in env vars or mounted secret files on the server. Export only redacted connection bundles between machines.

For the OpenClaw skill package, keep the package thin. The skill should call into the same Python CLI/backend codepaths the project uses everywhere else. Do not let the skill become a second backend implementation.

## Sources

- Context7 `/astral-sh/uv` - verified workspaces, lockfiles, tool management, and project-management guidance
- Context7 `/fastapi/fastapi` - verified FastAPI security primitives, lifespan guidance, and production positioning
- Context7 `/fastapi/typer` - verified nested subcommands and CLI scaling patterns
- https://pypi.org/project/uv/ - current version `0.10.12`, installers, and platform artifacts
- https://pypi.org/project/fastapi/ - current version `0.135.1`, Python support, Pydantic 2 requirement, `fastapi[standard]`
- https://pypi.org/project/uvicorn/ - current version `0.41.0`, Python support
- https://www.postgresql.org/docs/18/release.html - PostgreSQL 18 current release line
- https://www.postgresql.org/docs/18/release-18.html - PostgreSQL 18 features, including OAuth authentication support
- https://github.com/pgvector/pgvector - current `pgvector` install/build guidance, PG18 compatibility, vector indexing support
- https://pypi.org/project/pgvector/ - current `pgvector-python` version `0.4.2`
- https://pypi.org/project/SQLAlchemy/ - current version `2.0.48`
- https://alembic.sqlalchemy.org/en/latest/changelog.html - current Alembic version `1.18.4`
- https://pypi.org/project/pydantic/ - current Pydantic 2 release line
- https://pypi.org/project/pydantic-settings/ - current version `2.13.1`
- https://pypi.org/project/psycopg/ - current Psycopg 3 release line `3.3.3`
- https://docs.authlib.org/en/stable/ - Authlib `1.6.9`, FastAPI/HTTPX/OAuth/OIDC support
- https://pypi.org/project/httpx/ - current HTTPX release line `0.28.1`
- https://pypi.org/project/platformdirs/ - current version `4.9.4`, cross-platform path handling
- https://pypi.org/project/keyring/ - current version `25.7.0`, local secret storage behavior and caveats
- https://pypi.org/project/argon2-cffi/ - current version `25.1.0`
- https://docs.docker.com/compose/install/ - Docker Desktop recommended, Compose plugin on Linux, standalone marked legacy
- https://caddyserver.com/docs/ - Caddy docs, cross-platform/runtime-dependency positioning
- https://github.com/caddyserver/caddy - current stable release line `2.10.2`
- https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html - official `systemd.service` reference for native Linux units
- https://pypi.org/project/ruff/ - current version `0.15.7`
- https://pypi.org/project/pyright/ - current version `1.1.408`
- https://pypi.org/project/pytest/ - current version `9.0.2`

---
*Stack research for: OpenClaw-compatible memory deployment platform*
*Researched: 2026-03-23*
