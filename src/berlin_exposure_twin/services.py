from __future__ import annotations

from datetime import datetime

from berlin_exposure_twin.analytics import (
    estimate_location,
    spatial_mean_exposure,
    time_weighted_exposure,
)
from berlin_exposure_twin.geo import densify_trajectory
from berlin_exposure_twin.models import ExposureResult, ExposureSample, Pollutant, Trajectory
from berlin_exposure_twin.providers.base import AirQualityProvider


class ExposureService:
    def __init__(self, provider: AirQualityProvider) -> None:
        self.provider = provider

    def estimate_location(
        self,
        *,
        pollutant: Pollutant,
        latitude: float,
        longitude: float,
        timestamp: datetime,
        method: str = "idw",
        max_observation_age_seconds: float = 7200.0,
    ):
        stations = {
            station.id: station
            for station in self.provider.stations(active_only=True)
            if pollutant in station.available_pollutants
        }
        observations = []
        for station_id in stations:
            station_observations = self.provider.observations(station_id, pollutant)
            if not station_observations:
                continue
            nearest = min(
                station_observations,
                key=lambda observation: abs((observation.timestamp - timestamp).total_seconds()),
            )
            if abs((nearest.timestamp - timestamp).total_seconds()) <= max_observation_age_seconds:
                observations.append(nearest)
        return estimate_location(
            pollutant=pollutant,
            timestamp=timestamp,
            latitude=latitude,
            longitude=longitude,
            observations=observations,
            stations=stations,
            method=method,
        )

    def estimate_route(self, *, pollutant: Pollutant, trajectory: Trajectory) -> ExposureResult:
        dense = densify_trajectory(trajectory, max_step_m=250.0)
        samples: list[ExposureSample] = []
        for point in dense.points:
            if point.timestamp is None:
                raise ValueError(
                    "Untimestamped routes require explicit snapshot time via the API; "
                    "travel speed is never invented"
                )
            estimate = self.estimate_location(
                pollutant=pollutant,
                latitude=point.latitude,
                longitude=point.longitude,
                timestamp=point.timestamp,
            )
            samples.append(
                ExposureSample(
                    timestamp=point.timestamp,
                    latitude=point.latitude,
                    longitude=point.longitude,
                    concentration=estimate.value,
                    state=estimate.state,
                    uncertainty=estimate.uncertainty,
                )
            )
        return time_weighted_exposure(pollutant, samples)

    def compare_route_spatially(
        self, *, pollutant: Pollutant, trajectory: Trajectory, snapshot_time: datetime
    ) -> ExposureResult:
        dense = densify_trajectory(trajectory, max_step_m=250.0)
        samples: list[ExposureSample] = []
        for point in dense.points:
            estimate = self.estimate_location(
                pollutant=pollutant,
                latitude=point.latitude,
                longitude=point.longitude,
                timestamp=snapshot_time,
            )
            samples.append(
                ExposureSample(
                    latitude=point.latitude,
                    longitude=point.longitude,
                    concentration=estimate.value,
                    state=estimate.state,
                    uncertainty=estimate.uncertainty,
                )
            )
        return spatial_mean_exposure(pollutant, samples)
