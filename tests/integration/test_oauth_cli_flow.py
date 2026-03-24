from transcendence_memory.cli import app


def test_oauth_cli_flow(monkeypatch, bootstrap_roots, runner) -> None:
    monkeypatch.setattr(
        "transcendence_memory.cli.login_via_browser",
        lambda oauth: __import__("transcendence_memory.backend.auth.models", fromlist=["OAuthTokenState"]).OAuthTokenState(
            access_token="access-token",
            refresh_token="refresh-token",
            token_type="Bearer",
            subject="user-123",
        ),
    )

    result = runner.invoke(
        app,
        [
            "auth",
            "login",
            "--issuer",
            "https://issuer.example",
            "--authorize-url",
            "https://issuer.example/authorize",
            "--token-url",
            "https://issuer.example/token",
            "--client-id",
            "client-123",
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
        ],
    )
    assert result.exit_code == 0

    status = runner.invoke(
        app,
        [
            "auth",
            "status",
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
        ],
    )
    assert status.exit_code == 0
    assert "access-token" not in status.stdout
    assert "refresh-token" not in status.stdout

    logout = runner.invoke(
        app,
        [
            "auth",
            "logout",
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
        ],
    )
    assert logout.exit_code == 0
