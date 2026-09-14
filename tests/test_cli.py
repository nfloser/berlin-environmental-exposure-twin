from berlin_exposure_twin.cli import _select_berlin_area_station


def test_dwd_smoke_station_selection_uses_coordinates_not_state_label() -> None:
    stations = [
        {
            "station_id": "berlin-area",
            "latitude": 52.52,
            "longitude": 13.40,
            "name": "Berlin area",
            "state": "Brandenburg",
        },
        {
            "station_id": "misleading-label",
            "latitude": 53.55,
            "longitude": 10.00,
            "name": "Far away",
            "state": "Berlin",
        },
    ]

    station, method = _select_berlin_area_station(stations)

    assert station["station_id"] == "berlin-area"
    assert method == "inside_berlin_analysis_bounds"


def test_dwd_smoke_station_selection_falls_back_to_nearest_station() -> None:
    stations = [
        {
            "station_id": "near",
            "latitude": 52.75,
            "longitude": 13.45,
            "name": "Near Berlin",
            "state": "Brandenburg",
        },
        {
            "station_id": "far",
            "latitude": 50.11,
            "longitude": 8.68,
            "name": "Far away",
            "state": "Hessen",
        },
    ]

    station, method = _select_berlin_area_station(stations)

    assert station["station_id"] == "near"
    assert method == "nearest_to_berlin_center"
