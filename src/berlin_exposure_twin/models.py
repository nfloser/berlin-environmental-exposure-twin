from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class DataState(StrEnum):
    OBSERVED = "observed"
    INTERPOLATED = "interpolated"
    MODELLED = "modelled"
    DERIVED = "derived"
    SCENARIO = "scenario"


class Pollutant(StrEnum):
    NO2 = "no2"
    PM10 = "pm10"
    PM25 = "pm25"
    O3 = "o3"


class QualityFlag(StrEnum):
    VALID = "valid"
    PROVISIONAL = "provisional"
    MISSING = "missing"
    SUSPECT = "suspect"
    UNKNOWN = "unknown"


class DataSource(BaseModel):
    provider: str
    dataset: str
    reference: str
    licence: str | None = None


class Provenance(BaseModel):
    source: DataSource
    retrieved_at: datetime
    transformation_history: list[str] = Field(default_factory=list)
    method: str | None = None

    @field_validator("retrieved_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("retrieved_at must be timezone-aware")
        return value


class MonitoringStation(BaseModel):
    id: str
    name: str
    latitude: Annotated[float, Field(ge=-90, le=90)]
    longitude: Annotated[float, Field(ge=-180, le=180)]
    active: bool
    station_type: str | None = None
    available_pollutants: set[Pollutant] = Field(default_factory=set)
    source: DataSource


class EnvironmentalObservation(BaseModel):
    station_id: str
    pollutant: Pollutant
    timestamp: datetime
    value: float
    unit: Literal["µg/m³", "mg/m³"]
    state: Literal[DataState.OBSERVED] = DataState.OBSERVED
    quality: QualityFlag = QualityFlag.UNKNOWN
    provenance: Provenance

    @field_validator("timestamp")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value


class MeteorologicalObservation(BaseModel):
    station_id: str
    variable: Literal["air_temperature", "relative_humidity", "wind_speed", "wind_direction"]
    timestamp: datetime
    value: float
    unit: Literal["°C", "%", "m/s", "degree"]
    state: Literal[DataState.OBSERVED] = DataState.OBSERVED
    quality: QualityFlag = QualityFlag.UNKNOWN
    provenance: Provenance

    @field_validator("timestamp")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value


class UncertaintyIndicators(BaseModel):
    nearest_station_m: float | None = None
    contributing_stations: int = 0
    observation_age_seconds: float | None = None
    validation_mae: float | None = None
    missing: bool = False


class EnvironmentalFieldEstimate(BaseModel):
    pollutant: Pollutant
    timestamp: datetime
    latitude: float
    longitude: float
    value: float | None
    unit: Literal["µg/m³"] = "µg/m³"
    state: Literal[DataState.INTERPOLATED, DataState.OBSERVED]
    method: Literal["nearest_station", "idw", "station_observation"]
    uncertainty: UncertaintyIndicators
    contributing_station_ids: list[str]
    provenance: list[Provenance]


class ExposureSample(BaseModel):
    timestamp: datetime | None = None
    latitude: float
    longitude: float
    concentration: float | None
    unit: Literal["µg/m³"] = "µg/m³"
    state: DataState
    uncertainty: UncertaintyIndicators


class ExposureResult(BaseModel):
    pollutant: Pollutant
    metric: Literal["time_weighted_mean", "spatial_mean"]
    value: float | None
    unit: Literal["µg/m³"] = "µg/m³"
    duration_seconds: float | None = None
    method: str
    state: DataState
    samples: list[ExposureSample]
    provenance: list[Provenance]


class TrajectoryPoint(BaseModel):
    longitude: Annotated[float, Field(ge=-180, le=180)]
    latitude: Annotated[float, Field(ge=-90, le=90)]
    timestamp: datetime | None = None

    @field_validator("timestamp")
    @classmethod
    def timezone_required_if_present(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("trajectory timestamps must be timezone-aware")
        return value


class Trajectory(BaseModel):
    points: list[TrajectoryPoint] = Field(min_length=2)
    crs: Literal["EPSG:4326"] = "EPSG:4326"

    @model_validator(mode="after")
    def timestamps_are_all_or_none_and_monotonic(self) -> Trajectory:
        timestamps = [point.timestamp for point in self.points]
        has_any = any(value is not None for value in timestamps)
        has_all = all(value is not None for value in timestamps)
        if has_any and not has_all:
            raise ValueError("trajectory timestamps must be supplied for every point or none")
        if has_all:
            aware = [value for value in timestamps if value is not None]
            if any(right <= left for left, right in zip(aware, aware[1:], strict=False)):
                raise ValueError("trajectory timestamps must be strictly increasing")
        return self


class EnvironmentalSnapshot(BaseModel):
    generated_at: datetime
    pollutant: Pollutant
    estimates: list[EnvironmentalFieldEstimate]
    crs: Literal["EPSG:4326"] = "EPSG:4326"
