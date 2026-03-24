from __future__ import annotations

from pathlib import Path

from transcendence_memory.backend.settings import BackendSettings


SERVICE_NAME = "transcendence-memory-backend"


def render_systemd_env(settings: BackendSettings) -> str:
    values = {
        "DATABASE_URL": settings.database_url,
        "TRANSCENDENCE_PROVIDER": settings.provider,
        "TRANSCENDENCE_MODEL": settings.model,
        "TRANSCENDENCE_PROVIDER_BASE_URL": settings.provider_base_url,
        "TRANSCENDENCE_AUTH_MODE": settings.auth_mode,
        "TRANSCENDENCE_BIND_HOST": settings.bind_host,
        "TRANSCENDENCE_BIND_PORT": str(settings.bind_port),
    }
    return "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"


def render_systemd_service(*, working_directory: Path, env_file: Path, python_bin: str = "python") -> str:
    return "\n".join(
        [
            "[Unit]",
            "Description=Transcendence Memory Backend",
            "After=network.target",
            "",
            "[Service]",
            "Type=simple",
            f"WorkingDirectory={working_directory}",
            f"EnvironmentFile={env_file}",
            f"ExecStart={python_bin} -m transcendence_memory.backend.main",
            f"ExecStop=/bin/kill -TERM $MAINPID",
            "Restart=on-failure",
            "",
            "[Install]",
            "WantedBy=multi-user.target",
            "",
        ]
    )
