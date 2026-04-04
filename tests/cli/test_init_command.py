from transcendence_memory.cli import app


def test_init_backend_dry_run_shows_same_machine(bootstrap_roots, runner) -> None:
    result = runner.invoke(
        app,
        [
            "init",
            "backend",
            "--topology",
            "same_machine",
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "same_machine" in result.stdout
    assert "== Findings ==" in result.stdout


def test_init_frontend_dry_run_shows_split_machine(bootstrap_roots, runner) -> None:
    result = runner.invoke(
        app,
        [
            "init",
            "frontend",
            "--topology",
            "split_machine",
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "split_machine" in result.stdout


def test_init_both_writes_non_secret_config(bootstrap_roots, runner) -> None:
    result = runner.invoke(
        app,
        [
            "init",
            "both",
            "--topology",
            "same_machine",
            "--provider",
            "openai",
            "--model",
            "text-embedding-3-small",
            "--base-url",
            "http://127.0.0.1:8711",
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
            "--yes",
        ],
    )
    assert result.exit_code == 0
    config_text = (bootstrap_roots["config_root"] / "config.toml").read_text(encoding="utf-8")
    assert "provider = \"openai\"" in config_text
    assert "base_url = \"http://127.0.0.1:8711\"" in config_text


def test_init_frontend_writes_role_identity_document(bootstrap_roots, runner) -> None:
    result = runner.invoke(
        app,
        [
            "init",
            "frontend",
            "--topology",
            "split_machine",
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
            "--yes",
        ],
    )
    assert result.exit_code == 0
    identity_text = (bootstrap_roots["config_root"] / "operator-identity.md").read_text(encoding="utf-8")
    assert "frontend" in identity_text
    assert "不负责部署本机后端" in identity_text
    assert "docs/frontend-handoff.md" in identity_text
    assert "transcendence-memory/references/identity-frontend.md" in identity_text
