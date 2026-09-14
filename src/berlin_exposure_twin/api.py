from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from berlin_exposure_twin.models import Pollutant, Trajectory
from berlin_exposure_twin.providers.berlin_air import SOURCE as BERLIN_SOURCE
from berlin_exposure_twin.providers.berlin_air import BerlinAirQualityClient
from berlin_exposure_twin.providers.dwd import SOURCE as DWD_SOURCE
from berlin_exposure_twin.providers.dwd import DWDClient, DWDVariable
from berlin_exposure_twin.services import ExposureService

app = FastAPI(
    title="Berlin Environmental Exposure Twin",
    version="0.1.0",
    description=(
        "Scientific environmental exposure API. Measured observations and spatial estimates are "
        "explicitly distinguished; no medical-risk classification is provided."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class RouteExposureRequest(BaseModel):
    pollutant: Pollutant
    trajectory: Trajectory
    snapshot_time: datetime | None = None


@lru_cache(maxsize=1)
def get_provider() -> BerlinAirQualityClient:
    return BerlinAirQualityClient()


@lru_cache(maxsize=1)
def get_dwd_provider() -> DWDClient:
    return DWDClient()


def get_service(provider: BerlinAirQualityClient = Depends(get_provider)) -> ExposureService:
    return ExposureService(provider)


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "berlin-environmental-exposure-twin"}


@app.get("/api/v1/sources")
def sources() -> list[dict[str, object]]:
    return [BERLIN_SOURCE.model_dump(mode="json"), DWD_SOURCE.model_dump(mode="json")]


@app.get("/api/v1/stations")
def stations(
    pollutant: Pollutant | None = None,
    provider: BerlinAirQualityClient = Depends(get_provider),
):
    values = provider.stations(active_only=True)
    if pollutant is not None:
        values = [station for station in values if pollutant in station.available_pollutants]
    return values


@app.get("/api/v1/observations")
def observations(
    station_id: str,
    pollutant: Pollutant,
    timespan: str = Query(default="currentday", pattern=r"^[A-Za-z0-9_-]+$"),
    provider: BerlinAirQualityClient = Depends(get_provider),
):
    try:
        return provider.observations(station_id, pollutant, timespan=timespan)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream source error: {exc}") from exc


@app.get("/api/v1/meteorology/stations")
def meteorology_stations(
    variable: DWDVariable = "air_temperature",
    provider: DWDClient = Depends(get_dwd_provider),
):
    try:
        return provider.stations(variable)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream DWD source error: {exc}") from exc


@app.get("/api/v1/meteorology/observations")
def meteorology_observations(
    station_id: str,
    variable: DWDVariable = "air_temperature",
    provider: DWDClient = Depends(get_dwd_provider),
):
    try:
        return provider.recent_observations(station_id, variable)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream DWD source error: {exc}") from exc


@app.get("/api/v1/environment/state")
def environment_state(
    latitude: float,
    longitude: float,
    pollutant: Pollutant,
    timestamp: datetime,
    method: Literal["idw", "nearest_station"] = "idw",
    service: ExposureService = Depends(get_service),
):
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise HTTPException(status_code=422, detail="timestamp must be timezone-aware")
    return service.estimate_location(
        pollutant=pollutant,
        latitude=latitude,
        longitude=longitude,
        timestamp=timestamp.astimezone(UTC),
        method=method,
    )


@app.get("/api/v1/exposure/location")
def exposure_location(
    latitude: float,
    longitude: float,
    pollutant: Pollutant,
    timestamp: datetime,
    service: ExposureService = Depends(get_service),
):
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise HTTPException(status_code=422, detail="timestamp must be timezone-aware")
    return service.estimate_location(
        pollutant=pollutant,
        latitude=latitude,
        longitude=longitude,
        timestamp=timestamp.astimezone(UTC),
    )


@app.post("/api/v1/exposure/route")
def exposure_route(request: RouteExposureRequest, service: ExposureService = Depends(get_service)):
    has_timestamps = all(point.timestamp is not None for point in request.trajectory.points)
    try:
        if has_timestamps:
            return service.estimate_route(pollutant=request.pollutant, trajectory=request.trajectory)
        if request.snapshot_time is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Untimestamped routes require snapshot_time. The API does not invent travel speed or timestamps."
                ),
            )
        if request.snapshot_time.tzinfo is None or request.snapshot_time.utcoffset() is None:
            raise HTTPException(status_code=422, detail="snapshot_time must be timezone-aware")
        return service.compare_route_spatially(
            pollutant=request.pollutant,
            trajectory=request.trajectory,
            snapshot_time=request.snapshot_time.astimezone(UTC),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/coverage")
def coverage(
    pollutant: Pollutant | None = None,
    provider: BerlinAirQualityClient = Depends(get_provider),
):
    values = provider.stations(active_only=True)
    if pollutant is not None:
        values = [station for station in values if pollutant in station.available_pollutants]
    return {
        "active_station_count": len(values),
        "pollutant": pollutant,
        "note": "Coverage describes monitoring availability, not street-level certainty.",
        "stations": values,
    }
