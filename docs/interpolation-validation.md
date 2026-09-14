# Interpolation validation

## Intended validation
Where enough stations measure the same pollutant at aligned timestamps, IDW is evaluated by leave-one-station-out cross-validation (LOSO):

1. choose timestamps with sufficient simultaneous station coverage;
2. hold out one station;
3. estimate that station from the remaining stations only;
4. compare estimate with the held-out observation;
5. repeat across stations;
6. compute MAE/RMSE only from the actual held-out pairs.

## Implemented validation path
`leave_one_station_out_validation()` performs the held-out calculation and never uses the held-out station as a contributor. `berlin-exposure live-validate --pollutant no2` builds a real-source snapshot by choosing the latest network timestamp and, for each station, accepting only the nearest observation within an explicit ±1-hour alignment window.

If fewer than three stations satisfy that rule, the command reports `insufficient_data` rather than emitting a metric. No validation error is shipped as a constant and no metric is invented.

## Interpreting metrics
MAE and RMSE are expressed in the canonical pollutant concentration unit, µg/m³. A computed LOSO score describes how this transparent interpolation baseline reproduces held-out monitoring locations under the sampled network conditions. It is not a street-level accuracy guarantee.

## LIMITATION
A small monitoring network cannot establish exact street-level concentrations. LOSO evaluates interpolation between monitoring locations; it does not validate every street microenvironment. Traffic canyon effects and local emissions can remain unresolved.
