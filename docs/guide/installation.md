# Installation Guide

## For LLM Agents

Use this guide when you need to bootstrap `transcendence-memory` in a brand-new or isolated environment.

### 1. Enter repo root
```bash
cd transcendence-memory
```

### 2. Bootstrap local dev environment
```bash
./scripts/bootstrap_dev.sh
. .venv/bin/activate
```

### 3. Verify the local CLI/test baseline
```bash
python -m pytest -q
```

## Notes
- If you see `ModuleNotFoundError: No module named 'typer'`, do not treat it as a product failure.
- It usually means the project has not yet been installed with editable dev dependencies.
- Re-run `./scripts/bootstrap_dev.sh`.

## Next guide
- Backend deployment: `docs/guide/backend-deployment.md`
- Frontend handoff: `docs/guide/frontend-handoff.md`
