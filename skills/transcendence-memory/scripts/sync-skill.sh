#!/usr/bin/env bash
# sync-skill.sh — idempotent canonical→installed skill sync (anti-drift)
#
# WHY THIS EXISTS
# ---------------
# The canonical skill source lives in this git repo (the plugin/skill source of
# truth). It gets *installed* / deployed as a bare skill copy under
# ~/.agents/skills/. Those two trees historically drifted into two divergent
# SKILL.md lineages (a fat self-contained one vs a half-finished slimmed one
# that referenced a commands.md that did not exist). This script eliminates that
# class of bug: it one-way mirrors CANONICAL → INSTALLED so the deployed copy is
# always byte-identical to the reviewed source, including the executable bit on
# scripts. Run it after editing the canonical skill; never edit the installed
# copy by hand.
#
# Direction is intentionally one-way (canonical is authoritative). It does NOT
# touch the plugin/repo-root hooks/ dir — those are a separate plugin-only
# concern and are deliberately absent from bare skill installs.
#
# Usage:
#   ./sync-skill.sh            # sync both transcendence-memory + tm alias
#   ./sync-skill.sh --dry-run  # show what would change, copy nothing
#
# Idempotent: re-running with no canonical changes produces no diffs and exits 0.
set -euo pipefail

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

# CANONICAL_SKILLS = the skills/ dir this script lives under, two levels up.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"           # .../skills/transcendence-memory/scripts
CANONICAL_SKILLS="$(cd "$SCRIPT_DIR/../.." && pwd)"                  # .../skills
INSTALLED_SKILLS="${INSTALLED_SKILLS:-$HOME/.agents/skills}"        # deployed bare-skill root

# Skill dirs to mirror (canonical name + short alias). Alias is optional.
SKILL_DIRS=(transcendence-memory tm)

# rsync flags: archive (preserve mode incl. +x), delete extraneous installed
# files so a removed canonical file does not linger, exclude VCS noise.
RSYNC_FLAGS=(-a --delete --exclude='.git' --exclude='.DS_Store')
[[ $DRY_RUN -eq 1 ]] && RSYNC_FLAGS+=(--dry-run -v)

sync_one() {
  local name="$1"
  local src="$CANONICAL_SKILLS/$name"
  local dst="$INSTALLED_SKILLS/$name"
  if [[ ! -d "$src" ]]; then
    echo "skip: canonical '$name' not found ($src)"
    return 0
  fi
  if [[ ! -d "$dst" ]]; then
    echo "note: installed '$name' did not exist; creating ($dst)"
    [[ $DRY_RUN -eq 0 ]] && mkdir -p "$dst"
  fi
  echo "sync: $src/  ->  $dst/"
  # Trailing slash on src: copy contents into dst (not src dir itself).
  rsync "${RSYNC_FLAGS[@]}" "$src/" "$dst/"
  # Belt-and-suspenders: ensure shell scripts stay executable post-copy.
  if [[ $DRY_RUN -eq 0 && -d "$dst/scripts" ]]; then
    chmod +x "$dst"/scripts/*.sh 2>/dev/null || true
  fi
}

for d in "${SKILL_DIRS[@]}"; do
  sync_one "$d"
done

if [[ $DRY_RUN -eq 1 ]]; then
  echo "(dry-run) no files written."
else
  echo "sync complete: canonical -> installed (transcendence-memory + tm)."
fi
