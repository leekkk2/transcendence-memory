from __future__ import annotations

import json
from pathlib import Path

import typer

from .backend.auth.api_keys import auth_status_from_runtime
from .backend.auth.oauth import login_via_browser
from .backend.auth.tokens import clear_token_state, store_token_state
from .backend.settings import load_runtime_config
from .deploy.docker import docker_available, render_backend_env_file, run_compose_up, suggested_follow_up_commands
from .deploy.health import (
    DOCKER_LOGS_CMD,
    DOCKER_STATUS_CMD,
    SYSTEMD_LOGS_CMD,
    SYSTEMD_STATUS_CMD,
    classify_runtime_health,
    health_follow_up_commands,
    probe_backend_service,
)
from .bootstrap.detect import detect_environment
from .bootstrap.doctor import render_findings, run_doctor
from .bootstrap.models import BootstrapMode, BootstrapSecrets, BootstrapSelection, ProviderSettings, Role, Topology, TransportHint
from .bootstrap.paths import resolve_paths
from .bootstrap.persistence import (
    build_bootstrap_config,
    read_config,
    read_secrets,
    update_bootstrap_auth_config,
    write_config,
    write_secrets,
    write_state,
)
from .bootstrap.planner import build_bootstrap_plan, render_plan

app = typer.Typer(help="Bootstrap and configuration CLI for Transcendence Memory.")
init_app = typer.Typer(help="Initialize bootstrap state for backend, frontend, or both roles.")
config_app = typer.Typer(help="Inspect non-secret bootstrap configuration.")
auth_app = typer.Typer(help="Inspect and manage authentication state.")
backend_app = typer.Typer(help="Deploy and operate the backend runtime.")

app.add_typer(init_app, name="init")
app.add_typer(config_app, name="config")
app.add_typer(auth_app, name="auth")
app.add_typer(backend_app, name="backend")


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


@auth_app.command("set-api-key")
def auth_set_api_key(
    api_key: str = typer.Option(..., "--api-key"),
    config_path: Path | None = typer.Option(None, "--config-path"),
    secret_path: Path | None = typer.Option(None, "--secret-path"),
) -> None:
    """Configure the local API key used for backend and frontend workflows."""
    paths = resolve_paths(config_path=config_path, secret_path=secret_path)
    secrets = read_secrets(paths) or BootstrapSecrets()
    secrets.api_key = api_key
    write_secrets(secrets, paths)
    typer.echo("API key stored in secret storage.")


@auth_app.command("status")
def auth_status(
    config_path: Path | None = typer.Option(None, "--config-path"),
    secret_path: Path | None = typer.Option(None, "--secret-path"),
) -> None:
    """Show redacted local auth status."""
    runtime = load_runtime_config(config_path=config_path, secret_path=secret_path)
    status = auth_status_from_runtime(runtime)
    typer.echo(json.dumps(status.model_dump(mode="json"), indent=2))


@auth_app.command("login")
def auth_login(
    issuer: str | None = typer.Option(None, "--issuer"),
    authorize_url: str | None = typer.Option(None, "--authorize-url"),
    token_url: str | None = typer.Option(None, "--token-url"),
    client_id: str | None = typer.Option(None, "--client-id"),
    scope: list[str] | None = typer.Option(None, "--scope"),
    config_path: Path | None = typer.Option(None, "--config-path"),
    secret_path: Path | None = typer.Option(None, "--secret-path"),
) -> None:
    """Complete a browser-based OAuth login with PKCE and loopback redirect."""
    runtime = load_runtime_config(config_path=config_path, secret_path=secret_path)
    oauth = runtime.settings.oauth.model_copy(
        update={
            "issuer": issuer or runtime.settings.oauth.issuer,
            "authorize_url": authorize_url or runtime.settings.oauth.authorize_url,
            "token_url": token_url or runtime.settings.oauth.token_url,
            "client_id": client_id or runtime.settings.oauth.client_id,
            "scopes": scope or runtime.settings.oauth.scopes,
        }
    )
    token_state = login_via_browser(oauth)
    store_token_state(runtime.paths, token_state)
    update_bootstrap_auth_config(
        runtime.paths,
        auth_mode="oauth",
        oauth_issuer=oauth.issuer,
        oauth_authorize_url=oauth.authorize_url,
        oauth_token_url=oauth.token_url,
        oauth_client_id=oauth.client_id,
        oauth_scopes=oauth.scopes,
    )
    typer.echo("OAuth login completed.")


