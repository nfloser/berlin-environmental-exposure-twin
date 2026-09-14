# Exposure methodology

## Location estimation

### Nearest valid station
For target point `x`, choose the available station `i` with minimum great-circle distance `d(x, i)` and return its concentration as an **interpolated** estimate unless `x` is effectively the station coordinate.

### Inverse-distance weighting
For the nearest `k` valid stations:

`C(x) = Σ w_i C_i / Σ w_i`, where `w_i = 1 / max(d_i, 1 m)^p` and the baseline uses `p = 2`, `k = 4`.

This is an intentionally transparent estimator, not a claim of street-level atmospheric modelling. The result includes nearest-station distance, number of contributors and observation age.

## Timestamp alignment
The service selects, per station, the available observation nearest to the requested timestamp and rejects it when its age exceeds the configured maximum (baseline: two hours). This baseline does not silently average different aggregation intervals. Production air-quality exposure queries request hourly Berlin data.

## Timestamped trajectory exposure
Trajectory segments are spatially densified to at most 250 m between samples. Existing endpoint timestamps are interpolated along those segments; no timestamp or speed is invented when timing is absent.

For samples `(t_i, C_i)`, the time-weighted mean concentration is computed by trapezoidal integration:

`C̄ = [Σ ((C_i + C_{i+1}) / 2) · Δt_i] / [Σ Δt_i]`.

This is a concentration-time average, not a dose estimate and not a medical-risk score.

## Untimestamped route
If route travel time is unknown, the system does not invent a speed. With an explicit `snapshot_time`, the route can instead be compared spatially using the arithmetic mean of concentration estimates at its sampled points. The result is labelled `spatial_mean`, not time exposure.
