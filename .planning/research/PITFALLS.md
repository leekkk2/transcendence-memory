# Pitfalls Research

**Domain:** Open-source OpenClaw memory deployment skill plus backend service
**Researched:** 2026-03-23
**Confidence:** MEDIUM

## Critical Pitfalls

### Pitfall 1: "Redacted" connection bundles still leak secrets

**What goes wrong:**
Projects export a connection bundle or example config that still contains API keys, OAuth refresh tokens, private hostnames, internal container names, or transformed secrets embedded in JSON, logs, shell history, or Docker image metadata.

**Why it happens:**
Teams treat redaction as string replacement instead of a strict allowlist schema. They also use environment variables and JSON blobs as the universal transport for secrets, then later reuse those same blobs in docs, CI, or frontend import flows.

**How to avoid:**
- Define the exported connection bundle as a positive allowlist schema from day one. Only include non-sensitive fields such as `public_base_url`, `auth_mode`, `auth_header_name`, `backend_version`, `bundle_schema_version`, and declared capabilities.
- Explicitly forbid API keys, bearer tokens, refresh tokens, cookies, private DNS names, internal IPs, Docker service names, and provider client secrets from any exported bundle, fixture, or example file.
- Keep secrets only in local OS storage, local env files outside version control, or secret managers. For containers, prefer Docker secrets or runtime-mounted secret files over shared env blobs.
- Ban secrets in `Dockerfile ARG` and `ENV`; use build secrets and runtime secret mounts instead.
- Enable GitHub push protection and secret scanning before the first public push, and add custom detectors for bundle file names and internal token formats.
- Add a CI test that generates every example/config/export artifact and fails if any secret-like pattern is present after encoding, masking, or base64 transformation.

**Warning signs:**
- `backend export-connection` outputs a full header value or bearer token.
- Examples contain realistic production-looking domains, API keys, or JWTs.
- Dockerfiles or build scripts reference `ARG ...KEY`, `ARG ...TOKEN`, or `ENV ...SECRET`.
- GitHub Actions stores one large JSON/YAML secret blob instead of individual secret values.
- Logs print the full effective config, auth block, or imported bundle.

**Phase to address:**
Phase 1 - Security and configuration contract

---

### Pitfall 2: Skill and backend responsibilities collapse into one another

**What goes wrong:**
The skill starts acting like the backend runtime, or the backend becomes unmanageable without the skill. Frontend and backend machine roles blur together, split-machine deployment breaks down, and secrets end up on the wrong host.

**Why it happens:**
There is no explicit ownership contract for what the skill is allowed to do versus what the backend must own. Projects keep adding "just one more step" to the skill until it contains service logic, provider calls, storage assumptions, and machine-specific state.

**How to avoid:**
- Lock in a written boundary early:
  - Skill: detect environment, show plan, call backend/CLI commands, write local config, export/import redacted bundles, run verification.
  - Backend: own runtime, provider integrations, auth callbacks, indexing/search APIs, and persistent secret handling.
- Make the backend independently runnable and versioned. The skill should orchestrate it, not be the only path to running it.
- Separate CLI surfaces by role: `backend deploy/health/export-connection`, `frontend connect/check/import-connection`, `auth login/status/logout`.
- Reject role-invalid commands with clear errors instead of guessing.
- Keep same-machine and split-machine diagrams in the docs and ensure every command declares which machine role it is for.

**Warning signs:**
- `SKILL.md` references internal backend source paths or requires repo checkout assumptions.
- Frontend instructions ask the client machine to hold provider secrets for a remote-backend flow.
- Backend can only be started through skill-internal scripts.
- The same flag or config key means different things on frontend and backend machines.
- "Install backend via skill" is documented as if the skill itself provides backend capability.

**Phase to address:**
Phase 1 - Security and ownership contract

---

### Pitfall 3: OAuth behavior drifts across CLI, backend, and providers

**What goes wrong:**
`auth login` works on one machine or one provider but fails elsewhere because redirect URIs, PKCE behavior, token storage, reverse-proxy headers, scope naming, or refresh-token handling differ. Teams then start copying tokens by hand between machines.

**Why it happens:**
Projects begin with a single provider quickstart, then bolt on more providers and split-machine support without defining one internal OAuth contract. Native-app rules and proxy hardening get deferred until after implementation.

**How to avoid:**
- Choose a single v1 OAuth pattern per role:
  - Native/CLI flows: external browser + authorization code + PKCE + loopback IP redirect.
  - Backend/server flows: server-side confidential client only if truly needed.
