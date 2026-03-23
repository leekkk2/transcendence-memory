# Feature Research

**Domain:** Open-source memory deployment for OpenClaw (skill + backend + frontend connection)
**Researched:** 2026-03-23
**Confidence:** MEDIUM

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Guided bootstrap and environment detection | OpenMemory and OpenClaw both lead with quickstart/onboarding flows; users expect prereq checks and config scaffolding instead of reading docs for an hour first. | MEDIUM | Must cover `init/config`, OS detection, Docker presence, writable paths, occupied ports, and machine role (`backend`, `frontend`, `both`). |
| Topology-aware setup for same-machine and split-machine deployments | In this category, users need a clear answer to "am I deploying everything here or connecting to another box?" Ambiguity here causes abandonment. | HIGH | Same-machine should be the shortest happy path. Split-machine should branch into backend-side and frontend-side instructions without mixing responsibilities. |
| Provider, model, and base URL configuration | Mem0 OSS and OpenClaw both expose provider/model/endpoint settings. Users expect the stack to be configurable, not hard-coded to one vendor or one URL. | MEDIUM | Needs `provider set` plus explicit config for model IDs, base URL, and embedding/search defaults. |
| Auth lifecycle for API key and OAuth | OpenClaw users already expect CLI auth flows with visible state. Self-hosted tools also need an explicit answer to "am I authenticated right now?" | HIGH | Needs `auth login/status/logout`; API keys are the predictable default for long-lived hosts, OAuth should be supported where it is valid. |
| Backend deploy, restart, and health checks | OpenMemory and Letta both assume a runnable service with a documented port and a way to verify it is alive. | MEDIUM | Must include `backend deploy` and `backend health`, plus safe re-run behavior, version info, and operator-facing logs. |
| Frontend connect and connection verification | OpenMemory exposes explicit client install/connect and dashboard status. Users expect proof that the frontend is actually attached to the memory backend. | MEDIUM | Needs `frontend connect` and `frontend check`; output should show endpoint, auth mode, last successful probe, and mismatch hints. |
| Secure secret handling at rest and in CLI output | OpenClaw already trains users to expect SecretRefs, redaction, and non-tokenized output. Shipping plaintext secrets will immediately reduce trust. | HIGH | Secrets should stay local via env/file/ref storage. Commands must avoid echoing tokens, and exported artifacts must never contain live credentials. |
| End-to-end smoke tests and diagnostics | Users do not care that a process is "running" if search and embedding still fail. A fast functional check is expected. | MEDIUM | `search/embed` smoke tests should verify auth, embedding, storage, and retrieval end to end, not just ping a port. |
| Chinese-first bilingual docs and operator runbooks | For this target audience, docs are part of the product surface. Missing Chinese guidance materially lowers install success. | MEDIUM | README, topology playbooks, and troubleshooting should be mirrored in zh-CN/en, with copy-pasteable commands and AI-readable structure. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Redacted connection bundle export/import | Removes the most failure-prone part of split-machine setup: manual copy/paste of host, port, provider, and auth metadata while trying not to leak secrets. | HIGH | `backend export-connection` should emit only non-sensitive connection metadata plus secret placeholders; `frontend import-connection` should prompt for local secret resolution on the receiving machine. |
| OpenClaw-native orchestration across backend and frontend roles | Most adjacent tools stop at backend docs or SDK examples. A skill that coordinates both machines is materially more useful to OpenClaw users. | HIGH | Keep `SKILL.md` slim and push logic into `scripts/`, `references/`, and `assets/` so the skill stays maintainable while still guiding real deployment work. |
| Plan -> confirm -> execute -> verify workflow | Safer than opaque install scripts. It gives operators a preview of ports, paths, auth choices, and mutations before anything changes. | MEDIUM | This matters most for remote hosts, split-machine installs, and situations where the AI is acting with partial local context. |
| Recovery-first CLI output | Many OSS tools stop at raw logs. Stronger product behavior is to emit the next exact command or remediation step with redacted diagnostics. | MEDIUM | Errors should say what failed, why it likely failed, and what to run next. This reduces support burden more than adding more flags. |
| AI-consumable bilingual references and topology playbooks | The same docs can guide a human operator on one machine and an AI assistant on the other machine. That is unusually valuable in this niche. | MEDIUM | Structure bundle metadata and docs so another agent can continue setup with minimal interpretation. |
| Secure handoff UX by design | Trust becomes a competitive advantage when remote setup is involved. Making unsafe copy/paste harder than the safe flow is meaningful differentiation. | MEDIUM | Favor non-tokenized URLs, explicit secret prompts, and redacted summaries over "just print everything and hope the operator is careful." |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Built-in web admin console in v1 | Operators often ask for a dashboard because it feels easier than CLI. | It duplicates work across auth, status, config editing, and docs while expanding the security surface and delaying the core deployment path. | Keep v1 CLI-first with strong status output, health checks, and bilingual runbooks. Add a read-only status UI later only if usage proves it is needed. |
| Automatic cross-machine secret sync | It sounds convenient to "just move everything over" during split-machine setup. | This is the highest-risk leak path and is hard to make safe across macOS, Linux, and Windows. | Export a redacted bundle and require secrets to be entered or resolved locally on the receiving machine. |
| Embedding the backend runtime inside the skill package | Users may ask for "one install" simplicity. | It collapses boundaries, makes upgrades harder, and violates the stated design that the skill orchestrates rather than becomes the backend. | Keep the backend as a separate service that the skill deploys, configures, and validates. |
| Automatic migration/import of old private memory data | It reduces initial friction for internal users moving from a private system. | It bakes sensitive legacy assumptions into the open-source product and turns v1 into a data-migration project. | Ship migration guidance and manual import patterns later, but keep v1 deployment-focused. |
| Multi-node, HA, or Kubernetes in v1 | Teams equate these with "production readiness." | It explodes the ops surface before the single-node and two-machine paths are proven. | Docker-first single-node plus documented backup, restore, and reverse-proxy guidance is the right early scope. |
| Expanding auth and provider support beyond `apiKey + OAuth` at launch | Flexibility sounds attractive, especially in OSS. | It creates a support matrix the docs and tests cannot realistically cover in v1. | Ship `apiKey + OAuth`, generic `base URL`/model configuration, and only add more auth modes after real demand appears. |
| Unattended network mutation (opening firewall ports, creating tunnels, editing SSH configs) | "One-click remote setup" sounds powerful. | It is brittle across operating systems and easy to make unsafe or surprising. | Show the plan, ask for confirmation, and emit explicit next-step commands for the operator or AI to run. |

