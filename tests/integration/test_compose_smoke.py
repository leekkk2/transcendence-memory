import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which("docker") is None, reason="docker is required for compose smoke validation")
def test_compose_config_is_valid() -> None:
    env_target = Path("deploy/docker/backend.env")
    env_example = Path("deploy/docker/backend.env.example")
    if not env_target.exists():
        env_target.write_text(env_example.read_text(encoding="utf-8"), encoding="utf-8")

    result = subprocess.run(
        ["docker", "compose", "config"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "backend" in result.stdout
    assert "postgres" in result.stdout
