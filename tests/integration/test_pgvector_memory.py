import os

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from transcendence_memory.backend.db.models import MemoryRecord
from transcendence_memory.backend.db.session import create_engine_from_settings
from transcendence_memory.backend.settings import BackendSettings
from transcendence_memory.backend.services import memory as memory_service


@pytest.mark.skipif(
    "TEST_DATABASE_URL" not in os.environ,
    reason="TEST_DATABASE_URL is required for PostgreSQL + pgvector integration coverage.",
)
def test_pgvector_memory_roundtrip() -> None:
    settings = BackendSettings(
        database_url=os.environ["TEST_DATABASE_URL"],
        config_path="/tmp/config",
        secret_path="/tmp/secret",
    )
    engine = create_engine_from_settings(settings)
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


@pytest.mark.skipif(
    "TEST_DATABASE_URL" not in os.environ,
    reason="TEST_DATABASE_URL is required for PostgreSQL + pgvector integration coverage.",
)
def test_pgvector_search_service(monkeypatch) -> None:
    settings = BackendSettings(
        database_url=os.environ["TEST_DATABASE_URL"],
        config_path="/tmp/config",
        secret_path="/tmp/secret",
    )
    engine = create_engine_from_settings(settings)
    with Session(engine) as session:
        monkeypatch.setattr(
            "transcendence_memory.backend.services.memory.generate_embedding",
            lambda runtime, text: [0.1] * 1536 if text == "source" else [0.1] * 1536,
        )
        runtime = type("Runtime", (), {"settings": settings})()
        record = memory_service.embed_content(runtime, session, content="source", metadata={"kind": "test"})
        assert isinstance(record, MemoryRecord)
        results = memory_service.search_content(runtime, session, query="source", limit=1)
        assert results
        assert results[0]["id"] == record.id
