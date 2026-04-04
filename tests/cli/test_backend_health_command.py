from types import SimpleNamespace

from transcendence_memory.cli import app


def test_backend_health_emits_recovery_commands(monkeypatch, bootstrap_roots, runner) -> None:
    monkeypatch.setattr("transcendence_memory.cli.probe_backend_service", lambda runtime: (False, None, "connection failed"))
    monkeypatch.setattr(
        "transcendence_memory.cli.classify_runtime_health",
        lambda runtime, deployment_mode="docker-first": {
            "status": "degraded",
            "database": {"status": "error", "details": "db unavailable"},
            "provider_config": {"status": "ok", "provider": "openai", "base_url": "https://api.openai.com/v1"},
            "deployment": {"mode": "docker-first"},
        },
    )
    monkeypatch.setattr(
        "transcendence_memory.cli.detect_docker_access",
        lambda: SimpleNamespace(available=False, requires_sudo=False, command_prefix=["docker"]),
    )
    result = runner.invoke(
        app,
        [
            "backend",
            "health",
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
        ],
    )
    assert result.exit_code == 1
    assert "docker compose ps" in result.stdout
    assert "docker compose logs backend --tail=100" in result.stdout
    assert "systemctl status transcendence-memory-backend" in result.stdout
    assert "journalctl -u transcendence-memory-backend -n 100 --no-pager" in result.stdout


def test_backend_health_emits_sudo_docker_recovery_commands(monkeypatch, bootstrap_roots, runner) -> None:
    monkeypatch.setattr("transcendence_memory.cli.probe_backend_service", lambda runtime: (False, None, "connection failed"))
    monkeypatch.setattr(
        "transcendence_memory.cli.classify_runtime_health",
        lambda runtime, deployment_mode="docker-first": {
            "status": "degraded",
            "database": {"status": "error", "details": "db unavailable"},
            "provider_config": {"status": "ok", "provider": "openai", "base_url": "https://api.openai.com/v1"},
            "deployment": {"mode": "docker-first"},
        },
    )
    monkeypatch.setattr(
        "transcendence_memory.cli.detect_docker_access",
        lambda: SimpleNamespace(available=False, requires_sudo=True, command_prefix=["sudo", "docker"]),
    )
    result = runner.invoke(
        app,
        [
            "backend",
            "health",
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
        ],
    )
    assert result.exit_code == 1
    assert "sudo docker compose ps" in result.stdout
    assert "sudo docker compose logs backend --tail=100" in result.stdout
