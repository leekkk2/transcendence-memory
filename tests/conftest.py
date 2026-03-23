from pathlib import Path

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def bootstrap_roots(tmp_path: Path) -> dict[str, Path]:
    return {
        "config_root": tmp_path / "config-root",
        "secret_root": tmp_path / "secret-root",
    }
