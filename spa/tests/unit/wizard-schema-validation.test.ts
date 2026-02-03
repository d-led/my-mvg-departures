import { describe, it, expect, beforeAll } from "vitest";
import { readFileSync } from "fs";
import {
  applyWizardConfig,
  getWizardConfigContext,
} from "../../src/utils/config-modifier";
import type { WizardResult } from "../../src/utils/config-modifier";

/**
 * Integration tests: Verify wizard output maintains valid TOML schema
 * Tests against actual config.example.toml structure
 */
describe("Wizard TOML Schema Integrity", () => {
  let exampleConfig: string;

  beforeAll(() => {
    exampleConfig = readFileSync(
      "/Users/dmitryledentsov/src/my_mvg_departures/config.example.toml",
      "utf8",
    );
  });

  describe("Main route additions", () => {
    it("should add stop to main config preserving schema", () => {
      const result: WizardResult = {
        target: "main",
        stops: [
          {
            station_id: "de:test:9999",
            station_name: "New Test Stop",
            max_departures_per_stop: 4,
            max_departures_per_route: 2,
            max_hours_in_advance: 3,
            show_ungrouped: true,
          },
        ],
      };

      const output = applyWizardConfig(exampleConfig, result);

      // Schema validation: stops should be array of tables [[stops]]
      const lines = output.split("\n");

      // Count [[stops]] occurrences - should have multiple
      const stopsTableCount = lines.filter((l) =>
        l.match(/^\[\[stops\]\]/),
      ).length;
      expect(stopsTableCount).toBeGreaterThanOrEqual(2); // At least original + new

      // No inline stops = [...] array property
      const hasInlineStopsArray = lines.some(
        (l) => l.match(/^\s*stops\s*=\s*\[/) && !l.includes("routes.stops"),
      );
      expect(hasInlineStopsArray).toBe(false);

      // Must contain new stop
      expect(output).toContain("de:test:9999");
      expect(output).toContain("New Test Stop");
    });

    it("should preserve display section when adding main stop", () => {
      const result: WizardResult = {
        target: "main",
        stops: [
          {
            station_id: "de:test:8888",
            station_name: "Another Stop",
            max_departures_per_stop: 3,
            max_departures_per_route: 1,
            max_hours_in_advance: 2,
            show_ungrouped: false,
          },
        ],
      };

      const output = applyWizardConfig(exampleConfig, result);

      // Display section must be preserved
      expect(output).toContain("[display]");

      // Original display properties must exist
      expect(output).toMatch(/^\s*title\s*=/m);
      expect(output).toMatch(/^\s*theme\s*=/m);
    });
  });

  describe("Route creation", () => {
    it("should create new route with proper array-of-tables schema", () => {
      const result: WizardResult = {
        target: "route",
        route: {
          path: "/test-wizard-route",
          title: "Test Wizard Route",
        },
        stops: [
          {
            station_id: "de:09162:test:1",
            station_name: "Test Stop 1",
            max_departures_per_stop: 4,
            max_departures_per_route: 2,
            max_hours_in_advance: 3,
            show_ungrouped: true,
          },
          {
            station_id: "de:09162:test:2",
            station_name: "Test Stop 2",
            max_departures_per_stop: 5,
            max_departures_per_route: 2,
            max_hours_in_advance: 2,
            show_ungrouped: false,
          },
        ],
      };

      const output = applyWizardConfig(exampleConfig, result);
      const lines = output.split("\n");

      // Find the new route
      const routeLineIdx = lines.findIndex((l) =>
        l.includes('path = "/test-wizard-route"'),
      );
      expect(routeLineIdx).toBeGreaterThan(-1);

      // Check for display section - either [[routes.display]] or display = [...]
      const displaySectionStartIdx = lines.findIndex(
        (l, i) =>
          i > routeLineIdx && (l.includes("display") || l.includes("title")),
      );
      expect(displaySectionStartIdx).toBeGreaterThan(routeLineIdx);

      // Check for stops section - either [[routes.stops]] or stops array
      const stopsStart = lines.findIndex(
        (l, i) =>
          i > displaySectionStartIdx &&
          (l.includes("station_id") || l.includes("stops")),
      );
      expect(stopsStart).toBeGreaterThan(displaySectionStartIdx);

      // Check structure is NOT conflicting
      const routeBlock = lines.slice(
        routeLineIdx,
        Math.min(lines.length, routeLineIdx + 100),
      );
      const blockText = routeBlock.join("\n");

      // Should NOT have both inline display = {...} AND [[routes.display]]
      const hasInlineDisplay = blockText.includes("display = {");
      const hasArrayDisplay = blockText.includes("[[routes.display]]");
      if (hasInlineDisplay && hasArrayDisplay) {
        throw new Error(
          "SCHEMA VIOLATION: Route has both inline display = {...} AND [[routes.display]]",
        );
      }

      // Should have both stops
      const stopsMatches = blockText.match(/station_id/g);
      expect(stopsMatches?.length || 0).toBeGreaterThanOrEqual(2); // Both stops
    });

    it("should update existing route preserving schema", () => {
      // Get a route path from the example config
      const context = getWizardConfigContext(exampleConfig);
      const existingRoutePath = Object.keys(context.routeStopIdsByPath)[0];

      if (!existingRoutePath) {
        // Skip if no existing routes
        return;
      }

      const result: WizardResult = {
        target: "route",
        route: {
          path: existingRoutePath,
          title: "Updated Route Title",
        },
        stops: [
          {
            station_id: "de:new:test:route",
            station_name: "New Route Stop",
            max_departures_per_stop: 6,
            max_departures_per_route: 3,
            max_hours_in_advance: 4,
            show_ungrouped: true,
          },
        ],
      };

      const output = applyWizardConfig(exampleConfig, result);
      const lines = output.split("\n");

      // Find the updated route
      const pathLine = lines.findIndex((l) =>
        l.includes(`path = "${existingRoutePath}"`),
      );
      expect(pathLine).toBeGreaterThan(-1);

      // Check context for schema violations
      const routeBlock = lines.slice(
        pathLine,
        Math.min(lines.length, pathLine + 100),
      );
      const blockText = routeBlock.join("\n");

      const hasInlineDisplay = blockText.includes("display = {");
      const hasArrayDisplay = blockText.includes("[[routes.display]]");
      if (hasInlineDisplay && hasArrayDisplay) {
        throw new Error(
          `SCHEMA VIOLATION: Updated route ${existingRoutePath} has both inline display AND [[routes.display]]`,
        );
      }

      // Must have new stop
      expect(output).toContain("de:new:test:route");
      expect(output).toContain("New Route Stop");
    });
  });

  describe("Complex config scenarios", () => {
    it("should handle config with multiple routes", () => {
      // The example config has multiple routes - verify schema integrity
      // when adding new route
      const result: WizardResult = {
        target: "route",
        route: {
          path: "/multitest",
          title: "Multi Test",
        },
        stops: [
          {
            station_id: "de:multi:1",
            station_name: "Multi Stop",
            max_departures_per_stop: 4,
            max_departures_per_route: 2,
            max_hours_in_advance: 3,
            show_ungrouped: true,
          },
        ],
      };

      const output = applyWizardConfig(exampleConfig, result);

      // Count routes - should have original + 1
      const routeMatches = output.match(/^\[\[routes\]\]/gm);
      expect(routeMatches?.length || 0).toBeGreaterThanOrEqual(3);

      // All routes should be properly formatted
      const lines = output.split("\n");
      const routeIndices = lines
        .map((l, i) => (l.match(/^\[\[routes\]\]/) ? i : -1))
        .filter((i) => i >= 0);

      // Between each route start, check for conflicts
      for (let i = 0; i < routeIndices.length - 1; i++) {
        const startIdx = routeIndices[i];
        const endIdx = routeIndices[i + 1];
        const routeBlock = lines.slice(startIdx, endIdx).join("\n");

        const hasInline = routeBlock.includes("display = {");
        const hasArray = routeBlock.includes("[[routes.display]]");
        if (hasInline && hasArray) {
          throw new Error(
            `SCHEMA VIOLATION: Route at line ${startIdx} has both inline and array display`,
          );
        }
      }
    });
  });
});
