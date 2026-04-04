from types import SimpleNamespace

from transcendence_memory.cli import app


def test_backend_deploy_reports_reference_runtime_boundary(monkeypatch, bootstrap_roots, runner) -> None:
    monkeypatch.setattr(
        "transcendence_memory.cli.detect_docker_access",
        lambda: SimpleNamespace(available=False, requires_sudo=False, command_prefix=["docker"]),
    )
    result = runner.invoke(
        app,
        [
            "backend",
            "deploy",
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
        ],
    )
    assert result.exit_code == 1
    assert "no longer deploys a bundled backend runtime" in result.stdout
    assert "docker compose ps" in result.stdout


def test_backend_deploy_reports_sudo_host_path(monkeypatch, bootstrap_roots, runner) -> None:
    monkeypatch.setattr(
        "transcendence_memory.cli.detect_docker_access",
        lambda: SimpleNamespace(available=False, requires_sudo=True, command_prefix=["sudo", "docker"]),
    )
    result = runner.invoke(
        app,
        [
            "backend",
            "deploy",
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
        ],
    )
    assert result.exit_code == 1
    assert "canonical backend runtime" in result.stdout
    assert "sudo docker compose ps" in result.stdout
