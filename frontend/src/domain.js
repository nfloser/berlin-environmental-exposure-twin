export function stateLabel(state) {
  const labels = {
    observed: "Measured observation",
    interpolated: "Spatial estimate",
    modelled: "Model output",
    derived: "Derived indicator",
    scenario: "Scenario value"
  };
  return labels[state] ?? "Unknown data state";
}

export function uncertaintyText(uncertainty) {
  if (!uncertainty || uncertainty.missing) return "No defensible estimate available";
  const parts = [];
  if (Number.isFinite(uncertainty.nearest_station_m)) {
    parts.push(`nearest station ${(uncertainty.nearest_station_m / 1000).toFixed(1)} km`);
  }
  if (Number.isFinite(uncertainty.contributing_stations)) {
    parts.push(`${uncertainty.contributing_stations} contributing station(s)`);
  }
  if (Number.isFinite(uncertainty.observation_age_seconds)) {
    parts.push(`observation age ${(uncertainty.observation_age_seconds / 3600).toFixed(1)} h`);
  }
  return parts.join(" · ") || "Uncertainty metadata unavailable";
}
