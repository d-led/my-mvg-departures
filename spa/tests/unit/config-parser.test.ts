import { describe, it, expect } from "vitest";
import { ConfigParser } from "../../src/adapters/config/config-parser.js";

describe("ConfigParser", () => {
  const parser = new ConfigParser();

  it("should parse basic TOML config", () => {
    const toml = `
[display]
title = "Test Departures"
theme = "dark"
refresh_interval_seconds = 30

[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
max_departures_per_stop = 6
max_departures_per_route = 2

[stops.direction_mappings]
"->Garching" = ["U6 Garching-Forschungszentrum"]
`;

    const config = parser.parseToml(toml);

    expect(config.routes).toHaveLength(1);
    expect(config.routes[0].path).toBe("/");
    expect(config.routes[0].stops).toHaveLength(1);
    expect(config.routes[0].stops[0].stationId).toBe("de:09162:1110");
    expect(config.routes[0].stops[0].stationName).toBe("Giesing");
    expect(config.routes[0].display?.title).toBe("Test Departures");
    expect(config.routes[0].display?.theme).toBe("dark");
  });

  it("should parse route configurations", () => {
    const toml = `
[[routes]]
path = "/test"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
`;

    const config = parser.parseToml(toml);

    expect(config.routes).toHaveLength(1);
    expect(config.routes[0].path).toBe("/test");
  });

  it("should handle multiple stops", () => {
    const toml = `
[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"

[[stops]]
station_id = "de:09162:1056"
station_name = "Balanstr."
`;

    const config = parser.parseToml(toml);

    expect(config.routes[0].stops).toHaveLength(2);
  });

  it("should parse on_the_run config and add route", () => {
    const toml = `
[[on_the_run]]
radius_meters = 50
max_departures_per_stop = 8
max_departures_per_route = 2
update_location_interval_seconds = 20
use_adapters = ["mvg"]
use_precise_location = true
smart_sub_stops = true
random_header_colors = true
`;

    const config = parser.parseToml(toml);

    expect(config.onTheRun?.radiusMeters).toBe(50);
    expect(config.onTheRun?.useAdapters).toEqual(["mvg"]);
    expect(config.onTheRun?.randomHeaderColors).toBe(true);
    const onTheRunRoute = config.routes.find(
      (route) => route.path === "on-the-run",
    );
    expect(onTheRunRoute?.display?.title).toBe("Next to me");
    expect(onTheRunRoute?.display?.randomHeaderColors).toBe(true);
    expect(onTheRunRoute?.isOnTheRun).toBe(true);
  });
});
