# Testing strategy

Development follows Red → Green → Refactor. Tests specify scientific behaviour before or alongside the implementation capability they protect.

The repository covers:

- typed model validation;
- pollutant contract stability;
- unit conversion and rejection of unknown units;
- timezone-awareness and Berlin DST gap/fold behaviour;
- geospatial distance calculation and timestamp-preserving route densification;
- IDW behaviour and measured-vs-interpolated classification;
- time-weighted route exposure integration;
- held-out interpolation validation;
- Berlin source parsing, missing observations and station-specific component availability;
- DWD missing-value sentinels, units, UTC timestamps, station metadata and ZIP product ingestion;
- API health, OpenAPI route contract and timezone validation;
- frontend data-state distinction and uncertainty text.

All test environmental concentrations are synthetic fixtures and are labelled as such in source/test provenance. Provider parser tests use source-shaped payloads without claiming fixture values are current observations.

## Deterministic CI quality gates

- `pytest --cov=berlin_exposure_twin`
- `ruff check .`
- `ruff format --check .`
- `mypy src`
- frontend `node --test`
- frontend static build
- OpenAPI schema generation/JSON serialization

## External-source verification
CI also executes read-only Berlin and DWD smoke checks and a real Berlin LOSO validation attempt. These steps are deliberately non-blocking because upstream network/source availability is external to repository correctness. Their logs are evidence of what was actually reachable at that run; failure must never be replaced by fabricated data.
