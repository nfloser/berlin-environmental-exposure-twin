# Shared Urban Platform integration contract

All timestamps are ISO-8601 UTC at system boundaries. Coordinates use explicit `EPSG:4326` unless a future schema version adds another CRS.

## EnvironmentalObservation

```json
{
  "station_id": "example-station",
  "pollutant": "no2",
  "timestamp": "2026-09-14T10:00:00Z",
  "value": 12.0,
  "unit": "µg/m³",
  "state": "observed",
  "quality": "provisional",
  "provenance": { "source": { "provider": "Berliner Luftgütemessnetz" } }
}
```

The object above is a **schema example only**. Its station identifier and numeric value are illustrative and must not be interpreted as an actual observation.

## EnvironmentalSnapshot

Machine-readable fields: `generated_at`, `pollutant`, `crs`, `estimates[]`. Every estimate contains `state`, `method`, `unit`, contributing station IDs, uncertainty indicators and provenance.

## RouteExposure request

```json
{
  "pollutant": "no2",
  "trajectory": {
    "crs": "EPSG:4326",
    "points": [
      {"longitude": 13.39, "latitude": 52.51, "timestamp": "2026-09-14T10:00:00Z"},
      {"longitude": 13.41, "latitude": 52.52, "timestamp": "2026-09-14T10:10:00Z"}
    ]
  }
}
```

The route endpoint returns pollutant, metric, value/unit, method, state, duration when applicable, sampled estimates and provenance. When timestamps are absent, the caller must provide `snapshot_time`; the twin will not infer speed.

## Compatibility expectations

- Mobility and resilience twins may pass an `EPSG:4326` trajectory directly.
- `observed` is reserved for source observations at their monitoring location.
- Spatially inferred values are returned as `interpolated`.
- Aggregated route/location indicators are `derived` where appropriate.
- Units and timestamps are explicit and must not be inferred by downstream consumers.
- Missing data remain visible through `value=null`/uncertainty status rather than synthetic replacement.