- Register exact redirect URIs per provider and keep them in code/config, not only in docs.
- Never put refresh tokens into exported bundles or frontend-imported artifacts.
- Store token metadata in a structured local store and clearly separate access token, refresh token, expiry, and granted scopes.
- Add provider adapters behind one normalized auth interface so provider-specific quirks do not leak into user-facing docs.
- When running behind a reverse proxy, sanitize forwarded headers and protect the proxy-to-app hop.
- Test `auth login/status/logout` on a fresh machine for each supported provider before calling the auth matrix complete.

**Warning signs:**
- Docs mention `localhost`, code registers `127.0.0.1`, or vice versa.
- PKCE is optional in code or absent from the CLI flow.
- Redirect URIs are copied manually from README into provider dashboards.
- Reverse proxy passes client-controlled `X-Forwarded-*` values through unchanged.
- Refresh tokens appear in logs, bundle exports, or bug reports.
- A second provider requires "special manual steps" not encoded in the CLI contract.

**Phase to address:**
Phase 2 - Auth and topology contract

---

### Pitfall 4: Cross-platform support becomes shell and service-manager sprawl

**What goes wrong:**
The project claims Linux, macOS, and Windows support, but actual automation depends on Bash, GNU utilities, `systemctl`, Unix line endings, Docker Desktop assumptions, or path handling that only works on one platform. Maintenance cost explodes.

**Why it happens:**
Teams interpret "Docker exists everywhere" as "automation is the same everywhere". They mix Bash, zsh, PowerShell, WSL, systemd, and Docker Desktop networking behavior without naming one canonical deployment path.

**How to avoid:**
- Make Docker-first the only canonical v1 path across all three OSes.
- Treat Linux native systemd deployment as a secondary, Linux-only path rather than parity work for every platform.
- Put OS-specific logic in thin wrappers. Keep the real logic in the backend CLI and portable config files.
- Maintain an explicit support matrix with exact meanings:
  - Linux: Docker-first, optional native service path
  - macOS: Docker Desktop path
  - Windows: Docker Desktop plus WSL2 path
- Add smoke tests for PowerShell and POSIX shells where commands are user-facing.
- Enforce LF line endings for shell scripts and avoid POSIX-only commands in cross-platform entrypoints unless behind OS-specific wrappers.
- Pin the minimum Compose/Docker Desktop versions and features you depend on.

**Warning signs:**
- Windows docs start with `source ...` or `chmod +x`.
- Cross-platform scripts use `sed -i`, `systemctl`, `jq`, or GNU-only flags without detection.
- Support relies on `docker0`, host networking, or Linux-only networking assumptions.
- Git Bash users hit path-mount failures or CRLF syntax errors.
- Release testing happens only on one OS even though three are claimed.

**Phase to address:**
Phase 3 - Cross-platform automation baseline

---

### Pitfall 5: Same-machine assumptions leak into split-machine exports

**What goes wrong:**
The backend exports connection info that only works on the backend host: `localhost`, `127.0.0.1`, `host.docker.internal`, Docker service names, bridge IPs, or internal TLS assumptions. Frontend import succeeds locally but fails from the real client machine.

**Why it happens:**
Projects implement same-machine deployment first and later "extend" it by reusing local values in the exported config. They do not separate bind address, advertised address, and public URL.

**How to avoid:**
- Model topology explicitly in config with separate fields for bind/listen address, advertised base URL, public base URL, and machine role.
- Make `backend export-connection` compute a remote-safe bundle from advertised/public values only.
- Refuse to export loopback addresses, RFC1918-only addresses, or Docker-internal names unless the user explicitly opts into a same-machine-only bundle.
- Run split-machine verification from a second network context, not from the backend host itself.
- Use the reverse-proxy/public DNS endpoint as the exported target, not Docker internals.

**Warning signs:**
- Exported bundle contains `localhost`, `127.0.0.1`, `host.docker.internal`, container names, or private LAN addresses by default.
- `frontend check` passes only when run on the backend machine.
- Docs tell users to "replace the server IP later".
- Health checks succeed on the server but fail from a client machine.
- Imported bundle has no explicit topology flag or schema version.

**Phase to address:**
Phase 2 - Auth and topology contract

---

### Pitfall 6: Docs, CLI flags, env files, JSON config, and runtime behavior drift apart

**What goes wrong:**
The README says one thing, `SKILL.md` says another, `.env.example` uses a third name, Compose renders a fourth value, and the backend silently chooses a default. Users think deployment succeeded but runtime is using different settings or insecure fallbacks.

