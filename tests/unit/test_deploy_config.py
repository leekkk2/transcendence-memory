from pathlib import Path


def test_dockerfile_uses_backend_main_entrypoint() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    assert "uvicorn" in dockerfile
    assert "transcendence_memory.backend.main:app" in dockerfile


def test_dockerignore_excludes_local_runtime_noise() -> None:
    dockerignore = Path(".dockerignore").read_text(encoding="utf-8")
    assert ".venv" in dockerignore
    assert ".pytest_cache" in dockerignore
    assert "__pycache__" in dockerignore
