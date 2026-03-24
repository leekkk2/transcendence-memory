from pathlib import Path

import pytest
from typer.testing import CliRunner

from transcendence_memory.backend.settings import load_runtime_config


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def bootstrap_roots(tmp_path: Path) -> dict[str, Path]:
    return {
        "config_root": tmp_path / "config-root",
        "secret_root": tmp_path / "secret-root",
    }


@pytest.fixture
def runtime_config(bootstrap_roots):
    return load_runtime_config(
        config_path=bootstrap_roots["config_root"],
        secret_path=bootstrap_roots["secret_root"],
    )
