from pathlib import Path

from transcendence_memory.bootstrap.paths import resolve_paths


def test_linux_paths_use_xdg_convention() -> None:
    paths = resolve_paths(platform_name="Linux", home=Path("/tmp/test-home"))
    assert str(paths.config_root).endswith(".config/transcendence-memory")
    assert str(paths.secret_root).endswith(".config/transcendence-memory/secrets")


def test_macos_paths_use_application_support() -> None:
    paths = resolve_paths(platform_name="Darwin", home=Path("/tmp/test-home"))
    assert "Application Support/transcendence-memory" in str(paths.config_root)


def test_windows_paths_use_appdata() -> None:
    appdata = Path("/tmp/AppData/Roaming")
    paths = resolve_paths(platform_name="Windows", appdata=appdata)
    assert "AppData/Roaming/transcendence-memory" in str(paths.config_root)
