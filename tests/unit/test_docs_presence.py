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


def test_runbook_set_exists() -> None:
    assert Path("docs/backend-deploy.md").exists()
    assert Path("docs/frontend-handoff.md").exists()
    assert Path("docs/authentication.md").exists()
    assert Path("docs/troubleshooting.md").exists()


def test_runbooks_reference_real_commands() -> None:
    assert "backend deploy" in Path("docs/backend-deploy.md").read_text(encoding="utf-8")
    assert "frontend import-connection" in Path("docs/frontend-handoff.md").read_text(encoding="utf-8")
    assert "auth login" in Path("docs/authentication.md").read_text(encoding="utf-8")
    assert "backend health" in Path("docs/troubleshooting.md").read_text(encoding="utf-8")
