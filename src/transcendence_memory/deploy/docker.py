from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess

from transcendence_memory.backend.settings import BackendSettings


@dataclass
class DockerAccess:
    available: bool
    requires_sudo: bool
    command_prefix: list[str]
    reason: str | None = None


@dataclass
class DockerDeployPlan:
    state: str
    env_file: Path
    compose_file: Path
    command: list[str]


def detect_docker_access() -> DockerAccess:
    docker_bin = shutil.which("docker")
    if docker_bin is None:
        return DockerAccess(available=False, requires_sudo=False, command_prefix=[], reason="docker-cli-missing")

    direct = subprocess.run(
        [docker_bin, "info"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if direct.returncode == 0:
        return DockerAccess(available=True, requires_sudo=False, command_prefix=[docker_bin], reason=None)

    sudo_bin = shutil.which("sudo")
    if sudo_bin is not None:
        sudo_check = subprocess.run(
            [sudo_bin, "-n", docker_bin, "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if sudo_check.returncode == 0:
            return DockerAccess(available=True, requires_sudo=True, command_prefix=[sudo_bin, docker_bin], reason=None)
        return DockerAccess(
            available=False,
            requires_sudo=True,
            command_prefix=[sudo_bin, docker_bin],
            reason="docker-requires-sudo-auth",
        )

    return DockerAccess(available=False, requires_sudo=False, command_prefix=[docker_bin], reason="docker-access-denied")


def docker_compose_command(command_prefix: list[str] | None = None) -> list[str]:
    prefix = command_prefix or ["docker"]
    return [*prefix, "compose"]


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


def render_backend_env_file(
    settings: BackendSettings,
    env_file: Path,
    *,
    command_prefix: list[str] | None = None,
) -> DockerDeployPlan:
    env_file.parent.mkdir(parents=True, exist_ok=True)
    desired = render_backend_env(settings)
    state = classify_deploy_state(desired, env_file)
    if state != "no-op":
        env_file.write_text(desired, encoding="utf-8")
    return DockerDeployPlan(
        state=state,
        env_file=env_file,
        compose_file=Path("compose.yaml"),
        command=docker_compose_command(command_prefix) + ["up", "-d"],
    )


def docker_available() -> bool:
    return detect_docker_access().available


def run_compose_up(plan: DockerDeployPlan) -> subprocess.CompletedProcess[str]:
    return subprocess.run(plan.command, text=True, capture_output=True, check=False)


def suggested_follow_up_commands(command_prefix: list[str] | None = None) -> list[str]:
    compose = " ".join(docker_compose_command(command_prefix))
    return [
        f"{compose} ps",
        f"{compose} logs backend --tail=100",
    ]
