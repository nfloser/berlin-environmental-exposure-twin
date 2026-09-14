from datetime import UTC, datetime

import httpx

from berlin_exposure_twin.models import Pollutant
from berlin_exposure_twin.providers.berlin_air import BerlinAirQualityClient


def test_station_parser_respects_component_availability() -> None:
    station = BerlinAirQualityClient.parse_station(
        {
            "code": "mc999",
            "name": "Synthetic Station",
            "lat": "52.5",
            "lng": "13.4",
            "active": True,
            "stationgroups": ["background"],
            "activeComponents": ["no2_1h", "pm10_1h"],
        }
    )
    assert station.available_pollutants == {Pollutant.NO2, Pollutant.PM10}


def test_missing_measurement_is_not_fabricated() -> None:
    item = {
        "datetime": "2026-01-01T12:00:00+01:00",
        "station": "mc999",
        "core": "no2",
        "component": "no2_1h",
        "period": "1h",
        "value": None,
    }
    assert BerlinAirQualityClient.parse_observation(item, retrieved_at=datetime.now(UTC)) is None


def test_client_maps_real_shaped_payload_to_canonical_model() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/stations/mc027/data"):
            return httpx.Response(
                200,
                json=[
                    {
                        "datetime": "2023-10-25T00:00:00+02:00",
                        "station": "mc027",
                        "core": "no2",
                        "component": "no2_24h",
                        "period": "24h",
                        "value": 12,
                    }
                ],
            )
        return httpx.Response(404)

    client = BerlinAirQualityClient(transport=httpx.MockTransport(handler))
    values = client.observations("mc027", Pollutant.NO2)
    client.close()
    assert values[0].timestamp.tzinfo == UTC
    assert values[0].state.value == "observed"
    assert values[0].value == 12
