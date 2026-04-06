: << 'CMDBLOCK'
@echo off
setlocal enabledelayedexpansion
set "HOOK_NAME=%~1"
set "SCRIPT_DIR=%~dp0"
if exist "C:\Program Files\Git\bin\bash.exe" (
    "C:\Program Files\Git\bin\bash.exe" "%SCRIPT_DIR%%HOOK_NAME%" %*
    exit /b %errorlevel%
)
if exist "C:\Program Files (x86)\Git\bin\bash.exe" (
    "C:\Program Files (x86)\Git\bin\bash.exe" "%SCRIPT_DIR%%HOOK_NAME%" %*
    exit /b %errorlevel%
)
where bash >nul 2>nul && (
    bash "%SCRIPT_DIR%%HOOK_NAME%" %*
    exit /b %errorlevel%
)
exit /b 0
CMDBLOCK

#!/usr/bin/env bash
set -euo pipefail

HOOK_NAME="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -z "$HOOK_NAME" ]; then
  echo "Usage: run-hook.cmd <hook-name>" >&2
  exit 1
fi

HOOK_SCRIPT="${SCRIPT_DIR}/${HOOK_NAME}"
if [ -x "$HOOK_SCRIPT" ]; then
  exec "$HOOK_SCRIPT"
elif [ -f "$HOOK_SCRIPT" ]; then
  exec bash "$HOOK_SCRIPT"
else
  echo "Hook script not found: ${HOOK_SCRIPT}" >&2
  exit 1
fi
