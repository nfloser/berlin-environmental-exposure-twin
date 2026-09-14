import test from "node:test";
import assert from "node:assert/strict";
import { stateLabel, uncertaintyText } from "../src/domain.js";

test("observed and interpolated labels are visibly different", () => {
  assert.notEqual(stateLabel("observed"), stateLabel("interpolated"));
});

test("uncertainty text exposes distance and contributor count", () => {
  const text = uncertaintyText({ nearest_station_m: 1200, contributing_stations: 3, missing: false });
  assert.match(text, /1.2 km/);
  assert.match(text, /3 contributing/);
});
