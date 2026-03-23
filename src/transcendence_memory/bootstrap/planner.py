from __future__ import annotations

from .models import BootstrapConfig, BootstrapPlan, BootstrapSelection, DetectionResult, ResolvedPaths, Topology
from .persistence import diff_config


def build_bootstrap_plan(
    *,
    selection: BootstrapSelection,
    detection: DetectionResult,
    paths: ResolvedPaths,
    desired_config: BootstrapConfig,
    current_config: BootstrapConfig | None = None,
    dry_run: bool = True,
) -> BootstrapPlan:
    files_to_create = [
        str(paths.config_root),
        str(paths.secret_root),
        str(paths.config_file),
        str(paths.secret_file),
        str(paths.state_file),
    ]
    deferred_items = list(desired_config.deferred_items)
    if selection.topology == Topology.SPLIT_MACHINE and selection.transport_hint.value == "ip_port":
        deferred_items.append("Split-machine bootstrap is using IP + port for now; add domain/proxy details later if needed.")

    warnings = list(detection.warnings)
    if detection.port_conflicts:
        warnings.append(f"Default bootstrap port conflicts detected: {', '.join(map(str, detection.port_conflicts))}.")
    if not detection.config_path_writable:
        warnings.append("The config path is not writable.")
    if not detection.secret_path_writable:
        warnings.append("The secret path is not writable.")

    verification_commands = [
        f"transcendence-memory init {selection.role.value} --dry-run",
        "transcendence-memory config show",
        "transcendence-memory doctor",
    ]

    return BootstrapPlan(
        selection=selection,
        detection=detection,
        files_to_create=files_to_create,
        files_to_update=[str(paths.config_file), str(paths.secret_file), str(paths.state_file)],
        warnings=warnings,
        deferred_items=deferred_items,
        verification_commands=verification_commands,
        diff_summary=diff_config(current_config, desired_config),
        dry_run=dry_run,
    )


def render_plan(plan: BootstrapPlan) -> str:
    findings = [
        f"- os: {plan.detection.os_name}",
        f"- shell: {plan.detection.shell}",
        f"- docker: {'yes' if plan.detection.docker_available else 'no'}",
        f"- docker compose: {'yes' if plan.detection.docker_compose_available else 'no'}",
    ]
    if plan.detection.port_conflicts:
        findings.append(f"- port conflicts: {', '.join(map(str, plan.detection.port_conflicts))}")
    else:
        findings.append("- port conflicts: none")

    sections = [
        "== Findings ==",
        "\n".join(findings),
        "",
        "== Selection ==",
        f"- role: {plan.selection.role.value}",
        f"- topology: {plan.selection.topology.value}",
        f"- transport: {plan.selection.transport_hint.value}",
        f"- recommendation: {plan.selection.recommendation_reason}",
        "",
        "== File Actions ==",
        *[f"- create/update: {item}" for item in plan.files_to_create],
        "",
        "== Config Diff ==",
        *[f"- {item}" for item in plan.diff_summary],
        "",
        "== Warnings ==",
        *(plan.warnings or ["- none"]),
        "",
        "== Deferred Items ==",
        *(plan.deferred_items or ["- none"]),
        "",
        "== Verification ==",
        *[f"- {command}" for command in plan.verification_commands],
    ]
    return "\n".join(sections)
