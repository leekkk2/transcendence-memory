from pathlib import Path


def test_skill_references_operator_surface() -> None:
    text = Path("transcendence-memory/SKILL.md").read_text(encoding="utf-8")
    assert "references/setup.md" in text
    assert "references/ARCHITECTURE.md" in text
    assert "references/DATAFLOW.md" in text
    assert "references/OPERATIONS.md" in text
    assert "references/VETTING_REPORT.md" in text
    assert "public-safe" in text
