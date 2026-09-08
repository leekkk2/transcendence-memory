# Compatibility and installation

Skill resources live at `skills/transcendence-memory`, not the repository root.
Keep the checkout in a separate directory (for example `~/src/transcendence-memory`).
The installer copies the complete skill and creates agent directory entries.
It does not write AGENTS.md, install hooks, edit hosts, or change global proxies.

```sh
python3 scripts/install.py --agents codex gemini claude
# explicit development/offline CLI source:
python3 scripts/install.py --cli-source /path/to/transcendence-memory-server/cli-package
```

PowerShell: `scripts/install.ps1 -Python python` forwards installer options.
The existing native `tm_cli` engine is installed in a private app runtime;
PowerShell wrappers send UTF-8 JSON arguments through stdin, not command evaluation.
Use `scripts/tm.ps1 doctor`, `scripts/tm-search.ps1 search --json "中文"`, and
`scripts/tm-remember.ps1 "中文正文" --title "标题"` under the installed skill.

Installation records checkout revision, runtime path, entry targets and hashes
in `~/.transcendence-memory/install.json`. Updates require the correct git remote
and a clean checkout, and use `git pull --ff-only`. Dirty/diverged installs stop
without reset. `--allow-dirty` is an explicit development-only escape hatch.
An existing unmanaged/edited skill requires `--replace-existing`; its backup is
retained outside agent-discovery directories. Conflicting agent links are never
silently overwritten. Runtime changes create a fresh environment instead of
modifying the previous one. If a bundled host runtime disappears, rerun the
installer with a working Python; do not hard-code a Codex application directory.

Credentials: Python CLI writes private POSIX config files and protected current-user
NTFS ACLs on Windows. The installer does not rewrite an existing credential file.
Windows junction/ACL/Unicode behavior is covered by the Windows CI suite (execution evidence is recorded per release); real
LICHAO deployment still requires access to that node.

## Protocol

New score/write/capability fields are additive (`contract_version=2026-09-09`).
Older servers keep working; absent receipts cannot be presented as verified writes.
See [search contract](../skills/transcendence-memory/references/search-contract.md).
The optional CLI and server have independent package versions; capabilities,
not equal version numbers or the service name, determine compatibility.

`transport_mode` in `[connection]` accepts auto/direct/proxy. `TM_TRANSPORT_MODE`
overrides config; legacy `TM_NO_PROXY=1` selects direct when the new override is
not set. Proxy mode never switches to direct after a failure. Auto mode keeps
ambient proxy settings and may try one direct route for replay-safe operations.
Write timeouts/5xx are not replayed. TLS verification remains enabled.

Rollback: `python3 scripts/install.py --rollback` restores the previous skill/runtime
manifest, or removes the first managed install. Config files and backups remain.
It refuses to discard edited installed files.
