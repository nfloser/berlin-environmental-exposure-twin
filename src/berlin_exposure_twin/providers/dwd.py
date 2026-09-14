from __future__ import annotations

import io
import os
import re
import zipfile
from datetime import UTC, datetime
from typing import Any, Literal

import httpx

from berlin_exposure_twin.models import (
    DataSource,
    MeteorologicalObservation,
    Provenance,
    QualityFlag,
)

SOURCE = DataSource(
    provider="Deutscher Wetterdienst (DWD)",
    dataset="Climate Data Center hourly station observations",
    reference="https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/hourly/",
)

_DWD_TIMESTAMP = "%Y%m%d%H"
DWDVariable = Literal["air_temperature", "relative_humidity", "wind_speed", "wind_direction"]


def parse_station_metadata(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        return rows
    for line in lines[2:]:
        match = re.match(
            r"\s*(\d+)\s+(\d{8})\s+(\d{8})\s+(-?\d+)\s+([\d.]+)\s+([\d.]+)\s+(.+?)\s{2,}(.+)$",
            line,
        )
        if not match:
            continue
        station_id, start, end, height, lat, lon, name, state = match.groups()
        rows.append(
            {
                "station_id": station_id.zfill(5),
                "start": start,
                "end": end,
                "height_m": int(height),
                "latitude": float(lat),
                "longitude": float(lon),
                "name": name.strip(),
                "state": state.strip(),
            }
        )
    return rows


def parse_semicolon_product(text: str, *, variable: str) -> list[MeteorologicalObservation]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    headers = [header.strip() for header in lines[0].split(";") if header.strip()]
    result: list[MeteorologicalObservation] = []
    mapping = {
        "air_temperature": ("TT_TU", "°C"),
        "relative_humidity": ("RF_TU", "%"),
        "wind_speed": ("F", "m/s"),
        "wind_direction": ("D", "degree"),
    }
    if variable not in mapping:
        raise ValueError(f"Unsupported DWD variable: {variable}")
    column, unit = mapping[variable]
    if column not in headers:
        raise ValueError(f"DWD product does not contain required column {column}")
    retrieved_at = datetime.now(UTC)
    for raw in lines[1:]:
        values = [value.strip() for value in raw.split(";")]
        row = dict(zip(headers, values, strict=False))
        raw_value = row.get(column)
        if raw_value in (None, "", "-999"):
            continue
        # DWD documents these hourly records against UTC (e.g. "UTC 11").
        timestamp = datetime.strptime(row["MESS_DATUM"], _DWD_TIMESTAMP).replace(tzinfo=UTC)
        qn = row.get("QN_9") or row.get("QN_3") or row.get("QN_8")
        quality = QualityFlag.VALID if qn and qn != "-999" else QualityFlag.UNKNOWN
        result.append(
            MeteorologicalObservation(
                station_id=row["STATIONS_ID"].zfill(5),
                variable=variable,  # type: ignore[arg-type]
                timestamp=timestamp,
                value=float(raw_value),
                unit=unit,  # type: ignore[arg-type]
                quality=quality,
                provenance=Provenance(
                    source=SOURCE,
                    retrieved_at=retrieved_at,
                    transformation_history=[
                        "parsed DWD CDC semicolon product",
                        "interpreted documented hourly timestamp as UTC",
                    ],
                ),
            )
        )
    return result


def extract_product_from_zip(payload: bytes, *, variable: str) -> list[MeteorologicalObservation]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        product_names = [name for name in archive.namelist() if "produkt_" in name.lower()]
        if not product_names:
            raise ValueError("DWD archive contains no product file")
        text = archive.read(product_names[0]).decode("latin-1")
    return parse_semicolon_product(text, variable=variable)


class DWDClient:
    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        resolved_base = base_url or os.getenv(
            "DWD_HOURLY_BASE",
            "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/hourly",
        )
        self._client = httpx.Client(base_url=resolved_base, timeout=timeout, transport=transport)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> DWDClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @staticmethod
    def _dataset(variable: DWDVariable) -> tuple[str, str, str]:
        if variable in ("air_temperature", "relative_humidity"):
            return ("air_temperature", "TU", "TU_Stundenwerte_Beschreibung_Stationen.txt")
        if variable in ("wind_speed", "wind_direction"):
            return ("wind", "FF", "FF_Stundenwerte_Beschreibung_Stationen.txt")
        raise ValueError(f"Unsupported DWD variable: {variable}")

    def stations(self, variable: DWDVariable) -> list[dict[str, Any]]:
        dataset, _code, metadata_name = self._dataset(variable)
        response = self._client.get(f"/{dataset}/recent/{metadata_name}")
        response.raise_for_status()
        return parse_station_metadata(response.text)

    def recent_observations(
        self, station_id: str, variable: DWDVariable
    ) -> list[MeteorologicalObservation]:
        dataset, code, _metadata_name = self._dataset(variable)
        station = station_id.zfill(5)
        response = self._client.get(f"/{dataset}/recent/stundenwerte_{code}_{station}_akt.zip")
        response.raise_for_status()
        return extract_product_from_zip(response.content, variable=variable)
