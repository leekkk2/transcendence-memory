#!/usr/bin/env bash
set -euo pipefail
exec "${TM_PYTHON:-python3}" "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/install.py" "$@"
