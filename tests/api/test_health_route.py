from fastapi.testclient import TestClient

from transcendence_memory.backend.app import create_app


def test_health_route_reports_auth_mode() -> None:
    client = TestClient(create_app())
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "auth_mode" in payload
