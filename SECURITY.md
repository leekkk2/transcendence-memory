# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.2.x   | Yes       |
| < 0.2   | No        |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly:

1. **Do NOT open a public issue.**
2. Email the maintainer or use [GitHub Security Advisories](https://github.com/leekkk2/transcendence-memory/security/advisories/new) to report privately.
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We aim to acknowledge reports within 48 hours and provide a fix within 7 days for critical issues.

## Scope

This skill is a **stateless client** — it contains no server code, no database, and no user data storage. Security concerns for this skill include:

- **Credential handling**: API keys are stored locally in `~/.transcendence-memory/config.toml` with `600` permissions (owner-only read/write)
- **Hook execution**: Lifecycle hooks execute only well-defined, auditable shell scripts bundled in this repository
- **Data transmission**: All API calls use HTTPS; credentials are never passed via command-line arguments
- **Input handling**: User inputs are length-limited and sanitized before use in API calls
- **No dynamic code execution**: No `eval()`, `exec()`, `vm.runInNewContext()`, or equivalent mechanisms

## Best Practices for Users

- Always use HTTPS endpoints for your backend server
- Keep `~/.transcendence-memory/config.toml` with restrictive permissions (`chmod 600`)
- Do not commit `.env` files or config files containing API keys
- Review hook scripts before enabling automatic memory (`/tm auto on`)
- Keep the skill updated to the latest version

## Dependencies

This skill has **zero external dependencies**. All scripts use only:
- Bash (POSIX-compatible shell)
- Python 3 standard library (`json`, `urllib`, `pathlib`, `sys`)
- `curl` (system utility)

No packages are installed, no `node_modules` or `pip install` required.
