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


def test_location_rejects_naive_timestamp() -> None:
    response = client.get(
        "/api/v1/exposure/location",
        params={
            "latitude": 52.5,
            "longitude": 13.4,
            "pollutant": "no2",
            "timestamp": "2026-01-01T12:00:00",
        },
    )
    assert response.status_code == 422


def test_route_rejects_naive_snapshot_time() -> None:
    response = client.post(
        "/api/v1/exposure/route",
        json={
            "pollutant": "no2",
            "trajectory": {
                "crs": "EPSG:4326",
                "points": [
                    {"longitude": 13.4, "latitude": 52.5},
                    {"longitude": 13.41, "latitude": 52.5},
                ],
            },
            "snapshot_time": "2026-01-01T12:00:00",
        },
    )
    assert response.status_code == 422
