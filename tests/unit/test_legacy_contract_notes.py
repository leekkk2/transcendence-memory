import json
from pathlib import Path


def test_migration_compatibility_categories_exist() -> None:
    payload = json.loads(Path("compat/migration-compatibility.json").read_text(encoding="utf-8"))
    compat = payload["compatibility"]
    assert compat["frontend_backend_split"] == "preserved"
    assert compat["container_namespace_behavior"] == "adapted"
    assert compat["lancedb_backend_assumption"] == "not_migrated"


def test_private_values_do_not_reappear_in_migration_artifacts() -> None:
    texts = [
        Path("compat/migration-compatibility.json").read_text(encoding="utf-8"),
        Path("docs/migration/release-impact.md").read_text(encoding="utf-8"),
        Path("docs/examples/rag-config.example.json").read_text(encoding="utf-8"),
    ]
    merged = "\n".join(texts)
    assert "rag.zweiteng.tk" not in merged
    assert "sk-M50CPBnjq0dZeTgRPquuzKMesJQRoUSA7uQc81am56TPkDQt" not in merged
    assert "/Users/" not in merged
