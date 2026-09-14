from __future__ import annotations

from datetime import UTC, datetime
from math import isfinite, sqrt
from statistics import mean

from berlin_exposure_twin.geo import haversine_m
from berlin_exposure_twin.models import (
    DataState,
    EnvironmentalFieldEstimate,
    EnvironmentalObservation,
    ExposureResult,
    ExposureSample,
    MonitoringStation,
    Pollutant,
    Provenance,
    UncertaintyIndicators,
)
from berlin_exposure_twin.units import concentration_to_ug_m3


def _valid_pairs(
    observations: list[EnvironmentalObservation], stations: dict[str, MonitoringStation]
) -> list[tuple[EnvironmentalObservation, MonitoringStation]]:
    return [(obs, stations[obs.station_id]) for obs in observations if obs.station_id in stations]


def estimate_location(
    *,
    pollutant: Pollutant,
    timestamp: datetime,
    latitude: float,
    longitude: float,
    observations: list[EnvironmentalObservation],
    stations: dict[str, MonitoringStation],
    method: str = "idw",
    power: float = 2.0,
    max_stations: int = 4,
) -> EnvironmentalFieldEstimate:
    candidates = _valid_pairs(observations, stations)
    if not candidates:
        return EnvironmentalFieldEstimate(
            pollutant=pollutant,
            timestamp=timestamp,
            latitude=latitude,
            longitude=longitude,
            value=None,
            state=DataState.INTERPOLATED,
            method="idw" if method == "idw" else "nearest_station",
            uncertainty=UncertaintyIndicators(missing=True),
            contributing_station_ids=[],
            provenance=[],
        )
    ranked = sorted(
        ((haversine_m(latitude, longitude, s.latitude, s.longitude), o, s) for o, s in candidates),
        key=lambda item: item[0],
    )
    nearest_distance, nearest_obs, nearest_station = ranked[0]
    age = abs((timestamp - nearest_obs.timestamp).total_seconds())
    if nearest_distance < 1.0:
        value = concentration_to_ug_m3(nearest_obs.value, nearest_obs.unit)
        return EnvironmentalFieldEstimate(
            pollutant=pollutant,
            timestamp=timestamp,
            latitude=latitude,
            longitude=longitude,
            value=value,
            state=DataState.OBSERVED,
            method="station_observation",
            uncertainty=UncertaintyIndicators(
                nearest_station_m=nearest_distance,
                contributing_stations=1,
                observation_age_seconds=age,
            ),
            contributing_station_ids=[nearest_station.id],
            provenance=[nearest_obs.provenance],
        )
    if method == "nearest_station":
        value = concentration_to_ug_m3(nearest_obs.value, nearest_obs.unit)
        return EnvironmentalFieldEstimate(
            pollutant=pollutant,
            timestamp=timestamp,
            latitude=latitude,
            longitude=longitude,
            value=value,
            state=DataState.INTERPOLATED,
            method="nearest_station",
            uncertainty=UncertaintyIndicators(
                nearest_station_m=nearest_distance,
                contributing_stations=1,
                observation_age_seconds=age,
            ),
            contributing_station_ids=[nearest_station.id],
            provenance=[nearest_obs.provenance],
        )
    if method != "idw":
        raise ValueError(f"Unsupported spatial estimation method: {method}")
    selected = ranked[:max_stations]
    weighted_sum = 0.0
    weight_total = 0.0
    provenances: list[Provenance] = []
    ids: list[str] = []
    ages: list[float] = []
    for distance, obs, station in selected:
        safe_distance = max(distance, 1.0)
        weight = 1.0 / (safe_distance**power)
        weighted_sum += concentration_to_ug_m3(obs.value, obs.unit) * weight
        weight_total += weight
        ids.append(station.id)
        provenances.append(obs.provenance)
        ages.append(abs((timestamp - obs.timestamp).total_seconds()))
    value = weighted_sum / weight_total
    if not isfinite(value):
        raise ValueError("IDW produced a non-finite value")
    return EnvironmentalFieldEstimate(
        pollutant=pollutant,
        timestamp=timestamp,
        latitude=latitude,
        longitude=longitude,
        value=value,
        state=DataState.INTERPOLATED,
        method="idw",
        uncertainty=UncertaintyIndicators(
            nearest_station_m=nearest_distance,
            contributing_stations=len(selected),
            observation_age_seconds=max(ages),
        ),
        contributing_station_ids=ids,
        provenance=provenances,
    )


def time_weighted_exposure(pollutant: Pollutant, samples: list[ExposureSample]) -> ExposureResult:
    if len(samples) < 2:
        raise ValueError("At least two timestamped samples are required")
    if any(sample.timestamp is None for sample in samples):
        raise ValueError("Time-weighted exposure requires timestamps for every sample")
    weighted = 0.0
    duration = 0.0
    for left, right in zip(samples, samples[1:], strict=False):
        assert left.timestamp is not None and right.timestamp is not None
        dt = (right.timestamp - left.timestamp).total_seconds()
        if dt <= 0:
            raise ValueError("Sample timestamps must be strictly increasing")
        if left.concentration is None or right.concentration is None:
            continue
        weighted += ((left.concentration + right.concentration) / 2.0) * dt
        duration += dt
    value = weighted / duration if duration else None
    return ExposureResult(
        pollutant=pollutant,
        metric="time_weighted_mean",
        value=value,
        duration_seconds=duration or None,
        method="trapezoidal time integration of concentration samples",
        state=DataState.DERIVED,
        samples=samples,
        provenance=[],
    )


def spatial_mean_exposure(pollutant: Pollutant, samples: list[ExposureSample]) -> ExposureResult:
    values = [sample.concentration for sample in samples if sample.concentration is not None]
    return ExposureResult(
        pollutant=pollutant,
        metric="spatial_mean",
        value=mean(values) if values else None,
        duration_seconds=None,
        method="arithmetic mean of spatial concentration samples; not a time exposure",
        state=DataState.DERIVED,
        samples=samples,
        provenance=[],
    )


def leave_one_station_out_validation(
    *,
    pollutant: Pollutant,
    timestamp: datetime,
    observations: list[EnvironmentalObservation],
    stations: dict[str, MonitoringStation],
    method: str = "idw",
) -> dict[str, float | int | None]:
    errors: list[float] = []
    squared_errors: list[float] = []
    by_station = {obs.station_id: obs for obs in observations if obs.station_id in stations}
    for held_out_id, held_out in by_station.items():
        training = [obs for station_id, obs in by_station.items() if station_id != held_out_id]
        if not training:
            continue
        target_station = stations[held_out_id]
        estimate = estimate_location(
            pollutant=pollutant,
            timestamp=timestamp,
            latitude=target_station.latitude,
            longitude=target_station.longitude,
            observations=training,
            stations={key: value for key, value in stations.items() if key != held_out_id},
            method=method,
        )
        if estimate.value is None:
            continue
        truth = concentration_to_ug_m3(held_out.value, held_out.unit)
        error = estimate.value - truth
        errors.append(abs(error))
        squared_errors.append(error * error)
    return {
        "n": len(errors),
        "mae": mean(errors) if errors else None,
        "rmse": sqrt(mean(squared_errors)) if squared_errors else None,
    }


def utc_now() -> datetime:
    return datetime.now(UTC)
