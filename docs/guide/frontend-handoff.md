# Frontend Handoff Guide

## For LLM Agents

Use this guide after backend deployment is complete.

### Import the redacted bundle
```bash
transcendence-memory frontend import-connection --bundle-file bundle.json
```

### Then complete local auth material
Do not assume the bundle contains secrets.
The frontend machine must still provide its own local auth material.

If auth mode is `api_key`:
```bash
transcendence-memory auth set-api-key --api-key <frontend-local-api-key>
```

If auth mode is `oauth`:
```bash
transcendence-memory auth login --issuer <issuer> --authorize-url <url> --token-url <url> --client-id <id>
```

### Validate frontend readiness
```bash
transcendence-memory frontend check
transcendence-memory frontend smoke
```

## Rules
- The bundle is redacted.
- The bundle must not contain API keys, bearer tokens, or refresh tokens.
- Split-machine export must not use localhost, private IPs, or reserved test-network IPs as frontend targets.
- If `advertised_url` is still local-only, fix it before exporting the bundle.

## Next guide
- Auth handoff: `docs/guide/auth-handoff.md`
