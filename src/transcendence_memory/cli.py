from __future__ import annotations

import json
from pathlib import Path

import typer

from .bootstrap.detect import detect_environment
from .bootstrap.doctor import render_findings, run_doctor
from .bootstrap.models import BootstrapMode, BootstrapSecrets, BootstrapSelection, ProviderSettings, Role, Topology, TransportHint
from .bootstrap.paths import resolve_paths
from .bootstrap.persistence import build_bootstrap_config, read_config, write_config, write_secrets, write_state
from .bootstrap.planner import build_bootstrap_plan, render_plan

app = typer.Typer(help="Bootstrap and configuration CLI for Transcendence Memory.")
init_app = typer.Typer(help="Initialize bootstrap state for backend, frontend, or both roles.")
config_app = typer.Typer(help="Inspect non-secret bootstrap configuration.")

app.add_typer(init_app, name="init")
app.add_typer(config_app, name="config")


def _resolve_topology(
    requested: Topology | None,
    recommended: Topology,
    *,
    dry_run: bool,
    yes: bool,
) -> Topology:
    if requested is not None:
        return requested
    if dry_run or yes:
        return recommended

    typer.echo(f"Recommended topology: {recommended.value}")
    use_recommended = typer.confirm("Use the recommended topology?", default=True)
    if use_recommended:
        return recommended

    chosen = typer.prompt(
        "Choose topology",
        type=typer.Choice([Topology.SAME_MACHINE.value, Topology.SPLIT_MACHINE.value]),
        default=recommended.value,
    )
    return Topology(chosen)


def _run_init(
    role: Role,
    *,
    topology: Topology | None,
    provider: str,
    model: str,
    base_url: str | None,
    config_path: Path | None,
    secret_path: Path | None,
    dry_run: bool,
    yes: bool,
) -> None:
    paths = resolve_paths(config_path=config_path, secret_path=secret_path)
    detection = detect_environment(paths, requested_role=role)
    selected_topology = _resolve_topology(topology, detection.recommended_topology, dry_run=dry_run, yes=yes)
    transport_hint = TransportHint.DOMAIN_PROXY if base_url and "://" in base_url and "." in base_url else TransportHint.IP_PORT
    selection = BootstrapSelection(
        role=role,
        topology=selected_topology,
        transport_hint=transport_hint,
        mode=BootstrapMode.AUTO_RECOMMENDED,
        provider=ProviderSettings(provider=provider, model=model, base_url=base_url),
        recommendation_reason=detection.recommendation_reason,
    )
    desired_config = build_bootstrap_config(selection, paths, detection)
    current_config = read_config(paths)
    plan = build_bootstrap_plan(
        selection=selection,
        detection=detection,
        paths=paths,
        desired_config=desired_config,
        current_config=current_config,
        dry_run=dry_run,
    )

    typer.echo(render_plan(plan))
    if dry_run:
        raise typer.Exit(code=0)

    if not yes and not typer.confirm("Apply this bootstrap plan?", default=True):
        raise typer.Exit(code=1)

    write_config(desired_config, paths)
    write_secrets(BootstrapSecrets(api_key=None), paths)
    write_state(selection, plan, desired_config, paths)

    typer.echo("")
    typer.echo("Bootstrap configuration written.")
    typer.echo("Next commands:")
    typer.echo("- transcendence-memory config show")
    typer.echo("- transcendence-memory doctor")


@init_app.command("backend")
def init_backend(
    topology: Topology | None = typer.Option(None, "--topology", help="same_machine or split_machine"),
    provider: str = typer.Option("openai", "--provider"),
    model: str = typer.Option("text-embedding-3-small", "--model"),
    base_url: str | None = typer.Option(None, "--base-url"),
    config_path: Path | None = typer.Option(None, "--config-path"),
    secret_path: Path | None = typer.Option(None, "--secret-path"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "--yes"),
) -> None:
    """Initialize backend bootstrap state."""
    _run_init(
        Role.BACKEND,
        topology=topology,
        provider=provider,
        model=model,
        base_url=base_url,
        config_path=config_path,
        secret_path=secret_path,
        dry_run=dry_run,
        yes=yes,
    )


@init_app.command("frontend")
def init_frontend(
    topology: Topology | None = typer.Option(None, "--topology", help="same_machine or split_machine"),
    provider: str = typer.Option("openai", "--provider"),
    model: str = typer.Option("text-embedding-3-small", "--model"),
    base_url: str | None = typer.Option(None, "--base-url"),
    config_path: Path | None = typer.Option(None, "--config-path"),
    secret_path: Path | None = typer.Option(None, "--secret-path"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "--yes"),
) -> None:
    """Initialize frontend bootstrap state."""
    _run_init(
        Role.FRONTEND,
        topology=topology,
        provider=provider,
        model=model,
        base_url=base_url,
        config_path=config_path,
        secret_path=secret_path,
        dry_run=dry_run,
        yes=yes,
    )


@init_app.command("both")
def init_both(
    topology: Topology | None = typer.Option(None, "--topology", help="same_machine or split_machine"),
    provider: str = typer.Option("openai", "--provider"),
    model: str = typer.Option("text-embedding-3-small", "--model"),
    base_url: str | None = typer.Option(None, "--base-url"),
    config_path: Path | None = typer.Option(None, "--config-path"),
    secret_path: Path | None = typer.Option(None, "--secret-path"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "--yes"),
) -> None:
    """Initialize both backend and frontend bootstrap state."""
    _run_init(
        Role.BOTH,
        topology=topology,
        provider=provider,
        model=model,
        base_url=base_url,
        config_path=config_path,
        secret_path=secret_path,
        dry_run=dry_run,
        yes=yes,
    )


@config_app.command("show")
def config_show(
    config_path: Path | None = typer.Option(None, "--config-path"),
    secret_path: Path | None = typer.Option(None, "--secret-path"),
) -> None:
    """Show non-secret bootstrap configuration."""
    paths = resolve_paths(config_path=config_path, secret_path=secret_path)
    config = read_config(paths)
    if config is None:
        typer.echo("No bootstrap configuration found.")
        raise typer.Exit(code=1)
    typer.echo(json.dumps(config.model_dump(mode="json"), indent=2))


@app.command("doctor")
def doctor(
    config_path: Path | None = typer.Option(None, "--config-path"),
    secret_path: Path | None = typer.Option(None, "--secret-path"),
    fix: bool = typer.Option(False, "--fix"),
) -> None:
    """Run bootstrap-scoped diagnostics."""
    paths = resolve_paths(config_path=config_path, secret_path=secret_path)
    findings = run_doctor(paths, fix=fix)
    typer.echo(render_findings(findings))
    if findings:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
