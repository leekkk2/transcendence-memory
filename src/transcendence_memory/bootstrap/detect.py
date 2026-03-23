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


def _docker_compose_available() -> bool:
    if shutil.which("docker") is None:
        return False
    result = subprocess.run(
        ["docker", "compose", "version"],
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
    docker_available = shutil.which("docker") is not None
    config_candidate = paths.config_root if paths.config_root.exists() else paths.config_root.parent
    secret_candidate = paths.secret_root if paths.secret_root.exists() else paths.secret_root.parent
    config_writable = os.access(Path(config_candidate), os.W_OK) if Path(config_candidate).exists() else os.access(Path(config_candidate).parent, os.W_OK)
    secret_writable = os.access(Path(secret_candidate), os.W_OK) if Path(secret_candidate).exists() else os.access(Path(secret_candidate).parent, os.W_OK)

    warnings: list[str] = []
    if not docker_available:
        warnings.append("Docker CLI was not found; Docker-first deployment will need manual follow-up later.")

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
        config_path_writable=config_writable,
        secret_path_writable=secret_writable,
        port_conflicts=[port for port in (8000,) if _is_port_in_use(port)],
        recommended_role=recommended_role,
        recommended_topology=recommended_topology,
        recommendation_reason=recommendation_reason,
        local_ip=_detect_local_ip(),
        warnings=warnings,
    )
