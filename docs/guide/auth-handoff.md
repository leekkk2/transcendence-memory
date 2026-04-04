# Auth Handoff Guide

## For LLM Agents

Use this guide when the backend has already been deployed and you need to make sure the frontend operator gets the correct auth instructions.

## What the deploy-side operator must tell the frontend
After running:
```bash
transcendence-memory backend export-connection --topology split_machine --output bundle.json
```

the deploy-side operator must hand off:
1. `bundle.json`
2. the auth mode (`api_key` or `oauth`)
3. the required local frontend auth inputs
4. the exact next commands for the frontend operator

## API key mode
The frontend operator should receive instructions equivalent to:
```bash
transcendence-memory frontend import-connection --bundle-file bundle.json
transcendence-memory auth set-api-key --api-key <frontend-local-api-key>
transcendence-memory frontend check
transcendence-memory frontend smoke
```

## OAuth mode
The frontend operator should receive instructions equivalent to:
```bash
transcendence-memory frontend import-connection --bundle-file bundle.json
transcendence-memory auth login --issuer <issuer> --authorize-url <url> --token-url <url> --client-id <id>
transcendence-memory frontend check
transcendence-memory frontend smoke
```

## Safety
- Never put secrets into the bundle.
- Never print refresh tokens in summaries or guides.
- The handoff should tell the frontend what to do, not leak backend-side secrets.