**Why it happens:**
There is no single config schema. Docs, examples, CLI parsing, bundle export/import, and Compose files are maintained by hand and diverge over time. Docker Compose precedence rules make the drift worse.

**How to avoid:**
- Create one canonical config schema and generate from it:
  - CLI help
  - `.env.example`
  - JSON template
  - reference docs
  - bundle schema
- Add `init/config`, `config doctor`, `backend health`, and `frontend check` commands that print effective config with secrets masked.
- In CI, run `docker compose config --environment` and compare the rendered config against documented examples and expected defaults.
- Freeze user-facing config names early for provider, model, base URL, auth header, and workspace locations.
- Add golden tests for example configs and docs snippets so renames fail loudly.

**Warning signs:**
- Users must edit both JSON and `.env` to make one setting stick.
- README uses one env name while code reads another.
- Example config references features or headers that the current backend no longer supports.
- Bug reports say "setting ignored", "still uses default SQLite", or "works only when passed on the command line".
- Docs and examples are not produced from the same schema/source.

**Phase to address:**
Phase 1 - Security and configuration contract

---

### Pitfall 7: Skill packaging and backend version skew are left implicit

**What goes wrong:**
An older skill package tries to orchestrate a newer backend or import a newer connection bundle. The breakage looks like auth, path, or network failure because compatibility was never declared.

**Why it happens:**
Projects version the backend but treat the skill package, bundle schema, and install references as unversioned text. References and scripts drift away from what the shipped backend actually supports.

**How to avoid:**
- Version these contracts independently and document compatibility:
  - skill package version
  - backend API/CLI version
  - connection bundle schema version
- Keep `SKILL.md` minimal and stable. Put operational detail in versioned `references/` and scripts.
- Add package-install tests in a clean workspace that verify every referenced file exists and every documented command is real.
- Make `frontend import-connection` and `backend export-connection` validate schema version and supported capabilities before doing any side effects.
- Include backend version and feature flags in the exported bundle so the skill can make correct decisions.

**Warning signs:**
- `SKILL.md` names commands or flags missing from the current CLI.
- Scripts rely on repo-relative paths outside the skill package.
- Bundle imports have no version check.
- Users must "just use the latest backend tag" because compatibility rules do not exist.
- Docs and code mention deprecated endpoints or aliases long after runtime behavior changed.

**Phase to address:**
Phase 4 - Packaging and compatibility hardening

---

### Pitfall 8: CI/CD and runner trust are designed too late

**What goes wrong:**
The project wires deployment and packaging into broad GitHub Actions secrets, self-hosted runners, or third-party actions before establishing trust boundaries. A compromised action or pull request path exposes provider keys or release credentials.

**Why it happens:**
Teams optimize for convenience and automatic publishing before separating untrusted test paths from trusted release paths.

**How to avoid:**
- Separate public PR test workflows from protected release/deploy workflows.
- Do not expose production secrets to fork/PR paths.
- Prefer GitHub-hosted runners for public-repo automation. If self-hosted runners are necessary, isolate them by repository/environment and keep them ephemeral where possible.
- Pin third-party actions to immutable SHAs and review action dependency changes.
- Scope secrets narrowly by environment and avoid large structured secret blobs.
- Audit all secret access before enabling automation that can publish skills, images, or docs.

**Warning signs:**
- The same workflow runs PR tests and publishes artifacts.
- Self-hosted runners are shared across multiple repos or trust levels.
- Third-party actions are pinned to `@v1` or `@main`.
- Docs tell contributors to reuse deployment tokens locally.
- `secrets: inherit` is used broadly without environment isolation.

