from __future__ import annotations

from typing import Any

import httpx


DOCKER_STATUS_CMD = "docker compose ps"
DOCKER_LOGS_CMD = "docker compose logs backend --tail=100"
SYSTEMD_STATUS_CMD = "systemctl status transcendence-memory-backend"
SYSTEMD_LOGS_CMD = "journalctl -u transcendence-memory-backend -n 100 --no-pager"


def docker_follow_up_commands(command_prefix: list[str] | None = None) -> list[str]:
    compose = " ".join([*(command_prefix or ["docker"]), "compose"])
    return [
        f"{compose} ps",
        f"{compose} logs backend --tail=100",
    ]


def classify_runtime_health(runtime, *, deployment_mode: str) -> dict[str, Any]:
    return {
        "status": "info",
        "runtime_source": "canonical-private-runtime",
        "advertised_url": runtime.settings.advertised_url,
        "provider": runtime.settings.provider,
        "provider_base_url": runtime.settings.provider_base_url,
        "auth_mode": runtime.settings.auth_mode,
        "deployment": {"mode": deployment_mode},
    }


def probe_backend_service(runtime) -> tuple[bool, dict[str, Any] | None, str | None]:
    try:
        response = httpx.get(f"{runtime.settings.advertised_url.rstrip('/')}{runtime.settings.health_path}", timeout=5.0)
        response.raise_for_status()
        return True, response.json(), None
    except Exception as exc:  # noqa: BLE001
        return False, None, str(exc)


def health_follow_up_commands(failure_type: str, *, command_prefix: list[str] | None = None) -> list[str]:
    docker_commands = docker_follow_up_commands(command_prefix)
    commands = [*docker_commands, SYSTEMD_STATUS_CMD, SYSTEMD_LOGS_CMD]
    return commands
