from transcendence_memory.cli import app


def test_rerun_dry_run_shows_provider_diff(bootstrap_roots, runner) -> None:
    first = runner.invoke(
        app,
        [
            "init",
            "both",
            "--topology",
            "same_machine",
            "--provider",
            "openai",
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
            "--yes",
        ],
    )
    assert first.exit_code == 0

    second = runner.invoke(
        app,
        [
            "init",
            "both",
            "--topology",
            "same_machine",
            "--provider",
            "anthropic",
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
            "--dry-run",
        ],
    )
    assert second.exit_code == 0
    assert "provider: 'openai' -> 'anthropic'" in second.stdout
