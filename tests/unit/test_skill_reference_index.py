from pathlib import Path


def test_skill_references_operator_surface() -> None:
    text = Path("transcendence-memory/SKILL.md").read_text(encoding="utf-8")
    assert "references/setup.md" in text
    assert "references/ARCHITECTURE.md" in text
    assert "references/DATAFLOW.md" in text
    assert "references/OPERATIONS.md" in text
    assert "references/VETTING_REPORT.md" in text
    assert "public-safe" in text


def test_skill_references_identity_rules() -> None:
    text = Path("transcendence-memory/SKILL.md").read_text(encoding="utf-8")
    assert "references/identity-rules.md" in text
    assert "identity-frontend.md" in text
    assert "identity-backend.md" in text
    assert "identity-both.md" in text
    assert "operator-identity.md" in text
