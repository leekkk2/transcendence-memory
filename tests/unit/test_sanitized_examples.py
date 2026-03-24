from pathlib import Path


def test_sanitized_examples_keep_shape() -> None:
    config = Path("docs/examples/rag-config.example.json").read_text(encoding="utf-8")
    env = Path("docs/examples/env.snippet").read_text(encoding="utf-8")
    loader = Path("docs/examples/load_rag_config.sh").read_text(encoding="utf-8")
    skill_config = Path("transcendence-memory/references/rag-config.example.json").read_text(encoding="utf-8")
    skill_env = Path("transcendence-memory/references/env.snippet").read_text(encoding="utf-8")
    assert "defaultContainer" in config
    assert "X-API-KEY" in config
    assert "RAG_CONFIG_FILE" in env
    assert "RAG_DEFAULT_CONTAINER" in loader
    assert "defaultContainer" in skill_config
    assert "EMBEDDING_API_KEY" in skill_env


def test_sanitized_examples_do_not_reintroduce_private_values() -> None:
    texts = [
        Path("docs/examples/rag-config.example.json").read_text(encoding="utf-8"),
        Path("docs/examples/env.snippet").read_text(encoding="utf-8"),
        Path("docs/examples/load_rag_config.sh").read_text(encoding="utf-8"),
        Path("transcendence-memory/references/rag-config.example.json").read_text(encoding="utf-8"),
        Path("transcendence-memory/references/env.snippet").read_text(encoding="utf-8"),
    ]
    merged = "\n".join(texts)
    assert "rag.zweiteng.tk" not in merged
    assert "sk-M50CPBnjq0dZeTgRPquuzKMesJQRoUSA7uQc81am56TPkDQt" not in merged
    assert "/Users/" not in merged
