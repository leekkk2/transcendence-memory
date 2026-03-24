import os

import pytest
from sqlalchemy import text

from transcendence_memory.backend.db.session import create_engine_from_settings
from transcendence_memory.backend.settings import BackendSettings


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
