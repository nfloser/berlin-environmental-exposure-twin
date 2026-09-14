from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

import httpx

from berlin_exposure_twin.models import (
    DataSource,
    EnvironmentalObservation,
    MonitoringStation,
    Pollutant,
    Provenance,
    QualityFlag,
)

SOURCE = DataSource(
    provider="Berliner Luftgütemessnetz",
    dataset="Luftgütemessdaten Berlin REST API",
    reference="https://luftdaten.berlin.de/api/doc",
    licence="Datenlizenz Deutschland – Namensnennung – Version 2.0 (dl-de-by-2.0)",
)

_CORE_TO_POLLUTANT = {
    "no2": Pollutant.NO2,
    "pm10": Pollutant.PM10,
    "pm2": Pollutant.PM25,
    "o3": Pollutant.O3,
}
_POLLUTANT_TO_CORE = {value: key for key, value in _CORE_TO_POLLUTANT.items()}


class BerlinAirQualityClient:
    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        resolved_base = base_url or os.getenv(
            "BERLIN_AIR_API_BASE", "https://luftdaten.berlin.de/api"
        )
        self._client = httpx.Client(base_url=resolved_base, timeout=timeout, transport=transport)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> BerlinAirQualityClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @staticmethod
    def _pollutants_from_components(components: list[str]) -> set[Pollutant]:
        available: set[Pollutant] = set()
        for core, pollutant in _CORE_TO_POLLUTANT.items():
            if any(component.startswith(f"{core}_") for component in components):
                available.add(pollutant)
        return available

    def stations(self, *, active_only: bool = True) -> list[MonitoringStation]:
        response = self._client.get("/stations", params={"active": str(active_only).lower()})
        response.raise_for_status()
        payload = response.json()
        return [self.parse_station(item) for item in payload if not active_only or item.get("active")]

    @staticmethod
    def parse_station(item: dict[str, Any]) -> MonitoringStation:
        return MonitoringStation(
            id=str(item["code"]),
            name=str(item["name"]),
            latitude=float(item["lat"]),
            longitude=float(item["lng"]),
            active=bool(item.get("active", False)),
            station_type=(item.get("stationgroups") or [None])[0],
            available_pollutants=BerlinAirQualityClient._pollutants_from_components(
                list(item.get("activeComponents") or item.get("components") or [])
            ),
            source=SOURCE,
        )

    def observations(
        self, station_id: str, pollutant: Pollutant, *, timespan: str = "currentday"
    ) -> list[EnvironmentalObservation]:
        core = _POLLUTANT_TO_CORE[pollutant]
        response = self._client.get(
            f"/stations/{station_id}/data",
            params={"core": core, "period": "1h", "timespan": timespan},
        )
        response.raise_for_status()
        retrieved = datetime.now(UTC)
        observations: list[EnvironmentalObservation] = []
        for item in response.json():
            parsed = self.parse_observation(item, retrieved_at=retrieved)
            if parsed is not None and parsed.pollutant == pollutant:
                observations.append(parsed)
        return observations

    @staticmethod
    def parse_observation(
        item: dict[str, Any], *, retrieved_at: datetime
    ) -> EnvironmentalObservation | None:
        if item.get("value") is None:
            return None
        core = str(item["core"])
        pollutant = _CORE_TO_POLLUTANT.get(core)
        if pollutant is None:
            return None
        timestamp = datetime.fromisoformat(str(item["datetime"])).astimezone(UTC)
        return EnvironmentalObservation(
            station_id=str(item["station"]),
            pollutant=pollutant,
            timestamp=timestamp,
            value=float(item["value"]),
            unit="µg/m³",
            quality=QualityFlag.PROVISIONAL,
            provenance=Provenance(
                source=SOURCE,
                retrieved_at=retrieved_at,
                transformation_history=["parsed Berlin REST payload", "timestamp converted to UTC"],
            ),
        )