**Phase to address:**
Phase 5 - CI/CD and operational verification

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| One JSON "connection bundle" that sometimes carries secrets | Very easy manual handoff | Secret leakage, audit ambiguity, impossible redaction guarantees | Never |
| Supporting native parity across Linux, macOS, and Windows in v1 | Better marketing story | Shell sprawl, test matrix blow-up, slower roadmap | Never |
| Letting the skill call backend internals directly | Faster prototype | Boundary collapse, packaging breakage, split-machine failure | Never |
| Documenting provider-specific OAuth exceptions only in README | Fast first-provider integration | Auth drift, inconsistent bug fixes, poor automation | Only for a throwaway prototype |
| Duplicating config across `.env`, JSON, and CLI defaults | Easier manual debugging | Silent precedence bugs and docs drift | Only temporarily during internal prototyping, with `config doctor` |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| GitHub Actions | Assuming secrets are always available to PR, fork, or Dependabot-triggered workflows | Split trusted and untrusted workflows; use protected environments and narrow secret scope |
| Docker Compose | Assuming `.env` and shell values behave the same everywhere | Use explicit `--env-file`, document precedence, and verify with `docker compose config --environment` |
| Docker Desktop networking | Exporting `host.docker.internal`, bridge assumptions, or host-network behavior as portable config | Export only public/advertised URLs; treat Desktop networking behavior as local-only |
| OAuth providers | Treating redirect URIs and scopes as provider docs trivia instead of versioned config | Store provider registration data in code/config, test exact redirects, require PKCE for native flows |
| Reverse proxies | Trusting inbound `X-Forwarded-*` headers from clients | Terminate TLS at the proxy, sanitize forwarded headers, and protect proxy-to-app communication |
| OpenClaw skill packaging | Referencing files outside the package or relying on current repo layout | Keep the skill self-contained and installation-test every referenced file/path |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Deep smoke tests in interactive deploy commands | `backend deploy` feels hung, provider bills spike, users retry during warmup | Keep deploy, warmup, and smoke tests as distinct steps with explicit progress | Breaks as soon as indexing or provider latency grows |
| Building the entire memory index during first-run setup | First install takes too long, users think deployment failed | Separate service install from initial embed/warmup and show resumable status | Breaks once datasets move beyond trivial size |
| Health endpoints that call providers or full DB scans | Reverse proxy marks service unhealthy, flaky restarts | Use shallow `/health` plus separate readiness/smoke endpoints | Breaks under provider latency or transient network issues |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Exporting bearer tokens or refresh tokens in bundles | Credential replay and account takeover | Allowlist-only bundle schema and artifact secret scanning |
| Putting provider keys in Dockerfile `ARG` or `ENV` | Secret persists in image metadata and layers | Use Docker build/runtime secrets, never `ARG`/`ENV` for long-lived secrets |
| Shipping provider keys to frontend/client hosts for remote-backend flows | Unauthorized model usage and cost leakage | Route provider calls through backend and keep keys backend-local |
| Trusting unsanitized forwarded headers | OAuth and authz bypass through spoofed origin/client info | Sanitize proxy headers and secure proxy-to-app hop |
| Using one structured JSON secret in CI | Redaction failures and hard-to-scope access | Store individual secrets separately and register transformed values when needed |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Commands mutate state without a role/topology preview | Users break the wrong machine or wrong config | Use detect -> plan -> confirm -> execute -> verify flow |
| "Supports Linux/macOS/Windows" without a capability matrix | Users follow invalid instructions for their host | Publish exact support paths and v1 non-goals |
| Reporting success on transport-level HTTP 200 only | Users believe deployment works when backend logic is still failing | Verify semantic success, not just status code |
| Asking users to manually carry secrets between machines | High error rate and secret leakage | Export/import only redacted bundles and keep secrets local |

## "Looks Done But Isn't" Checklist

- [ ] **Connection bundle export/import:** Missing schema version and secret scan on generated artifacts.
- [ ] **OAuth support:** Missing `login/status/logout` verification on a fresh second machine and missing redirect registration checks.
- [ ] **Windows support:** Missing PowerShell, CRLF, and path-mount smoke tests.
- [ ] **Split-machine deployment:** Tested only from the backend host, not from a real frontend machine/network context.
- [ ] **Docs and config:** Missing `config doctor` and generated config reference from one schema.
- [ ] **Release automation:** Missing push protection, protected environments, and pinned action SHAs.
- [ ] **Skill packaging:** Missing clean-install test that proves every referenced script and file exists inside the package.

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Secret leakage in bundle/docs/CI | HIGH | Revoke exposed secrets, invalidate sessions/tokens, purge logs/artifacts, rotate credentials, add scanner regression tests, reissue sanitized examples |
| Boundary collapse between skill and backend | HIGH | Freeze new feature work, write ownership contract, move runtime logic into backend, reduce skill to orchestration surface, add role-based acceptance tests |
| OAuth drift | MEDIUM | Re-register exact redirects, rotate tokens, purge copied tokens from machines, normalize provider adapter behavior, add matrix tests before reopening rollout |
| OS matrix sprawl | HIGH | Cut unsupported paths from v1 scope, re-center on Docker-first path, move shell logic into backend CLI, add explicit capability matrix |
| Split-machine bundle exports local-only addresses | MEDIUM | Patch export logic, invalidate old bundles, add remote-context verification, introduce topology flags and URL validation |
| Docs/config mismatch | MEDIUM | Define one canonical schema, regenerate examples/docs, add config rendering checks, deprecate renamed settings with compatibility warnings |
| Skill/backend version skew | MEDIUM | Introduce bundle/schema versioning, publish compatibility table, add package-install tests, block incompatible imports |
| CI/CD trust model flaw | HIGH | Rotate all automation secrets, disable unsafe workflows, migrate to protected environments, isolate or rebuild runners, pin actions by SHA |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Redacted bundles still leak secrets | Phase 1 - Security and configuration contract | Generated artifacts, examples, and logs pass secret scanning; bundle schema rejects sensitive fields |
| Skill/backend responsibility collapse | Phase 1 - Security and ownership contract | Architecture doc and CLI surface show clear role separation; split-machine tests pass without backend internals in skill |
| OAuth contract drift | Phase 2 - Auth and topology contract | `auth login/status/logout` passes for each provider on a fresh machine; redirect URIs and PKCE behavior are validated |
| Split-machine topology leakage | Phase 2 - Auth and topology contract | Exported bundles use only public/advertised URLs; remote frontend check passes from a second machine/network |
| OS matrix sprawl | Phase 3 - Cross-platform automation baseline | PowerShell and POSIX smoke tests pass on supported platforms; unsupported paths are explicitly documented |
| Docs/config mismatch | Phase 1 - Security and configuration contract | One canonical schema generates docs/examples; `config doctor` matches rendered runtime config |
| Skill/backend version skew | Phase 4 - Packaging and compatibility hardening | Clean-install package tests pass; bundle imports fail fast on incompatible schema/backend versions |
| CI/CD trust model late design | Phase 5 - CI/CD and operational verification | Protected release workflow is isolated from PR paths; actions are SHA-pinned; secret scope audit passes |

