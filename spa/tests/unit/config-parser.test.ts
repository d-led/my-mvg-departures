import { describe, it, expect } from "vitest";
import { ConfigParser } from "../../src/adapters/config/config-parser.js";

describe("ConfigParser", () => {
  const parser = new ConfigParser();

  describe("the route at /", () => {
    it("takes the top-level stops of a legacy config", () => {
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
      expect(config.routes[0].stops[0].directionMappings).toEqual({
        "->Garching": ["U6 Garching-Forschungszentrum"],
      });
    });

    it("keeps the legacy stops ahead of an explicit route at /", () => {
      const toml = `
[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"

[[routes]]
path = "/"

[[routes.stops]]
station_id = "de:09162:1056"
station_name = "Balanstr."
`;

      const config = parser.parseToml(toml);

      expect(config.routes).toHaveLength(1);
      expect(config.routes[0].stops.map((stop) => stop.stationName)).toEqual([
        "Giesing",
        "Balanstr.",
      ]);
    });
  });

  describe("display settings", () => {
    it("are inherited by every route from the global table", () => {
      const toml = `
[display]
title = "Home"
theme = "dark"
fetch_retry_attempts = 5
fetch_retry_delay_ms = 1500

[[routes]]
path = "/work"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
`;

      const config = parser.parseToml(toml);
      const workRoute = config.routes.find((route) => route.path === "/work");

      expect(workRoute?.display).toMatchObject({
        title: "Home",
        theme: "dark",
        fetchRetryAttempts: 5,
        fetchRetryDelayMs: 1500,
      });
    });

    it("let a route override the global values", () => {
      const toml = `
[display]
title = "Home"
theme = "dark"
refresh_interval_seconds = 20

[[routes]]
path = "/work"

[routes.display]
title = "Work"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
`;

      const workRoute = parser
        .parseToml(toml)
        .routes.find((route) => route.path === "/work");

      expect(workRoute?.display?.title).toBe("Work");
      expect(workRoute?.display?.theme).toBe("dark");
      expect(workRoute?.refreshIntervalSeconds).toBe(20);
    });

    it("are absent when nothing is configured, so nothing is inherited", () => {
      const toml = `
[[routes]]
path = "/work"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
`;

      const config = parser.parseToml(toml);

      expect(config.display).toBeUndefined();
      expect(config.routes[0].display).toBeUndefined();
    });
  });

  describe("server-only configuration", () => {
    it("is ignored, leaving only what the SPA renders", () => {
      const toml = `
[display]
title = "Home"
banner_color = "#087BC4"
pagination_enabled = true
departures_per_page = 5
page_rotation_seconds = 8

[api]
sleep_ms_between_calls = 500

[inky]
font_family = "hk_grotesk"

[server]
host = "0.0.0.0"

[[routes]]
path = "/"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
`;

      const config = parser.parseToml(toml);

      expect(config.routes[0].display).toEqual({ title: "Home" });
      expect(Object.keys(config)).toEqual(["display", "routes", "onTheRun"]);
    });
  });

  describe("routes", () => {
    it("are parsed from their path and stops", () => {
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

    it("are dropped when they carry no stops", () => {
      const toml = `
[[routes]]
path = "/empty"
`;

      expect(parser.parseToml(toml).routes).toEqual([]);
    });
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
refresh_interval_seconds = 20
update_location_on_every_poll = false
use_adapters = ["mvg"]
use_precise_location = true
smart_sub_stops = true
random_header_colors = true
`;

    const config = parser.parseToml(toml);

    expect(config.onTheRun?.radiusMeters).toBe(50);
    expect(config.onTheRun?.updateLocationOnEveryPoll).toBe(false);
    expect(config.onTheRun?.useAdapters).toEqual(["mvg"]);
    expect(config.onTheRun?.randomHeaderColors).toBe(true);
    const onTheRunRoute = config.routes.find(
      (route) => route.path === "on-the-run",
    );
    expect(onTheRunRoute?.display?.title).toBe("Departures within 50m");
    expect(onTheRunRoute?.display?.randomHeaderColors).toBe(true);
    expect(onTheRunRoute?.isOnTheRun).toBe(true);
  });
});
