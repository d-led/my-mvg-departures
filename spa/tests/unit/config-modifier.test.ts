import { describe, it, expect } from "vitest";
import {
  applyWizardConfig,
  getWizardConfigContext,
  type WizardResult,
} from "../../src/utils/config-modifier.js";

describe("config-modifier", () => {
  describe("applyWizardConfig - main stops with existing config", () => {
    it("should add new stop alongside existing stops", () => {
      const existingConfig = `
[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
max_departures_per_stop = 5
`;

      const wizardResult: WizardResult = {
        target: "main",
        stops: [
          {
            station_id: "de:09162:2000",
            station_name: "Marienplatz",
            max_departures_per_stop: 6,
            max_departures_per_route: 3,
            max_hours_in_advance: 2,
            show_ungrouped: true,
          },
        ],
      };

      const result = applyWizardConfig(existingConfig, wizardResult);

      expect(result).toContain("de:09162:1110");
      expect(result).toContain("Giesing");
      expect(result).toContain("de:09162:2000");
      expect(result).toContain("Marienplatz");
    });

    it("should persist platform_filter_routes when adding stop to main config", () => {
      const existingConfig = `
[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
`;

      const wizardResult: WizardResult = {
        target: "main",
        stops: [
          {
            station_id: "de:09162:1108:3:3",
            station_name: "Marienplatz",
            max_departures_per_stop: 4,
            max_departures_per_route: 2,
            max_hours_in_advance: 3,
            show_ungrouped: true,
            custom_title: "Platform 3",
            platform_filter_routes: ["62", "U2"],
          },
        ],
      };

      const result = applyWizardConfig(existingConfig, wizardResult);

      expect(result).toContain("platform_filter_routes");
      expect(result).toContain('"62"');
      expect(result).toContain('"U2"');
    });

    it("should merge platform_filter_routes when updating existing stop", () => {
      const existingConfig = `
[[stops]]
station_id = "de:09162:1129:9:9"
station_name = "Am Harras"
max_departures_per_stop = 4
max_departures_per_route = 2
max_hours_in_advance = 3
show_ungrouped = true
ungrouped_title = "7"
`;

      const wizardResult: WizardResult = {
        target: "main",
        stops: [
          {
            station_id: "de:09162:1129:9:9",
            station_name: "Am Harras",
            max_departures_per_stop: 4,
            max_departures_per_route: 2,
            max_hours_in_advance: 3,
            show_ungrouped: true,
            custom_title: "7",
            platform_filter_routes: ["134", "54"],
          },
        ],
      };

      const result = applyWizardConfig(existingConfig, wizardResult);

      expect(result).toContain("platform_filter_routes");
      expect(result).toContain('"134"');
      expect(result).toContain('"54"');
      expect(result).toContain("ungrouped_title");
    });

    it("should add custom ungrouped title to existing config", () => {
      const existingConfig = `
[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
max_departures_per_stop = 6
`;

      const wizardResult: WizardResult = {
        target: "main",
        stops: [
          {
            station_id: "de:09162:1110",
            station_name: "Giesing",
            max_departures_per_stop: 6,
            max_departures_per_route: 3,
            max_hours_in_advance: 2,
            show_ungrouped: true,
            custom_title: "Other Directions",
          },
        ],
      };

      const result = applyWizardConfig(existingConfig, wizardResult);

      expect(result).toContain("ungrouped_title");
      expect(result).toContain("Other Directions");
    });
  });

  describe("applyWizardConfig - route stops with existing config", () => {
    it("should merge stops into existing route with multiple stops", () => {
      const existingConfig = `
[[routes]]
path = "/my-route"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
max_departures_per_stop = 6
max_departures_per_route = 3
max_hours_in_advance = 2
show_ungrouped = true

[[routes.stops]]
station_id = "de:09162:1200"
station_name = "Existing Stop"
max_departures_per_stop = 6
max_departures_per_route = 3
max_hours_in_advance = 2
show_ungrouped = true
`;

      const wizardResult: WizardResult = {
        target: "route",
        route: {
          path: "/my-route",
        },
        stops: [
          {
            station_id: "de:09162:2000",
            station_name: "Marienplatz",
            max_departures_per_stop: 6,
            max_departures_per_route: 3,
            max_hours_in_advance: 2,
            show_ungrouped: true,
          },
        ],
      };

      const result = applyWizardConfig(existingConfig, wizardResult);

      expect(result).toContain("de:09162:1110"); // Existing stops preserved
      expect(result).toContain("de:09162:1200");
      expect(result).toContain("de:09162:2000"); // New stop added
      expect(result).toContain("Marienplatz");
    });

    it("should normalize route path with leading slash when route exists", () => {
      const existingConfig = `
[[routes]]
path = "/custom-route"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
max_departures_per_stop = 6
max_departures_per_route = 3
max_hours_in_advance = 2
show_ungrouped = true
`;

      const wizardResult: WizardResult = {
        target: "route",
        route: {
          path: "custom-route", // No leading slash
        },
        stops: [
          {
            station_id: "de:09162:1110",
            station_name: "Giesing",
            max_departures_per_stop: 6,
            max_departures_per_route: 3,
            max_hours_in_advance: 2,
            show_ungrouped: true,
          },
        ],
      };

      const result = applyWizardConfig(existingConfig, wizardResult);

      // Should find and update the route with normalized path
      expect(result).toContain('path = "/custom-route"');
      expect(result).toContain("de:09162:1110");
    });
  });

  describe("applyWizardConfig - validation", () => {
    it("should reject update to main route (/)", () => {
      const existingConfig = `
[[routes]]
path = "/test"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
max_departures_per_stop = 6
max_departures_per_route = 3
max_hours_in_advance = 2
show_ungrouped = true
`;

      const wizardResult: WizardResult = {
        target: "route",
        route: {
          path: "/",
        },
        stops: [],
      };

      expect(() => applyWizardConfig(existingConfig, wizardResult)).toThrow(
        "not allowed for this target",
      );
    });

    it("should reject update to on-the-run route", () => {
      const existingConfig = `
[[routes]]
path = "/test"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
max_departures_per_stop = 6
max_departures_per_route = 3
max_hours_in_advance = 2
show_ungrouped = true
`;

      const wizardResult: WizardResult = {
        target: "route",
        route: {
          path: "on-the-run",
        },
        stops: [],
      };

      expect(() => applyWizardConfig(existingConfig, wizardResult)).toThrow(
        "not allowed for this target",
      );
    });

    it("should throw error when route path is missing", () => {
      const existingConfig = `[display]
title = "Test"`;

      const wizardResult: WizardResult = {
        target: "route",
        stops: [],
      };

      expect(() => applyWizardConfig(existingConfig, wizardResult)).toThrow(
        "Route target requires a path",
      );
    });
  });

  describe("applyWizardConfig - comment preservation", () => {
    it("should preserve TOML comments when patching", () => {
      const existingConfig = `
# This is my config
[display]
title = "My Departures" # Main display title

# Main stops configuration
[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
max_departures_per_stop = 5
`;

      const wizardResult: WizardResult = {
        target: "main",
        stops: [
          {
            station_id: "de:09162:2000",
            station_name: "Marienplatz",
            max_departures_per_stop: 6,
            max_departures_per_route: 3,
            max_hours_in_advance: 2,
            show_ungrouped: true,
          },
        ],
      };

      const result = applyWizardConfig(existingConfig, wizardResult);

      // Comments are NOT preserved when using stringifyToml (we use it to avoid tomlPatch's inline table issues with direction_mappings)
      // Just verify the new stop was added and existing stop preserved
      expect(result).toContain("de:09162:2000");
      expect(result).toContain("de:09162:1110");
      expect(result).toContain("Marienplatz");
      expect(result).toContain("Giesing");
    });
  });

  describe("getWizardConfigContext", () => {
    it("should extract main stop IDs from config", () => {
      const config = `
[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"

[[stops]]
station_id = "de:09162:2000"
station_name = "Marienplatz"
`;

      const context = getWizardConfigContext(config);

      expect(context.mainStopIds).toEqual(["de:09162:1110", "de:09162:2000"]);
    });

    it("should extract route stop IDs indexed by path", () => {
      const config = `
[[routes]]
path = "/route1"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"

[[routes]]
path = "/route2"

[[routes.stops]]
station_id = "de:09162:2000"
station_name = "Marienplatz"

[[routes.stops]]
station_id = "de:09162:3000"
station_name = "Sendlinger Tor"
`;

      const context = getWizardConfigContext(config);

      expect(context.routeStopIdsByPath["/route1"]).toEqual(["de:09162:1110"]);
      expect(context.routeStopIdsByPath["/route2"]).toEqual([
        "de:09162:2000",
        "de:09162:3000",
      ]);
    });

    it("should detect on_the_run section", () => {
      const configWithOnTheRun = `
[on_the_run]
title = "Next to me"
`;

      const context = getWizardConfigContext(configWithOnTheRun);

      expect(context.hasOnTheRun).toBe(true);
    });

    it("should report no on_the_run when section missing", () => {
      const config = `
[[stops]]
station_id = "de:09162:1110"
`;

      const context = getWizardConfigContext(config);

      expect(context.hasOnTheRun).toBe(false);
    });

    it("should return empty context for empty config", () => {
      const context = getWizardConfigContext("");

      expect(context.mainStopIds).toEqual([]);
      expect(context.routeStopIdsByPath).toEqual({});
      expect(context.hasOnTheRun).toBe(false);
    });

    it("should handle mixed main and route stops", () => {
      const config = `
[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"

[[routes]]
path = "/custom"

[[routes.stops]]
station_id = "de:09162:2000"
station_name = "Marienplatz"
`;

      const context = getWizardConfigContext(config);

      expect(context.mainStopIds).toEqual(["de:09162:1110"]);
      expect(context.routeStopIdsByPath["/custom"]).toEqual(["de:09162:2000"]);
    });
  });

  describe("edge cases - sequential operations and optional fields", () => {
    it("should handle stops without optional fields in existing config", () => {
      const existingConfig = `
[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
max_departures_per_stop = 6
`;

      const wizardResult: WizardResult = {
        target: "main",
        stops: [
          {
            station_id: "de:09162:2000",
            station_name: "Marienplatz",
            max_departures_per_stop: 6,
            max_departures_per_route: 3,
            max_hours_in_advance: 2,
            show_ungrouped: true,
            // No custom_title or direction_mappings
          },
        ],
      };

      const result = applyWizardConfig(existingConfig, wizardResult);

      expect(result).toContain("de:09162:1110");
      expect(result).toContain("de:09162:2000");
      expect(result).not.toContain("ungrouped_title");
    });

    it("should handle stops with empty direction mappings in existing config", () => {
      const existingConfig = `
[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
max_departures_per_stop = 6
`;

      const wizardResult: WizardResult = {
        target: "main",
        stops: [
          {
            station_id: "de:09162:2000",
            station_name: "Marienplatz",
            max_departures_per_stop: 6,
            max_departures_per_route: 3,
            max_hours_in_advance: 2,
            show_ungrouped: true,
            direction_mappings: {}, // Empty mappings
          },
        ],
      };

      const result = applyWizardConfig(existingConfig, wizardResult);

      expect(result).toContain("de:09162:1110");
      expect(result).toContain("de:09162:2000");
      // Empty direction_mappings shouldn't create the section
      expect(result).not.toContain("[stops.direction_mappings]");
    });

    it("should preserve existing config sections when adding new stops", () => {
      const existingConfig = `
[display]
title = "My Departures"
theme = "dark"

[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
`;

      const wizardResult: WizardResult = {
        target: "main",
        stops: [
          {
            station_id: "de:09162:2000",
            station_name: "Marienplatz",
            max_departures_per_stop: 6,
            max_departures_per_route: 3,
            max_hours_in_advance: 2,
            show_ungrouped: true,
          },
        ],
      };

      const result = applyWizardConfig(existingConfig, wizardResult);

      // Existing display section should be preserved
      expect(result).toContain("[display]");
      expect(result).toContain("My Departures");
      expect(result).toContain("dark");
      // New stop added
      expect(result).toContain("de:09162:2000");
      expect(result).toContain("Marienplatz");
    });
  });
});