## Feature Dependencies

```text
[Guided bootstrap / prereq detection]
    -> [Topology-aware setup]
        -> [Provider / model / base URL configuration]
            -> [Auth lifecycle]
                -> [Secure secret handling]

[Topology-aware setup]
    -> [Backend deploy + health]
        -> [Redacted connection bundle export]
            -> [Frontend import / connect / check]
                -> [search/embed smoke test]

[Chinese-first bilingual docs]
    -> [Guided bootstrap / prereq detection]
    -> [Topology-aware setup]
    -> [Recovery-first CLI output]

[Plan -> confirm -> execute -> verify]
    -> [Backend deploy + health]
    -> [Frontend import / connect / check]

[Automatic cross-machine secret sync]
    --conflicts--> [Redacted connection bundle export]
```

### Dependency Notes

- **Guided bootstrap requires topology-aware setup:** the installer cannot safely generate the right commands until it knows whether the current machine is the backend host, frontend host, or both.
- **Provider/model config requires auth lifecycle:** provider and endpoint settings are only actionable once the system knows how credentials will be acquired, stored, refreshed, and checked.
- **Auth lifecycle requires secure secret handling:** `auth login/status/logout` is not credible if credentials are still echoed into logs, config dumps, or exported bundles.
- **Backend deploy must happen before frontend connect/check:** the frontend cannot verify anything meaningful until the backend is reachable and healthy.
- **Redacted connection bundle enhances split-machine topology:** it is the cleanest way to move non-sensitive connection metadata from backend host to frontend host without recreating configuration manually.
- **Smoke tests depend on both backend health and frontend connection:** they should verify the real memory path, not just individual components in isolation.
- **Bilingual docs enhance the entire installation surface:** in this project, documentation quality directly affects install success, especially when the backend and frontend are configured on different machines by different operators or agents.
- **Automatic cross-machine secret sync conflicts with the redacted bundle model:** the whole point of the bundle is to move only non-sensitive connection information and keep secrets local.

## MVP Definition

### Launch With (v1)

Minimum viable product for this project is still fairly opinionated because the core value depends on secure deployment, not just a working backend.

- [ ] Guided `init/config` with prereq checks and topology selection — without this, the setup path is too ambiguous for same-machine vs split-machine users.
- [ ] Provider/model/base URL config plus `auth login/status/logout` for `apiKey + OAuth` — this is the minimum viable control plane.
- [ ] `backend deploy/health` — users need a supported way to stand up and validate the backend service.
- [ ] `frontend connect/check` — connection success must be explicitly verifiable from the frontend side.
- [ ] Secure secret handling with local storage conventions and redacted CLI output — this is a trust requirement, not polish.
- [ ] `backend export-connection` and `frontend import-connection` using a redacted bundle — split-machine support is part of the project definition, so this cannot slip past v1.
- [ ] `search/embed` smoke test — must prove the actual memory path works.
- [ ] Chinese-first bilingual README and topology troubleshooting docs — the product is incomplete without them for the target users.

