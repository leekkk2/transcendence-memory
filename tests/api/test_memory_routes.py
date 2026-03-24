from types import SimpleNamespace

from fastapi.testclient import TestClient

from transcendence_memory.backend.app import create_app
from transcendence_memory.bootstrap.models import BootstrapSecrets


def test_memory_routes_require_auth(monkeypatch) -> None:
    app = create_app()
    app.state.runtime_config.bootstrap_secrets = BootstrapSecrets(api_key="secret")
    client = TestClient(app)
    response = client.post("/api/v1/memory/search", json={"query": "hello", "limit": 3})
    assert response.status_code == 401


def test_memory_routes_return_results(monkeypatch) -> None:
    app = create_app()
    app.state.runtime_config.bootstrap_secrets = BootstrapSecrets(api_key="secret")
    client = TestClient(app)

    class DummySession:
        def close(self):
            return None

    monkeypatch.setattr(
        "transcendence_memory.backend.api.routes.memory.create_session_factory",
        lambda settings: (lambda: DummySession()),
    )
    monkeypatch.setattr(
        "transcendence_memory.backend.api.routes.memory.search_content",
        lambda runtime, session, query, limit=5: [
            {
                "id": "record-1",
                "content": "hello world",
                "metadata": {"topic": "greeting"},
                "provider": "openai",
                "model": "text-embedding-3-small",
                "score": 0.01,
            }
        ],
    )

    response = client.post(
        "/api/v1/memory/search",
        headers={"X-Transcendence-API-Key": "secret"},
        json={"query": "hello", "limit": 3},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["score"] == 0.01
