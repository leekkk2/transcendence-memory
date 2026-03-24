from transcendence_memory.cli import app


def test_backend_deploy_reports_noop_state(monkeypatch, bootstrap_roots, runner, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "deploy/docker").mkdir(parents=True)
    monkeypatch.setattr("transcendence_memory.cli.docker_available", lambda: False)
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
    assert "Deployment state:" in result.stdout
    assert "docker compose ps" in result.stdout
