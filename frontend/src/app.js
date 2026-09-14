import { stateLabel, uncertaintyText } from "./domain.js";

const apiBase = globalThis.ENV_API_BASE ?? "http://localhost:8000";
const map = L.map("map", { zoomControl: true }).setView([52.52, 13.405], 10);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap contributors",
  maxZoom: 18
}).addTo(map);

const stationLayer = L.layerGroup().addTo(map);
const queryLayer = L.layerGroup().addTo(map);
const timestamp = document.querySelector("#timestamp");
timestamp.value = new Date().toISOString().slice(0, 16);

async function checkHealth() {
  try {
    const response = await fetch(`${apiBase}/api/v1/health`);
    if (!response.ok) throw new Error("not ok");
    document.querySelector("#health").textContent = "API online";
  } catch {
    document.querySelector("#health").textContent = "API unavailable";
  }
}

async function loadStations() {
  try {
    const response = await fetch(`${apiBase}/api/v1/stations`);
    if (!response.ok) throw new Error(await response.text());
    const stations = await response.json();
    stationLayer.clearLayers();
    for (const station of stations) {
      L.circleMarker([station.latitude, station.longitude], {
        radius: 5, weight: 2, fillOpacity: 0.75
      }).bindPopup(`<strong>${station.name}</strong><br>${station.station_type ?? "station"}<br><small>Observed monitoring location</small>`).addTo(stationLayer);
    }
    document.querySelector("#coverage-copy").textContent = `${stations.length} active monitoring stations returned by source`;
  } catch {
    document.querySelector("#coverage-copy").textContent = "Station source unavailable";
  }
}

async function estimate() {
  const lat = Number(document.querySelector("#lat").value);
  const lon = Number(document.querySelector("#lon").value);
  const pollutant = document.querySelector("#pollutant").value;
  const method = document.querySelector("#method").value;
  const local = document.querySelector("#timestamp").value;
  const iso = new Date(`${local}Z`).toISOString();
  const params = new URLSearchParams({ latitude: lat, longitude: lon, pollutant, method, timestamp: iso });
  const button = document.querySelector("#estimate");
  button.disabled = true;
  button.textContent = "Querying official observations…";
  try {
    const response = await fetch(`${apiBase}/api/v1/environment/state?${params}`);
    if (!response.ok) throw new Error(await response.text());
    const result = await response.json();
    document.querySelector("#result-title").textContent = `${pollutant.toUpperCase()} at selected location`;
    document.querySelector("#value").textContent = result.value == null ? "N/A" : Number(result.value).toFixed(1);
    const state = document.querySelector("#data-state");
    state.textContent = stateLabel(result.state);
    state.className = `state ${result.state}`;
    document.querySelector("#result-method").textContent = result.method;
    document.querySelector("#stations-used").textContent = result.contributing_station_ids?.length ?? 0;
    document.querySelector("#uncertainty").textContent = uncertaintyText(result.uncertainty);
    queryLayer.clearLayers();
    L.circleMarker([lat, lon], { radius: 9, weight: 3, fillOpacity: 0.25 })
      .bindPopup(stateLabel(result.state)).addTo(queryLayer);
    map.panTo([lat, lon]);
  } catch (error) {
    document.querySelector("#result-title").textContent = "No defensible result";
    document.querySelector("#value").textContent = "N/A";
    document.querySelector("#uncertainty").textContent = String(error);
    const state = document.querySelector("#data-state");
    state.textContent = "Unavailable";
    state.className = "state unknown";
  } finally {
    button.disabled = false;
    button.textContent = "Estimate environmental state";
  }
}

document.querySelector("#estimate").addEventListener("click", estimate);
checkHealth();
loadStations();
