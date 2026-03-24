from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from .detect import detect_environment
from .models import ResolvedPaths
from .paths import ensure_layout, ensure_secret_permissions
from .persistence import read_config, read_state, regenerate_config_from_state, secret_file_needs_permission_fix


class DoctorFinding(BaseModel):
    classification: str
    code: str
    message: str
    suggested_command: str


def run_doctor(paths: ResolvedPaths, *, fix: bool = False) -> list[DoctorFinding]:
    findings: list[DoctorFinding] = []

    if not paths.config_root.exists():
        findings.append(
            DoctorFinding(
                classification="auto-fixable",
                code="missing-config-root",
                message=f"Config root {paths.config_root} does not exist.",
                suggested_command="transcendence-memory doctor --fix",
            )
        )
    if not paths.secret_root.exists():
        findings.append(
            DoctorFinding(
                classification="auto-fixable",
                code="missing-secret-root",
                message=f"Secret root {paths.secret_root} does not exist.",
                suggested_command="transcendence-memory doctor --fix",
            )
        )

    try:
        config = read_config(paths)
    except Exception as exc:  # pragma: no cover - defensive
        config = None
        findings.append(
            DoctorFinding(
                classification="needs input",
                code="invalid-config",
                message=f"Config file is invalid: {exc}",
                suggested_command="transcendence-memory init both --dry-run",
            )
        )
    else:
        if config is None:
            suggestion = "transcendence-memory init both --dry-run"
            classification = "needs input"
            if read_state(paths) is not None:
                suggestion = "transcendence-memory doctor --fix"
                classification = "auto-fixable"
            findings.append(
                DoctorFinding(
                    classification=classification,
                    code="missing-config-file",
                    message=f"Config file {paths.config_file} is missing.",
                    suggested_command=suggestion,
                )
            )
        elif not paths.identity_file.exists():
            findings.append(
                DoctorFinding(
                    classification="needs input",
                    code="missing-identity-doc",
                    message=(
                        f"Role identity document {paths.identity_file} is missing. "
                        f"Confirm that this machine is `{config.role.value}` and补录对应身份后再继续。"
                    ),
                    suggested_command=f"transcendence-memory init {config.role.value} --yes",
                )
            )

    if not paths.secret_file.exists():
        findings.append(
            DoctorFinding(
                classification="needs input",
                code="missing-secret-file",
                message=f"Secret file {paths.secret_file} is missing.",
                suggested_command="transcendence-memory init both --dry-run",
            )
        )
    elif secret_file_needs_permission_fix(paths):
        findings.append(
            DoctorFinding(
                classification="auto-fixable",
                code="secret-permissions",
                message=f"Secret file {paths.secret_file} does not have the expected permissions.",
                suggested_command="transcendence-memory doctor --fix",
            )
        )

    detection = detect_environment(paths)
    if not detection.docker_available:
        findings.append(
            DoctorFinding(
                classification="manual follow-up",
                code="docker-missing",
                message="Docker CLI is not available on this machine.",
                suggested_command="Install Docker, then re-run `transcendence-memory doctor`.",
            )
        )
    if detection.port_conflicts:
        findings.append(
            DoctorFinding(
                classification="needs input",
                code="port-conflict",
                message=f"Default bootstrap port conflict detected: {', '.join(map(str, detection.port_conflicts))}.",
                suggested_command="Choose a different port via config and re-run `transcendence-memory init ... --dry-run`.",
            )
        )

    if fix:
        ensure_layout(paths)
        if read_config(paths) is None:
            regenerate_config_from_state(paths)
        ensure_secret_permissions(paths.secret_file)

    return findings


def render_findings(findings: list[DoctorFinding]) -> str:
    if not findings:
        return "No doctor findings."
    lines = []
    for finding in findings:
        lines.append(f"- [{finding.classification}] {finding.code}: {finding.message}")
        lines.append(f"  next: {finding.suggested_command}")
    return "\n".join(lines)
