from __future__ import annotations

from typing import Protocol

from berlin_exposure_twin.models import EnvironmentalObservation, MonitoringStation, Pollutant


class AirQualityProvider(Protocol):
    def stations(self, *, active_only: bool = True) -> list[MonitoringStation]: ...

    def observations(
        self, station_id: str, pollutant: Pollutant, *, timespan: str = "currentday"
    ) -> list[EnvironmentalObservation]: ...
