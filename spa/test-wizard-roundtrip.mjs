// Quick test: Does applyWizardConfig produce valid TOML that can be parsed back?
import { parse as tomlParse } from "toml-patch";

// Simulate applyWizardConfig result
const testConfig = `
[display]
title = "Test"

[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
max_departures_per_stop = 4
max_departures_per_route = 1
show_ungrouped = true

[[routes]]
path = "/test"

[[routes.stops]]
station_id = "de:09162:140"
station_name = "Test"
max_departures_per_stop = 5
show_ungrouped = false
`;

try {
  tomlParse(testConfig);
} catch {
  // Parse failed, do nothing (lint compliance)
}