### Add After Validation (v1.x)

- [ ] Redacted diagnostics bundle generation — add once real users start needing easier issue reporting.
- [ ] Reverse-proxy / HTTPS helper templates for remote deployments — useful after the baseline split-machine flow is proven.
- [ ] Optional read-only status UI or TUI — only if CLI output is still insufficient for operators.

### Future Consideration (v2+)

- [ ] Backup and restore workflows — valuable once users have real data worth protecting.
- [ ] Multi-user or workspace-aware connection profiles — only after the single-user deployment story is stable.
- [ ] Provider-specific tuning assistants — defer until the generic provider/model/base URL path has usage data behind it.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Guided `init/config` + topology selection | HIGH | MEDIUM | P1 |
| Provider/model/base URL config | HIGH | MEDIUM | P1 |
| `auth login/status/logout` for `apiKey + OAuth` | HIGH | HIGH | P1 |
| `backend deploy/health` | HIGH | MEDIUM | P1 |
| `frontend connect/check` | HIGH | MEDIUM | P1 |
| Redacted connection bundle export/import | HIGH | HIGH | P1 |
| Secure secret handling + redacted output | HIGH | HIGH | P1 |
| `search/embed` smoke test | HIGH | MEDIUM | P1 |
| Chinese-first bilingual docs | HIGH | MEDIUM | P1 |
| Redacted diagnostics bundle | MEDIUM | MEDIUM | P2 |
| Reverse-proxy / HTTPS helper templates | MEDIUM | MEDIUM | P2 |
| Read-only status UI / TUI | MEDIUM | MEDIUM | P2 |
| Multi-user connection profiles | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | OpenMemory | Letta | Our Approach |
|---------|------------|-------|--------------|
| Fast local install | One-command hosted install and a Docker/local quickstart for self-hosting. | Docker-first self-hosting with explicit local server docs. | Use a role-aware OpenClaw skill to drive install for `backend`, `frontend`, or `both` instead of leaving the operator to interpret generic server docs. |
| Local vs remote connection model | Strong local install/client-connect story; split-machine handoff is less productized. | Explicit local and remote ADE connection model; remote requires HTTPS. | Treat same-machine and split-machine as first-class branches, with different commands and docs for each side. |
| Secret handling | Mostly env-var and `.env` based setup. | Env files plus optional password protection for remote servers. | Local secret storage, redacted exports, non-tokenized output, and explicit local secret prompts on import. |
| Verification surface | Dashboard connection status and API/UI visibility after setup. | ADE or REST connectivity verifies the server is reachable. | CLI-native `backend health`, `frontend check`, and end-to-end `search/embed` smoke tests with remediation hints. |
| Agent-native packaging | Installs into supported clients, but not OpenClaw-native packaging. | Server/SDK oriented, not OpenClaw skill-first. | Ship an OpenClaw-native skill package plus backend project so installation, connection, and troubleshooting fit the host ecosystem. |

## Sources

- Internal project context: `transcendence-memory/.planning/PROJECT.md` (HIGH confidence for scope, topology requirements, redacted bundle, bilingual docs, and security boundaries).
- OpenMemory Quickstart: https://docs.mem0.ai/openmemory/quickstart (HIGH confidence for quickstart expectations, client connect/install, and connection-status UX).
- Mem0 OSS Configuration: https://docs.mem0.ai/open-source/configuration (HIGH confidence for provider/model/base URL and env-based secret expectations).
- Letta self-hosting: https://docs.letta.com/guides/docker (HIGH confidence for Docker-first deployment, env-file patterns, and password protection on self-hosted servers).
- Letta local/remote connection guidance: https://docs.letta.com/guides/ade/setup (HIGH confidence for local-vs-remote topology expectations and HTTPS requirements for remote connections).
- OpenClaw memory CLI: https://docs.openclaw.ai/cli/memory (HIGH confidence for status/search/index command expectations in the host ecosystem).
- OpenClaw auth and onboarding: https://docs.openclaw.ai/gateway/authentication, https://docs.openclaw.ai/concepts/oauth, https://docs.openclaw.ai/start/wizard, https://docs.openclaw.ai/start/onboarding (HIGH confidence for `apiKey + OAuth`, login/status-style UX, and local-vs-remote setup expectations).
- OpenClaw secrets and safe output: https://docs.openclaw.ai/gateway/secrets, https://docs.openclaw.ai/cli/dashboard, https://docs.openclaw.ai/cli/configure (HIGH confidence for SecretRef behavior, redacted output, and safe configuration patterns).
- OpenClaw skill packaging: https://docs.openclaw.ai/tools/creating-skills (HIGH confidence for `SKILL.md`-first skill structure expectations).

---
*Feature research for: Open-source memory deployment for OpenClaw*
*Researched: 2026-03-23*
