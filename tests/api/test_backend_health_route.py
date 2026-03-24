from fastapi.testclient import TestClient

from transcendence_memory.backend.app import create_app


def test_backend_health_route_reports_database_and_provider() -> None:
    client = TestClient(create_app())
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert "database" in payload
    assert "provider_config" in payload
    assert "deployment" in payload
