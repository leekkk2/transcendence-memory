from pathlib import Path


def test_migration_contract_doc_exists_with_core_markers() -> None:
    text = Path("docs/migration/rag-everything-enhancer-contract.md").read_text(encoding="utf-8")
    assert "builtin memory" in text
    assert "defaultContainer" in text
    assert "X-API-KEY" in text


def test_source_vs_current_has_explicit_status_sections() -> None:
    text = Path("docs/migration/source-vs-current.md").read_text(encoding="utf-8")
    assert "Preserved" in text
    assert "Adapted" in text
    assert "Not Migrated" in text
