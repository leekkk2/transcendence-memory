from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess

from transcendence_memory.backend.settings import BackendSettings


@dataclass
class DockerDeployPlan:
    state: str
    env_file: Path
    compose_file: Path
    command: list[str]


def docker_compose_command() -> list[str]:
    return ["docker", "compose"]


def render_backend_env(settings: BackendSettings) -> str:
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


def classify_deploy_state(desired_env: str, env_file: Path) -> str:
    if not env_file.exists():
        return "create"
    current = env_file.read_text(encoding="utf-8")
    if current == desired_env:
        return "no-op"
    return "update"


def render_backend_env_file(settings: BackendSettings, env_file: Path) -> DockerDeployPlan:
    env_file.parent.mkdir(parents=True, exist_ok=True)
    desired = render_backend_env(settings)
    state = classify_deploy_state(desired, env_file)
    if state != "no-op":
        env_file.write_text(desired, encoding="utf-8")
    return DockerDeployPlan(
        state=state,
        env_file=env_file,
        compose_file=Path("compose.yaml"),
        command=docker_compose_command() + ["up", "-d"],
    )


def docker_available() -> bool:
    return shutil.which("docker") is not None


def run_compose_up(plan: DockerDeployPlan) -> subprocess.CompletedProcess[str]:
    return subprocess.run(plan.command, text=True, capture_output=True, check=False)


def suggested_follow_up_commands() -> list[str]:
    return [
        "docker compose ps",
        "docker compose logs backend --tail=100",
    ]
