from pathlib import Path

from transcendence_memory.backend.settings import BackendSettings
from transcendence_memory.deploy.systemd import render_systemd_env, render_systemd_service


def test_systemd_service_template_contains_required_directives() -> None:
    service = Path("deploy/systemd/transcendence-memory-backend.service").read_text(encoding="utf-8")
    assert "WorkingDirectory=" in service
    assert "EnvironmentFile=" in service
    assert "ExecStart=" in service
    assert "Restart=on-failure" in service


def test_render_systemd_service_uses_expected_contract(tmp_path: Path) -> None:
    service = render_systemd_service(
        working_directory=tmp_path / "app",
        env_file=tmp_path / "backend.env",
        python_bin="python3",
    )
    assert "WorkingDirectory=" in service
    assert "EnvironmentFile=" in service
    assert "ExecStart=python3 -m transcendence_memory.backend.main" in service


def test_render_systemd_env_contains_backend_values(tmp_path: Path) -> None:
    settings = BackendSettings(
        database_url="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/transcendence_memory",
        provider="openai",
        model="text-embedding-3-small",
        provider_base_url="https://api.openai.com/v1",
        auth_mode="api_key",
        config_path=str(tmp_path / "config"),
        secret_path=str(tmp_path / "secret"),
    )
    env_text = render_systemd_env(settings)
    assert "DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/transcendence_memory" in env_text
    assert "TRANSCENDENCE_PROVIDER=openai" in env_text
