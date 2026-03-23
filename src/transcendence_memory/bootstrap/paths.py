from __future__ import annotations

import os
import platform
from pathlib import Path

from platformdirs import PlatformDirs

from .models import ResolvedPaths


APP_NAME = "transcendence-memory"


def _expand(path: str | Path | None) -> Path | None:
    if path is None:
        return None
    return Path(path).expanduser().resolve()


def _platform_config_root(
    platform_name: str | None = None,
    home: Path | None = None,
    appdata: Path | None = None,
) -> Path:
    normalized = (platform_name or platform.system()).lower()
    home_dir = home or Path.home()

    if normalized == "darwin":
        return home_dir / "Library" / "Application Support" / APP_NAME
    if normalized == "windows":
        return (appdata or Path(os.environ.get("APPDATA", home_dir / "AppData" / "Roaming"))) / APP_NAME
    if normalized == "linux":
        xdg = os.environ.get("XDG_CONFIG_HOME")
        return Path(xdg) / APP_NAME if xdg else home_dir / ".config" / APP_NAME

    dirs = PlatformDirs(appname=APP_NAME, appauthor=False)
    return Path(dirs.user_config_dir)


def _platform_secret_root(
    platform_name: str | None = None,
    home: Path | None = None,
    appdata: Path | None = None,
) -> Path:
    return _platform_config_root(platform_name=platform_name, home=home, appdata=appdata) / "secrets"


def resolve_paths(
    config_path: str | Path | None = None,
    secret_path: str | Path | None = None,
    *,
    platform_name: str | None = None,
    home: Path | None = None,
    appdata: Path | None = None,
) -> ResolvedPaths:
    config_root = _expand(config_path) or _platform_config_root(
        platform_name=platform_name,
        home=home,
        appdata=appdata,
    )
    secret_root = _expand(secret_path) or _platform_secret_root(
        platform_name=platform_name,
        home=home,
        appdata=appdata,
    )
    return ResolvedPaths(
        config_root=config_root,
        secret_root=secret_root,
        config_file=config_root / "config.toml",
        secret_file=secret_root / "secrets.toml",
        state_file=config_root / "state.json",
    )


def ensure_layout(paths: ResolvedPaths) -> None:
    paths.config_root.mkdir(parents=True, exist_ok=True)
    paths.secret_root.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(paths.secret_root, 0o700)


def ensure_secret_permissions(secret_file: Path) -> None:
    if os.name != "nt" and secret_file.exists():
        os.chmod(secret_file, 0o600)


def is_writable(path: Path) -> bool:
    candidate = path
    if candidate.suffix:
        candidate = candidate.parent
    candidate.mkdir(parents=True, exist_ok=True)
    probe = candidate / ".tm_write_probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False
