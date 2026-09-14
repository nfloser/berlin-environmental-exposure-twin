from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from berlin_exposure_twin.analytics import leave_one_station_out_validation
from berlin_exposure_twin.models import Pollutant
from berlin_exposure_twin.providers.berlin_air import BerlinAirQualityClient
from berlin_exposure_twin.providers.dwd import DWDClient, DWDVariable


def _berlin_smoke(
    client: BerlinAirQualityClient, pollutant: Pollutant, station_id: str | None
) -> dict:
    stations = client.stations()
    eligible = [station for station in stations if pollutant in station.available_pollutants]
    if not eligible:
        raise RuntimeError(f"No active station reports {pollutant.value}")
    selected = next((station for station in eligible if station.id == station_id), None)
    if station_id is not None and selected is None:
        raise RuntimeError(f"Station {station_id} is not active with {pollutant.value}")
    selected = selected or eligible[0]
    observations = client.observations(selected.id, pollutant)
    values = [observation.value for observation in observations]
    timestamps = [observation.timestamp for observation in observations]
    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "active_station_count": len(stations),
        "eligible_station_count": len(eligible),
        "requested_station": station_id,
        "selected_station": selected.model_dump(mode="json"),
        "pollutant": pollutant.value,
        "observation_count": len(observations),
        "units": sorted({observation.unit for observation in observations}),
        "data_states": sorted({observation.state.value for observation in observations}),
        "value_min": min(values) if values else None,
        "value_max": max(values) if values else None,
        "timestamp_min": min(timestamps).isoformat() if timestamps else None,
        "timestamp_max": max(timestamps).isoformat() if timestamps else None,
        "latest_observation": max(observations, key=lambda value: value.timestamp).model_dump(mode="json")
        if observations
        else None,
    }


def _live_validation(client: BerlinAirQualityClient, pollutant: Pollutant) -> dict:
    stations = {
        station.id: station
        for station in client.stations()
        if pollutant in station.available_pollutants
    }
    series = {station_id: client.observations(station_id, pollutant) for station_id in stations}
    latest_timestamps = [max(values, key=lambda item: item.timestamp).timestamp for values in series.values() if values]
    if not latest_timestamps:
        return {"status": "insufficient_data", "reason": "no observations returned", "n": 0}
    target = max(latest_timestamps)
    aligned = []
    for values in series.values():
        if not values:
            continue
        nearest = min(values, key=lambda item: abs((item.timestamp - target).total_seconds()))
        if abs((nearest.timestamp - target).total_seconds()) <= 3600:
            aligned.append(nearest)
    if len(aligned) < 3:
        return {
            "status": "insufficient_data",
            "reason": "fewer than three stations within the explicit ±1 h alignment window",
            "target_timestamp": target.isoformat(),
            "n": len(aligned),
        }
    metrics = leave_one_station_out_validation(
        pollutant=pollutant,
        timestamp=target,
        observations=aligned,
        stations=stations,
    )
    return {
        "status": "computed",
        "pollutant": pollutant.value,
        "target_timestamp": target.isoformat(),
        "alignment_rule": "nearest station observation within ±1 hour of latest network timestamp",
        "validation": "leave-one-station-out IDW",
        **metrics,
    }


def _dwd_smoke(client: DWDClient, variable: DWDVariable) -> dict:
    stations = client.stations(variable)
    berlin = [station for station in stations if station.get("state", "").casefold() == "berlin"]
    if not berlin:
        raise RuntimeError(f"DWD station metadata contains no Berlin station for {variable}")
    station = berlin[0]
    observations = client.recent_observations(station["station_id"], variable)
    values = [observation.value for observation in observations]
    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "variable": variable,
        "berlin_station_count": len(berlin),
        "selected_station": station,
        "observation_count": len(observations),
        "units": sorted({observation.unit for observation in observations}),
        "data_states": sorted({observation.state.value for observation in observations}),
        "value_min": min(values) if values else None,
        "value_max": max(values) if values else None,
        "timestamp_min": min(o.timestamp for o in observations).isoformat() if observations else None,
        "timestamp_max": max(o.timestamp for o in observations).isoformat() if observations else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Berlin Environmental Exposure Twin utilities")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("stations", help="Fetch active Berlin air-quality stations")

    live = sub.add_parser("live-smoke", help="Run a read-only Berlin source ingestion smoke check")
    live.add_argument("--station", default=None)
    live.add_argument("--pollutant", choices=[p.value for p in Pollutant], default="no2")

    validate = sub.add_parser("live-validate", help="Compute real LOSO validation when coverage permits")
    validate.add_argument("--pollutant", choices=[p.value for p in Pollutant], default="no2")

    dwd = sub.add_parser("dwd-smoke", help="Run a read-only DWD meteorology ingestion smoke check")
    dwd.add_argument(
        "--variable",
        choices=["air_temperature", "relative_humidity", "wind_speed", "wind_direction"],
        default="air_temperature",
    )

    args = parser.parse_args()
    if args.command == "dwd-smoke":
        with DWDClient() as client:
            print(json.dumps(_dwd_smoke(client, args.variable), indent=2))
        return

    with BerlinAirQualityClient() as client:
        if args.command == "stations":
            print(json.dumps([s.model_dump(mode="json") for s in client.stations()], indent=2))
            return
        pollutant = Pollutant(args.pollutant)
        if args.command == "live-validate":
            print(json.dumps(_live_validation(client, pollutant), indent=2))
            return
        print(json.dumps(_berlin_smoke(client, pollutant, args.station), indent=2))


if __name__ == "__main__":
    main()
