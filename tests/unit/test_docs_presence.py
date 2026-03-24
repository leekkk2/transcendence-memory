from pathlib import Path


def test_root_readme_has_release_sections() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "memory-lancedb-pro" in readme
    assert "same-machine" in readme
    assert "split-machine" in readme
    assert "License" in readme


def test_license_exists_with_mit_language() -> None:
    license_text = Path("LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in license_text
