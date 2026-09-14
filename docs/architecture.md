# Architecture

## FACT
The primary air-quality source is the Berliner Luftgütemessnetz REST interface. The meteorological source is DWD Climate Data Center Open Data.

## METHOD
The repository uses a provider-adapter architecture:

1. **Provider adapters** terminate external schemas (`providers/berlin_air.py`, `providers/dwd.py`).
2. **Canonical domain models** enforce pollutant identity, time awareness, units, provenance and data state.
3. **Scientific analytics** implement transparent spatial estimation and exposure integration.
4. **Service layer** orchestrates observations and estimators without leaking provider field names.
5. **Versioned API** exposes machine-readable contracts.
6. **Static scientific UI** consumes the API and differentiates measured and estimated values visually and textually.

No production component falls back to generated environmental observations. If upstream data are unavailable, the request fails or returns an explicitly missing estimate.

## Integration boundary
Mobility/resilience twins provide `EPSG:4326` route geometry plus timestamps or an explicit snapshot time. The environmental twin returns pollutant-specific values, data state, method, uncertainty indicators, contributing stations and provenance.
