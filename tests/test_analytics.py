from datetime import UTC, datetime, timedelta

import pytest

from berlin_exposure_twin.analytics import (
    estimate_location,
    leave_one_station_out_validation,
    time_weighted_exposure,
)
from berlin_exposure_twin.models import (
    DataSource,
    EnvironmentalObservation,
    ExposureSample,
    MonitoringStation,
    Pollutant,
    Provenance,
    UncertaintyIndicators,
)

SOURCE = DataSource(provider="TEST", dataset="synthetic", reference="test://synthetic")
PROV = Provenance(source=SOURCE, retrieved_at=datetime(2026, 1, 1, tzinfo=UTC))


def _station(station_id: str, lat: float, lon: float) -> MonitoringStation:
    return MonitoringStation(
        id=station_id,
        name=station_id,
        latitude=lat,
        longitude=lon,
        active=True,
        available_pollutants={Pollutant.NO2},
        source=SOURCE,
    )


def _obs(station_id: str, value: float) -> EnvironmentalObservation:
    return EnvironmentalObservation(
        station_id=station_id,
        pollutant=Pollutant.NO2,
        timestamp=datetime(2026, 1, 1, 12, tzinfo=UTC),
        value=value,
        unit="µg/m³",
        provenance=PROV,
    )


def test_idw_midpoint_between_equal_distance_stations_is_mean() -> None:
    stations = {"a": _station("a", 52.5, 13.39), "b": _station("b", 52.5, 13.41)}
    result = estimate_location(
        pollutant=Pollutant.NO2,
        timestamp=datetime(2026, 1, 1, 12, tzinfo=UTC),
        latitude=52.5,
        longitude=13.4,
        observations=[_obs("a", 10), _obs("b", 30)],
        stations=stations,
    )
    assert result.value == pytest.approx(20.0, rel=1e-3)
    assert result.state.value == "interpolated"
    assert result.uncertainty.contributing_stations == 2


def test_observation_at_station_is_not_labelled_interpolated() -> None:
    station = _station("a", 52.5, 13.4)
    result = estimate_location(
        pollutant=Pollutant.NO2,
        timestamp=datetime(2026, 1, 1, 12, tzinfo=UTC),
        latitude=52.5,
        longitude=13.4,
        observations=[_obs("a", 17)],
        stations={"a": station},
    )
    assert result.state.value == "observed"
    assert result.method == "station_observation"


def test_time_weighted_exposure_uses_trapezoidal_integration() -> None:
    t0 = datetime(2026, 1, 1, 12, tzinfo=UTC)
    uncertainty = UncertaintyIndicators(contributing_stations=1)
    samples = [
        ExposureSample(
            timestamp=t0,
            latitude=52.5,
            longitude=13.4,
            concentration=10,
            state="interpolated",
            uncertainty=uncertainty,
        ),
        ExposureSample(
            timestamp=t0 + timedelta(hours=1),
            latitude=52.51,
            longitude=13.41,
            concentration=30,
            state="interpolated",
            uncertainty=uncertainty,
        ),
    ]
    result = time_weighted_exposure(Pollutant.NO2, samples)
    assert result.value == pytest.approx(20)
    assert result.duration_seconds == 3600


def test_loso_validation_never_uses_held_out_station() -> None:
    stations = {
        "a": _station("a", 52.5, 13.39),
        "b": _station("b", 52.5, 13.40),
        "c": _station("c", 52.5, 13.41),
    }
    metrics = leave_one_station_out_validation(
        pollutant=Pollutant.NO2,
        timestamp=datetime(2026, 1, 1, 12, tzinfo=UTC),
        observations=[_obs("a", 10), _obs("b", 20), _obs("c", 30)],
        stations=stations,
    )
    assert metrics["n"] == 3
    assert metrics["mae"] is not None
    assert metrics["rmse"] is not None
