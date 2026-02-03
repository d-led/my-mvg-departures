import { describe, it, expect, beforeAll } from "vitest";
import { readFileSync } from "fs";
import { applyWizardConfig } from "../../src/utils/config-modifier";
import type { WizardResult } from "../../src/utils/config-modifier";

/**
 * Integration tests with actual config.example.toml
 * Validates that wizard output is valid TOML that can be parsed back
 */
describe("config-modifier with real config.example.toml", () => {
  let configText: string;

  beforeAll(() => {
    // Load actual config from repo root
    configText = readFileSync(
      "/Users/dmitryledentsov/src/my_mvg_departures/config.example.toml",
      "utf8",
    );
  });

  it("should add new route without breaking TOML structure", () => {
    const wizardResult: WizardResult = {
      target: "route",
      route: {
        path: "/test-new-route",
        title: "Test New Route",
      },
      stops: [
        {
          station_id: "de:09184:460:11:52",
          station_name: "Test Station",
          max_departures_per_stop: 4,
          max_departures_per_route: 2,
          max_hours_in_advance: 3,
          show_ungrouped: true,
        },
      ],
    };

    const output = applyWizardConfig(configText, wizardResult);

    // Check structure: Should have valid TOML
    expect(output).toContain("[[routes]]");
    expect(output).toContain('path = "/test-new-route"');
    expect(output).toContain("de:09184:460:11:52");

    // CRITICAL: Should NOT have conflicting display definitions
    // Count how many times we see both inline display and [[routes.display]]
    const lines = output.split("\n");
    let routeBlockIndex = -1;
    let hasInlineDisplay = false;
    let hasArrayDisplay = false;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      if (line.includes('path = "/test-new-route"')) {
        routeBlockIndex = i;
        hasInlineDisplay = false;
        hasArrayDisplay = false;
      }

      if (routeBlockIndex >= 0 && i > routeBlockIndex) {
        if (line.startsWith("[[routes]]") && i !== routeBlockIndex) {
          // New route block started, check the previous one
          if (hasInlineDisplay && hasArrayDisplay) {
            throw new Error(
              `Route at line ${routeBlockIndex} has BOTH inline display = {...} AND [[routes.display]]`,
            );
          }
          routeBlockIndex = -1;
        }

        if (line.includes("display = {")) {
          hasInlineDisplay = true;
        }
        if (line.includes("[[routes.display]]")) {
          hasArrayDisplay = true;
        }
      }
    }

    if (hasInlineDisplay && hasArrayDisplay) {
      throw new Error(
        `Route at line ${routeBlockIndex} has BOTH inline display = {...} AND [[routes.display]]`,
      );
    }
  });

  it("should add stop to main config without breaking TOML", () => {
    const wizardResult: WizardResult = {
      target: "main",
      stops: [
        {
          station_id: "de:09162:999",
          station_name: "Test Stop",
          max_departures_per_stop: 5,
          max_departures_per_route: 2,
          max_hours_in_advance: 2,
          show_ungrouped: true,
        },
      ],
    };

    const output = applyWizardConfig(configText, wizardResult);

    // Should have new stop
    expect(output).toContain("de:09162:999");
    expect(output).toContain("Test Stop");

    // Should still have valid structure
    expect(output).toContain("[[stops]]");
    expect(output).toContain("[display]");
    expect(output).toContain("[[routes]]");
  });
});
