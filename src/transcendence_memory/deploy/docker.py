from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess


@dataclass
class DockerAccess:
    available: bool
    requires_sudo: bool
    command_prefix: list[str]
    reason: str | None = None


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


def suggested_follow_up_commands(command_prefix: list[str] | None = None) -> list[str]:
    prefix = command_prefix or ["docker"]
    compose = " ".join([*prefix, "compose"])
    return [
        f"{compose} ps",
        f"{compose} logs backend --tail=100",
    ]