## Sources

- [HIGH] Local project context: `/Users/zykj/gitlab/transcendence-memory/.planning/PROJECT.md`
- [MEDIUM] Local packaging/prototype references:
  - `/Users/zykj/gitlab/skills-hub/skills/rag-everything-enhancer/SKILL.md`
  - `/Users/zykj/gitlab/skills-hub/skills/rag-everything-enhancer/references/setup.md`
  - `/Users/zykj/gitlab/skills-hub/skills/rag-everything-enhancer/references/OPERATIONS.md`
  - `/Users/zykj/gitlab/skills-hub/README.md`
- [HIGH] Docker Compose secrets: https://docs.docker.com/compose/how-tos/use-secrets/
- [HIGH] Docker build secret guidance: https://docs.docker.com/reference/build-checks/secrets-used-in-arg-or-env/
- [HIGH] Docker Compose environment precedence: https://docs.docker.com/compose/how-tos/environment-variables/envvars-precedence/
- [HIGH] Docker Compose interpolation and `.env` behavior: https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/
- [HIGH] Docker Compose pre-defined env vars and Windows path conversion: https://docs.docker.com/compose/how-tos/environment-variables/envvars/
- [HIGH] Docker Desktop networking how-tos: https://docs.docker.com/desktop/features/networking/networking-how-tos/
- [HIGH] Docker Desktop Windows install/support constraints: https://docs.docker.com/desktop/setup/install/windows-install/
- [HIGH] Docker Desktop troubleshooting for CRLF/path conversion on Windows: https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/topics/
- [HIGH] Docker host networking limits by platform: https://docs.docker.com/engine/network/drivers/host/
- [HIGH] GitHub Actions secrets reference: https://docs.github.com/en/actions/reference/security/secrets
- [HIGH] GitHub secure use reference: https://docs.github.com/en/enterprise-cloud@latest/actions/reference/security/secure-use
- [HIGH] GitHub push protection: https://docs.github.com/en/code-security/concepts/secret-security/about-push-protection
- [HIGH] GitHub secret types and workflow secret restrictions: https://docs.github.com/en/code-security/reference/secret-security/understanding-github-secret-types
- [HIGH] OAuth 2.0 for Native Apps (RFC 8252): https://datatracker.ietf.org/doc/html/rfc8252
- [HIGH] OAuth 2.0 Security Best Current Practice (RFC 9700): https://datatracker.ietf.org/doc/html/rfc9700
- [MEDIUM] Provider-side key handling guidance: https://help.openai.com/en/articles/5112595-best-practices-for-api
- [MEDIUM] Ecosystem evidence of docs/config drift causing deployment and security issues:
  - https://github.com/langflow-ai/langflow/security
  - https://github.com/langflow-ai/langflow/issues/5340
  - https://github.com/langflow-ai/langflow/issues/3820

---
*Pitfalls research for: OpenClaw memory deployment skill plus backend service*
*Researched: 2026-03-23*
