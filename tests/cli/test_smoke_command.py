from transcendence_memory.cli import app


def test_smoke_command_reports_health_embed_search(monkeypatch, bootstrap_roots, runner) -> None:
    monkeypatch.setattr(
        "transcendence_memory.cli.run_smoke_checks",
        lambda runtime: {
            "health": {"status": "ok"},
            "embed": {"id": "record-1"},
            "search": {"count": 1},
        },
    )
    result = runner.invoke(
        app,
        [
            "frontend",
            "smoke",
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
        ],
    )
    assert result.exit_code == 0
    assert "health" in result.stdout
    assert "embed" in result.stdout
    assert "search" in result.stdout
