from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
from pathlib import Path

from .models import DetectionResult, ResolvedPaths, Role, Topology


def _detect_shell() -> str:
    return os.environ.get("SHELL") or os.environ.get("COMSPEC") or "unknown"


def _docker_access() -> tuple[bool, bool, bool]:
    docker_bin = shutil.which("docker")
    if docker_bin is None:
        return False, False, False

    direct = subprocess.run(
        [docker_bin, "info"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if direct.returncode == 0:
        return True, False, False

    sudo_bin = shutil.which("sudo")
    if sudo_bin is None:
        return False, False, False

    sudo_check = subprocess.run(
        [sudo_bin, "-n", docker_bin, "info"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if sudo_check.returncode == 0:
        return True, True, True
    return False, True, False


def _docker_compose_available() -> bool:
    docker_bin = shutil.which("docker")
    if docker_bin is None:
        return False
    result = subprocess.run(
        [docker_bin, "compose", "version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _detect_local_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def detect_environment(paths: ResolvedPaths, requested_role: Role | None = None) -> DetectionResult:
    os_name = platform.system().lower()
    docker_available, docker_requires_sudo, docker_sudo_works = _docker_access()
    config_candidate = paths.config_root if paths.config_root.exists() else paths.config_root.parent
    secret_candidate = paths.secret_root if paths.secret_root.exists() else paths.secret_root.parent
    config_writable = os.access(Path(config_candidate), os.W_OK) if Path(config_candidate).exists() else os.access(Path(config_candidate).parent, os.W_OK)
    secret_writable = os.access(Path(secret_candidate), os.W_OK) if Path(secret_candidate).exists() else os.access(Path(secret_candidate).parent, os.W_OK)

    warnings: list[str] = []
    if shutil.which("docker") is None:
        warnings.append("Docker CLI was not found; Docker-first deployment will need manual follow-up later.")
    elif docker_requires_sudo and not docker_sudo_works:
        warnings.append("Docker exists on the host, but this session cannot use it directly; host-level sudo/authorization is required.")
    elif docker_requires_sudo and docker_sudo_works:
        warnings.append("Docker is available through host sudo; deployment commands should prefer the sudo Docker path on this machine.")

    recommended_role = requested_role or Role.BOTH
    recommended_topology = Topology.SAME_MACHINE
    recommendation_reason = "Default to both + same_machine for the fastest first bootstrap."
    if requested_role in {Role.BACKEND, Role.FRONTEND}:
        recommendation_reason = f"Role `{requested_role.value}` was chosen explicitly; recommend same_machine unless split-machine is required."

    return DetectionResult(
        os_name=os_name,
        shell=_detect_shell(),
        docker_available=docker_available,
        docker_compose_available=_docker_compose_available(),
        docker_requires_sudo=docker_requires_sudo,
        docker_sudo_works=docker_sudo_works,
        config_path_writable=config_writable,
        secret_path_writable=secret_writable,
        port_conflicts=[],
        recommended_role=recommended_role,
        recommended_topology=recommended_topology,
        recommendation_reason=recommendation_reason,
        local_ip=_detect_local_ip(),
        warnings=warnings,
    )
