import json
from pathlib import Path

from transcendence_memory import __version__
from transcendence_memory.handoff.models import BUNDLE_VERSION


def test_release_compatibility_manifest_exists_and_has_versions() -> None:
    payload = json.loads(Path("compat/release-compatibility.json").read_text(encoding="utf-8"))
    assert payload["cli_version"]
    assert payload["backend_version"]
    assert payload["skill_version"]
    assert payload["bundle_version"]


def test_release_compatibility_matches_current_versions() -> None:
    payload = json.loads(Path("compat/release-compatibility.json").read_text(encoding="utf-8"))
    assert payload["cli_version"] == __version__
    assert payload["backend_version"] == __version__
    assert payload["bundle_version"] == BUNDLE_VERSION
    assert payload["skill_version"] == "0.1.0"
