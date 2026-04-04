from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy import text

from transcendence_memory.backend.db.session import create_engine_from_settings


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
    database = {"status": "unknown", "details": "database health not checked"}
    try:
        engine = create_engine_from_settings(runtime.settings)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database = {"status": "ok", "details": "database reachable"}
    except Exception as exc:  # noqa: BLE001
        database = {"status": "error", "details": str(exc)}

    provider_config = {
        "status": "ok" if runtime.settings.provider and runtime.settings.provider_base_url else "error",
        "provider": runtime.settings.provider,
        "base_url": runtime.settings.provider_base_url,
    }

    overall = "ok"
    if database["status"] != "ok" or provider_config["status"] != "ok":
        overall = "degraded"

    return {
        "status": overall,
        "database": database,
        "provider_config": provider_config,
        "deployment": {"mode": deployment_mode},
    }


def probe_backend_service(runtime) -> tuple[bool, dict[str, Any] | None, str | None]:
    try:
        response = httpx.get(f"{runtime.settings.advertised_url.rstrip('/')}/api/v1/health", timeout=5.0)
        response.raise_for_status()
        return True, response.json(), None
    except Exception as exc:  # noqa: BLE001
        return False, None, str(exc)


def health_follow_up_commands(failure_type: str, *, command_prefix: list[str] | None = None) -> list[str]:
    docker_commands = docker_follow_up_commands(command_prefix)
    commands = [*docker_commands, SYSTEMD_STATUS_CMD, SYSTEMD_LOGS_CMD]
    if failure_type == "docker":
        return commands
    if failure_type == "systemd":
        return commands
    return commands
