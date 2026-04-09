: << 'CMDBLOCK'
@echo off
setlocal enabledelayedexpansion
set "HOOK_NAME=%~1"
set "SCRIPT_DIR=%~dp0"
rem 动态查找 bash，不使用硬编码路径
where bash >nul 2>nul && (
    bash "%SCRIPT_DIR%%HOOK_NAME%" %*
    exit /b %errorlevel%
)
rem 回退：通过 Git 安装目录动态定位 bash
for /f "tokens=*" %%G in ('where git 2^>nul') do (
    set "GIT_PATH=%%~dpG"
    if exist "!GIT_PATH!bash.exe" (
        "!GIT_PATH!bash.exe" "%SCRIPT_DIR%%HOOK_NAME%" %*
        exit /b %errorlevel%
    )
    if exist "!GIT_PATH!..\bin\bash.exe" (
        "!GIT_PATH!..\bin\bash.exe" "%SCRIPT_DIR%%HOOK_NAME%" %*
        exit /b %errorlevel%
    )
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
