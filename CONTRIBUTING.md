# Contributing

Thanks for your interest in contributing to `transcendence-memory` (the Claude Code skill).

## Reporting Issues

Use [GitHub Issues](https://github.com/leekkk2/transcendence-memory/issues) with:
- What you tried
- What you expected
- What happened instead
- Skill version (see `.claude-plugin/plugin.json`)

## Pull Requests

1. Fork the repo and create a feature branch.
2. Keep changes scoped — SKILL.md, references/, and hooks/ are the typical surfaces.
3. Submit a PR with a clear description.

## Naming Conventions (open-source hygiene)

This is a public open-source repository. **Do not commit vendor-specific business identifiers** — internal scope codes, internal product names, deploy hostnames, device names, sprint codes, etc. Use generic placeholders in docs, scripts, comments, and commit messages:

| Don't write | Use instead |
|---|---|
| Internal scope codes (e.g. private team / personal credential labels) | `personal` / `team` / `shared` |
| Internal product / app names | `your-app` / `example-app` |
| Specific deploy hostnames | `example-host` / `memory.example.com` |
| Specific device names | `device-x` / `host-y` |
| Internal sprint codes (e.g. `XX-NNN`) | drop them or use generic `cleanup-YYYY-MM` |

### Pre-commit guard

A one-shot guard checks for the most common leakable patterns. Wire it up locally:

```bash
git config core.hooksPath .githooks
# Now every git commit runs scripts/check-no-private-identifiers.sh on staged files
```

You can also run it ad-hoc against the full tree:

```bash
bash scripts/check-no-private-identifiers.sh
```

If you intentionally need one of the flagged words (e.g. a legitimate code example), add a tightly-scoped allow comment and propose the rule update in the PR.

## License

By contributing, you agree that your contributions will be licensed under the MIT License (see `LICENSE`).
