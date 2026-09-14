# Data sources

## Berliner Luftgütemessnetz / Berlin Open Data

**FACT:** Berlin publishes current and historical air-quality observations and documents a REST API at `https://luftdaten.berlin.de/api/doc`. Station metadata expose active components; component availability differs by station. The Berlin Open Data catalogue identifies the licence as Datenlizenz Deutschland – Namensnennung – Version 2.0 (dl-de-by-2.0) and notes that measurements remain subject to quality control and may be corrected.

The canonical pollutants initially supported here are NO₂, PM10, PM2.5 and O₃. Values returned by the adapter are labelled `observed` and retain station/timestamp/source provenance. A `null` upstream value is treated as missing and is never replaced with a fabricated concentration.

## Deutscher Wetterdienst (DWD) Climate Data Center

**FACT:** DWD CDC publishes hourly station observations including air temperature/humidity and wind, with station metadata and recent/historical product archives. DWD distinguishes recent data whose quality control is not completed from the versioned historical archive. The hourly source documentation expresses example observation times in UTC.

The implemented recent-product paths are deliberately provider-specific: temperature and relative humidity use the hourly `air_temperature/recent` `TU` product, while wind speed and wind direction use the current hourly `wind_synop/recent` `F` product. Those external naming conventions terminate inside the DWD adapter and are not propagated into the canonical domain model.

**METHOD:** The repository parses station metadata and semicolon product files into `MeteorologicalObservation`. Missing sentinel `-999` is discarded. DWD hourly timestamps are stored internally as UTC and physical units remain explicit. Because DWD metadata may contain stations for which no current `_akt.zip` exists, the live smoke utility first discovers the station IDs that actually have recent archives, intersects that set with station metadata, and only then selects a suitable station by coordinates inside a documented Berlin analysis envelope. If no recent station lies inside the envelope, it falls back to the nearest recent station to Berlin centre. It never substitutes an invented observation when an archive is unavailable.

Meteorological values are exposed as context. The baseline does not infer that simultaneous meteorological and pollutant changes prove causation.

## Reproducibility and raw data

Downloaded source data should be cached under `data/raw/` when running larger analyses. Derived artefacts belong under `data/processed/`. Both directories are ignored except for placeholders so large third-party datasets are not committed accidentally.
