from pathlib import Path


def test_root_readme_has_release_sections() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "Scope" in readme
    assert "Boundaries" in readme
    assert "same-machine" in readme
    assert "split-machine" in readme
    assert "operator-identity.md" in readme
    assert "Identity First" in readme
    assert "License" in readme


def test_license_exists_with_mit_language() -> None:
    license_text = Path("LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in license_text


def test_runbook_set_exists() -> None:
    assert Path("docs/backend-deploy.md").exists()
    assert Path("docs/frontend-handoff.md").exists()
    assert Path("docs/authentication.md").exists()
    assert Path("docs/troubleshooting.md").exists()
    assert Path("docs/guide/HUMAN_GUIDE_INDEX.md").exists()
    assert Path("docs/guide/INDEX.md").exists()
    assert Path("docs/guide/installation.md").exists()
    assert Path("docs/guide/backend-deployment.md").exists()
    assert Path("docs/guide/frontend-handoff.md").exists()
    assert Path("docs/guide/auth-handoff.md").exists()


def test_runbooks_reference_real_commands() -> None:
    backend = Path("docs/backend-deploy.md").read_text(encoding="utf-8")
    handoff = Path("docs/frontend-handoff.md").read_text(encoding="utf-8")
    guide_human = Path("docs/guide/HUMAN_GUIDE_INDEX.md").read_text(encoding="utf-8")
    guide_install = Path("docs/guide/installation.md").read_text(encoding="utf-8")
    guide_backend = Path("docs/guide/backend-deployment.md").read_text(encoding="utf-8")
    guide_frontend = Path("docs/guide/frontend-handoff.md").read_text(encoding="utf-8")
    guide_auth = Path("docs/guide/auth-handoff.md").read_text(encoding="utf-8")
    assert "backend deploy" in backend
    assert "backend 身份" in backend
    assert "frontend import-connection" in handoff
    assert "frontend 身份" in handoff
    assert "Start Here" in guide_human
    assert "./scripts/bootstrap_dev.sh" in guide_install
    assert "backend export-connection" in guide_backend
    assert "frontend import-connection" in guide_frontend
    assert "auth set-api-key" in guide_auth
    assert "auth login" in Path("docs/authentication.md").read_text(encoding="utf-8")
    assert "backend health" in Path("docs/troubleshooting.md").read_text(encoding="utf-8")
