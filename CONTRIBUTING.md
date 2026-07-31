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

| Category | Generic placeholders |
|---|---|
| Credential / tenancy scope labels | `personal` / `team` / `shared` |
| Product / app names | `your-app` / `example-app` |
| Deploy hostnames | `example-host` / `memory.example.com` |
| Device names | `device-x` / `host-y` |
| Sprint / cleanup codes | `cleanup-YYYY-MM` |

### Optional private-identifier pre-commit guard

If your local fork tracks identifiers that should never leave your machine
(internal hostnames, vendor codes, project codenames, etc.), you can opt into
the pre-commit guard by setting either:

```bash
# Tier 1: unambiguous compound names (literal extended-regex, low FP risk)
git config --local hooks.privateIdentifiersTier1 '<your-extended-regex>'

# Tier 2: short bare names — supply your own \b...\b word boundaries
git config --local hooks.privateIdentifiersTier2 '<your-extended-regex>'
```

Or by pointing it at an external file:

```bash
git config --local hooks.privateIdentifiersFile ~/.config/tm-guard/words.txt
# file format: one assignment per line:
#   tier1=<extended-regex>
#   tier2=<extended-regex>
```

Then enable the hooks path:

```bash
git config core.hooksPath .githooks
```

The hook is a **silent no-op** if neither tier is configured — open-source
contributors do not need to set anything. You can also run the script ad-hoc:

```bash
bash scripts/check-no-private-identifiers.sh
```

The dictionary lives only in your local `.git/config` (or an external file
outside the repo). The script itself contains no business-specific terms.

## License

By contributing, you agree that your contributions will be licensed under the MIT License (see `LICENSE`).

