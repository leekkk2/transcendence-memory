#!/usr/bin/env python3
"""
Multi-platform hook adapter for transcendence-memory.

Normalizes hook input from different AI coding CLIs into a unified format,
then dispatches to the appropriate action. Follows the pattern established
by skill-usage-governor.

Supported platforms:
  - Claude Code   (hook_event_name, tool_name, tool_input)
  - Cursor        (CURSOR_PLUGIN_ROOT env, same JSON schema)
  - Gemini CLI    (AfterTool, matcher, tool_input)
  - Windsurf      (post-tool-use, tool, arguments)
  - Vibe CLI      (post-tool-call, tool, input)
  - Cline/Roo     (JSON stdin/stdout protocol)
  - Copilot CLI   (COPILOT_CLI env)
  - Augment Code  (Claude Code compatible)

Usage:
  echo '<hook-json>' | python3 adapter.py <platform> <action>

  platform: claude | cursor | gemini | windsurf | vibe | cline | copilot | augment | auto
  action:   post-commit | session-start
"""

import json
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = Path.home() / ".transcendence-memory"
CONFIG_FILE = CONFIG_DIR / "config.toml"
AUTO_MARKER = CONFIG_DIR / "auto-memory.enabled"


def read_config():
    """Read endpoint, api_key, container from config.toml."""
    if not CONFIG_FILE.exists():
        return None, None, None
    text = CONFIG_FILE.read_text()
    def extract(key):
        for line in text.splitlines():
            if line.strip().startswith(key):
                return line.split('"')[1] if '"' in line else line.split("=", 1)[1].strip()
        return None
    return extract("endpoint"), extract("api_key"), extract("container")


def is_git_commit(tool_input_str):
    """Check if a tool input string contains a git commit-like command."""
    import re
    return bool(re.search(r'git\s+(commit|merge|cherry-pick|rebase)', tool_input_str or ""))


# --- Platform handlers ---

def extract_tool_info_claude(data):
    """Claude Code / Augment Code format."""
    return {
        "event": data.get("hook_event_name", ""),
        "tool": data.get("tool_name", ""),
        "input": data.get("tool_input", {}),
        "input_raw": json.dumps(data.get("tool_input", {})),
    }


def extract_tool_info_gemini(data):
    """Gemini CLI format."""
    return {
        "event": data.get("event", ""),
        "tool": data.get("matcher") or data.get("tool_name", ""),
        "input": data.get("tool_input", {}),
        "input_raw": json.dumps(data.get("tool_input", {})),
    }


def extract_tool_info_windsurf(data):
    """Windsurf / Cascade format."""
    return {
        "event": data.get("event", ""),
        "tool": data.get("tool", ""),
        "input": data.get("arguments", {}),
        "input_raw": json.dumps(data.get("arguments", {})),
    }


def extract_tool_info_vibe(data):
    """Vibe CLI format."""
    return {
        "event": data.get("event", "post-tool-call"),
        "tool": data.get("tool", ""),
        "input": data.get("input", {}),
        "input_raw": json.dumps(data.get("input", {})),
    }


def extract_tool_info_cline(data):
    """Cline / Roo Code format."""
    return {
        "event": data.get("event", ""),
        "tool": data.get("tool_name") or data.get("tool", ""),
        "input": data.get("tool_input") or data.get("arguments", {}),
        "input_raw": json.dumps(data.get("tool_input") or data.get("arguments", {})),
    }


def detect_platform(data):
    """Auto-detect platform from environment and data structure."""
    if os.environ.get("CURSOR_PLUGIN_ROOT"):
        return "cursor"
    if os.environ.get("COPILOT_CLI"):
        return "copilot"
    if "hook_event_name" in data:
        return "claude"
    if "matcher" in data and "event" in data:
        return "gemini"
    if "arguments" in data and "tool" in data:
        return "windsurf"
    if "input" in data and "tool" in data:
        return "vibe"
    return "claude"  # default


EXTRACTORS = {
    "claude": extract_tool_info_claude,
    "cursor": extract_tool_info_claude,  # same schema
    "augment": extract_tool_info_claude,  # compatible
    "copilot": extract_tool_info_claude,  # compatible
    "gemini": extract_tool_info_gemini,
    "windsurf": extract_tool_info_windsurf,
    "vibe": extract_tool_info_vibe,
    "cline": extract_tool_info_cline,
    "roo": extract_tool_info_cline,
}


# --- Actions ---

def action_post_commit(info):
    """Store a commit memory via the API."""
    endpoint, api_key, container = read_config()
    if not all([endpoint, api_key, container]):
        return

    if not AUTO_MARKER.exists():
        return

    # Get commit info
    try:
        commit_msg = subprocess.run(
            ["git", "log", "-1", "--pretty=format:%h %s"],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
        changed = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-status", "-r", "HEAD"],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
    except Exception:
        return

    if not commit_msg:
        return

    short_hash = commit_msg.split()[0] if commit_msg else "unknown"
    files_summary = ", ".join(changed.splitlines()[:10]) if changed else "no files"
    memory_text = f"[commit {short_hash}] {commit_msg} | files: {files_summary}"

    # Truncate to 500 chars
    if len(memory_text) > 500:
        memory_text = memory_text[:497] + "..."

    mem_id = f"commit-{short_hash}"
    payload = {
        "container": container,
        "objects": [{"id": mem_id, "text": memory_text, "tags": ["auto-commit"]}],
        "auto_embed": True,
    }

    try:
        subprocess.run(
            [
                "curl", "-sS", "-X", "POST", f"{endpoint}/ingest-memory/objects",
                "-H", f"X-API-KEY: {api_key}",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload),
            ],
            capture_output=True, timeout=10,
        )
    except Exception:
        pass  # hooks should fail silently


def main():
    platform_hint = sys.argv[1] if len(sys.argv) > 1 else "auto"
    action = sys.argv[2] if len(sys.argv) > 2 else "auto"

    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    if platform_hint == "auto":
        platform_hint = detect_platform(data)

    extractor = EXTRACTORS.get(platform_hint, extract_tool_info_claude)
    info = extractor(data)

    # Determine action from args or context
    if action == "auto":
        if info["tool"] == "Bash" and is_git_commit(info.get("input_raw", "")):
            action = "post-commit"
        else:
            return  # no action needed

    if action == "post-commit":
        action_post_commit(info)


if __name__ == "__main__":
    main()
