from fastapi.testclient import TestClient

from berlin_exposure_twin.api import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_exposes_versioned_route_contract() -> None:
    schema = client.get("/openapi.json").json()
    assert "/api/v1/exposure/route" in schema["paths"]