@auth_app.command("logout")
def auth_logout(
    config_path: Path | None = typer.Option(None, "--config-path"),
    secret_path: Path | None = typer.Option(None, "--secret-path"),
) -> None:
    """Clear stored OAuth tokens from secret storage."""
    paths = resolve_paths(config_path=config_path, secret_path=secret_path)
    clear_token_state(paths)
    update_bootstrap_auth_config(paths, auth_mode="api_key")
    typer.echo("Stored OAuth credentials cleared.")


@backend_app.command("deploy")
def backend_deploy(
    config_path: Path | None = typer.Option(None, "--config-path"),
    secret_path: Path | None = typer.Option(None, "--secret-path"),
) -> None:
    """Render deployment assets and deploy the backend via Docker Compose."""
    runtime = load_runtime_config(config_path=config_path, secret_path=secret_path)
    env_file = Path("deploy/docker/backend.env")
    plan = render_backend_env_file(runtime.settings, env_file)
    typer.echo(f"Deployment state: {plan.state}")
    typer.echo(f"Rendered env file: {plan.env_file}")

    if not docker_available():
        typer.echo("Docker is not available on this machine.")
        for command in health_follow_up_commands("docker"):
            typer.echo(f"- {command}")
        raise typer.Exit(code=1)

    result = run_compose_up(plan)
    if result.returncode != 0:
        typer.echo(result.stderr or result.stdout)
        for command in health_follow_up_commands("docker"):
            typer.echo(f"- {command}")
        raise typer.Exit(code=result.returncode)

    typer.echo("Backend deploy completed.")
    for command in suggested_follow_up_commands():
        typer.echo(f"- {command}")


@backend_app.command("restart")
def backend_restart() -> None:
    """Restart only the backend service in the Compose stack."""
    if not docker_available():
        typer.echo("Docker is not available on this machine.")
        raise typer.Exit(code=1)
    import subprocess

    result = subprocess.run(["docker", "compose", "restart", "backend"], text=True, capture_output=True, check=False)
    if result.returncode != 0:
        typer.echo(result.stderr or result.stdout)
        raise typer.Exit(code=result.returncode)
    typer.echo("Backend restart completed.")
    typer.echo(f"- {DOCKER_STATUS_CMD}")
    typer.echo(f"- {DOCKER_LOGS_CMD}")


@backend_app.command("health")
def backend_health(
    config_path: Path | None = typer.Option(None, "--config-path"),
    secret_path: Path | None = typer.Option(None, "--secret-path"),
) -> None:
    """Inspect backend deployment health and print exact next commands."""
    runtime = load_runtime_config(config_path=config_path, secret_path=secret_path)
    local = classify_runtime_health(runtime, deployment_mode="docker-first")
    reachable, payload, error = probe_backend_service(runtime)

    result = {
        "service_reachable": reachable,
        "local": local,
        "remote": payload,
    }
    typer.echo(json.dumps(result, indent=2))

    if reachable and local["status"] == "ok":
        return

    failure_type = "docker"
    if local["deployment"]["mode"] == "systemd":
        failure_type = "systemd"
    typer.echo("Next commands:")
    for command in health_follow_up_commands(failure_type):
        typer.echo(f"- {command}")
    if error:
        typer.echo(f"- probe error: {error}")
    raise typer.Exit(code=1)


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
