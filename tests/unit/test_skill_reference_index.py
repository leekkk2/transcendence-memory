from pathlib import Path


def test_skill_references_migration_surface() -> None:
    text = Path("transcendence-memory/SKILL.md").read_text(encoding="utf-8")
    assert "rag-everything-enhancer" in text
    assert "setup-migration" in text
    assert "architecture-migration" in text
    assert "dataflow-migration" in text
    assert "operations-migration" in text
    assert "safety-migration" in text
