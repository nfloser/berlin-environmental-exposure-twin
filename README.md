# Berlin Environmental Exposure Twin

A research-oriented environmental digital twin for Berlin that combines genuine air-quality observations with meteorological context and transparent spatial/temporal methods to analyse environmental exposure at monitoring stations, arbitrary locations and routes.

The central scientific rule is simple: **measurements remain measurements; estimates remain estimates.** The system never turns interpolation into an apparent sensor observation and never fabricates missing environmental values.

## What it supports

- Berlin air-quality station discovery and hourly observation ingestion for **NO₂, PM10, PM2.5 and O₃** where the official station actually provides the component.
- Canonical, typed models with provenance, explicit units, quality metadata and the data states `observed`, `interpolated`, `modelled`, `derived`, `scenario`.
- DWD CDC ingestion for hourly meteorological station metadata and recent temperature/humidity and wind products.
- UTC-normalised temporal handling with explicit Berlin DST-gap and DST-fold tests.
- Transparent nearest-station and inverse-distance-weighting (IDW) spatial estimation.
- Leave-one-station-out interpolation validation that computes MAE/RMSE only when enough aligned real observations are available.
- Timestamped trajectory exposure using trapezoidal time integration; untimestamped routes are treated only as spatial concentration comparisons when an explicit snapshot time is supplied.
- Versioned FastAPI endpoints and OpenAPI schemas.
- A scientific map UI that visibly distinguishes measured monitoring locations from estimated environmental fields and surfaces uncertainty indicators.
- CI quality gates for backend tests, linting, formatting, type checking, frontend tests/build and OpenAPI generation, plus non-blocking real-source smoke checks.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'
pytest
uvicorn berlin_exposure_twin.api:app --reload
```

In a second terminal:

```bash
cd frontend
npm test
npm run build
python -m http.server 8080 -d dist
```

Open `http://localhost:8080`. API docs are at `http://localhost:8000/docs`.

## Real-source checks

```bash
berlin-exposure live-smoke --pollutant no2
berlin-exposure dwd-smoke --variable air_temperature
berlin-exposure live-validate --pollutant no2
```

These commands are read-only. They never substitute synthetic values when an official source is unavailable. The Berlin smoke check reports actual returned value/timestamp ranges and units; the validation command uses a documented ±1-hour alignment window and reports LOSO metrics only when at least three stations can contribute.

## Configuration

```bash
cp .env.example .env
```

Supported provider overrides:

- `BERLIN_AIR_API_BASE`
- `DWD_HOURLY_BASE`

No credentials are required for the public source endpoints used by the baseline.

## Docker

```bash
cp .env.example .env
cd frontend && npm run build && cd ..
docker compose up --build
```

API: `http://localhost:8000` · UI: `http://localhost:8080`

## API surface

- `GET /api/v1/health`
- `GET /api/v1/sources`
- `GET /api/v1/stations`
- `GET /api/v1/observations`
- `GET /api/v1/meteorology/stations`
- `GET /api/v1/meteorology/observations`
- `GET /api/v1/environment/state`
- `GET /api/v1/exposure/location`
- `POST /api/v1/exposure/route`
- `GET /api/v1/coverage`

## Scientific caution

This is an environmental analysis system, not a medical diagnostic or personal-risk tool. Monitoring stations are sparse relative to street-level variation. IDW and nearest-station outputs are therefore estimates whose reliability depends on station distance, station count, observation age and source availability.

See `docs/` for architecture, sources, data model, exposure mathematics, validation, integration contracts, testing and limitations.
