# Limitations

- Monitoring stations are sparse compared with street-level environmental variability.
- Nearest-station and IDW methods are transparent baselines, not atmospheric dispersion models.
- Local street-canyon, traffic, construction and microclimate effects may not be represented by nearby stations.
- Source observations may be provisional and later corrected by the provider.
- Missing observations remain missing; the production path does not synthesize replacements.
- The current baseline uses nearest-in-time hourly air-quality observations rather than a meteorological dispersion model.
- DWD observations are exposed as meteorological context; they are not currently used as causal predictors or to manufacture pollutant fields.
- LOSO validation describes performance at held-out monitoring locations under available network coverage, not exact street-level accuracy.
- Real-source validation may be unavailable when too few stations have sufficiently aligned observations; in that case no metric is emitted.
- No medical-risk, diagnosis, “safe route”, or “unsafe route” claim is produced.
