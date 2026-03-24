from pathlib import Path

import pytest
from typer.testing import CliRunner

from transcendence_memory.backend.settings import load_runtime_config


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def temp_config_root(tmp_path: Path) -> Path:
    return tmp_path / "config-root"


@pytest.fixture
def temp_secret_root(tmp_path: Path) -> Path:
    return tmp_path / "secret-root"


@pytest.fixture
def bootstrap_roots(temp_config_root: Path, temp_secret_root: Path) -> dict[str, Path]:
    return {
        "config_root": temp_config_root,
        "secret_root": temp_secret_root,
    }


@pytest.fixture
def patched_bootstrap_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Path]:
    home = tmp_path / "home"
    appdata = home / "AppData" / "Roaming"
    xdg_config_home = home / ".config"
    for path in (home, appdata, xdg_config_home):
        path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config_home))

    return {
        "home": home,
        "appdata": appdata,
        "xdg_config_home": xdg_config_home,
    }


@pytest.fixture
def runtime_config(bootstrap_roots: dict[str, Path]):
    return load_runtime_config(
        config_path=bootstrap_roots["config_root"],
        secret_path=bootstrap_roots["secret_root"],
    )
