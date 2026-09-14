# Canonical data model

The core is typed rather than dictionary-driven.

- `MonitoringStation`: identifier, coordinates, type, active state, available pollutants, source.
- `EnvironmentalObservation`: station, pollutant, aware timestamp, value, unit, quality, provenance, always `state=observed`.
- `MeteorologicalObservation`: station, variable, aware timestamp, value, unit, quality, provenance.
- `EnvironmentalFieldEstimate`: point estimate with method, `observed` or `interpolated` state, contributing stations and uncertainty indicators.
- `ExposureSample`: location/time/concentration sample used in route calculations.
- `ExposureResult`: documented aggregate metric with state `derived`.
- `Trajectory`: ordered EPSG:4326 points; timestamps must be supplied for all points or none.
- `DataSource` / `Provenance`: provider, dataset/reference/licence, retrieval time, transformation history and optional method.
- `QualityFlag`: `valid`, `provisional`, `missing`, `suspect`, `unknown`.

## Units
Air-pollutant concentrations are canonicalised to µg/m³ for analytics. Explicit tested conversion from mg/m³ is supported. Unsupported units raise rather than silently converting.

## Time
Every production observation timestamp is timezone-aware and normalised to UTC. Berlin local time conversion rejects nonexistent spring-transition times and requires an explicit `fold` choice for duplicated autumn-transition local times.
