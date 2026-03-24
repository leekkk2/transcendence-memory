from pathlib import Path

from transcendence_memory.backend.settings import BackendSettings
from transcendence_memory.deploy.docker import classify_deploy_state, render_backend_env


def test_dockerfile_uses_backend_main_entrypoint() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    assert "uvicorn" in dockerfile
    assert "transcendence_memory.backend.main:app" in dockerfile


def test_dockerignore_excludes_local_runtime_noise() -> None:
    dockerignore = Path(".dockerignore").read_text(encoding="utf-8")
    assert ".venv" in dockerignore
    assert ".pytest_cache" in dockerignore
    assert "__pycache__" in dockerignore


def test_compose_stack_has_health_checks_and_service_healthy() -> None:
    compose = Path("compose.yaml").read_text(encoding="utf-8")
    assert "healthcheck" in compose
    assert "depends_on" in compose
    assert "service_healthy" in compose


def test_render_backend_env_contains_backend_and_postgres_values(tmp_path: Path) -> None:
    settings = BackendSettings(
        database_url="postgresql+psycopg://postgres:postgres@postgres:5432/transcendence_memory",
        provider="openai",
        model="text-embedding-3-small",
        provider_base_url="https://api.openai.com/v1",
        auth_mode="api_key",
        config_path=str(tmp_path / "config"),
        secret_path=str(tmp_path / "secret"),
    )
    rendered = render_backend_env(settings)
    assert "DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/transcendence_memory" in rendered
    assert "TRANSCENDENCE_PROVIDER=openai" in rendered


def test_classify_deploy_state_distinguishes_create_update_noop(tmp_path: Path) -> None:
    env_file = tmp_path / "backend.env"
    desired = "DATABASE_URL=db\n"
    assert classify_deploy_state(desired, env_file) == "create"
    env_file.write_text("DATABASE_URL=other\n", encoding="utf-8")
    assert classify_deploy_state(desired, env_file) == "update"
    env_file.write_text(desired, encoding="utf-8")
    assert classify_deploy_state(desired, env_file) == "no-op"
