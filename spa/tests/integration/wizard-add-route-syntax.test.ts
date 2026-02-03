import { describe, it, expect, beforeAll } from "vitest";
import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { applyWizardConfig } from "../../src/utils/config-modifier";
import { parse as tomlParse } from "toml-patch";
import type { WizardResult } from "../../src/utils/config-modifier";

/**
 * Integration test: Add a new route to a full config and validate TOML syntax
 */
describe("Wizard Add Route - Syntax Validation", () => {
  let exampleConfig: string;

  beforeAll(() => {
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = dirname(__filename);
    exampleConfig = readFileSync(
      join(__dirname, "../../..", "config.example.toml"),
      "utf8",
    );
  });

  it("should add /garching route and produce valid TOML", () => {
    const wizardResult: WizardResult = {
      target: "route",
      route: {
        path: "/garching",
        title: "Garching Departures",
      },
      stops: [
        {
          station_id: "de:09184:460:11:52",
          station_name: "Garching, Forschungszentrum",
          max_departures_per_stop: 4,
          max_departures_per_route: 2,
          max_hours_in_advance: 3,
          show_ungrouped: true,
          custom_title: "Platform 2",
        },
      ],
    };

    const output = applyWizardConfig(exampleConfig, wizardResult);

    // Validate TOML syntax
    try {
      tomlParse(output);
    } catch (e) {
      const msg =
        typeof e === "object" && e && "message" in e
          ? (e as Error).message
          : String(e);
      throw new Error(
        `Wizard produced invalid TOML: ${msg}\n---\n${output}\n---`,
      );
    }

    // Check that the new route exists
    expect(output).toContain('path = "/garching"');
    expect(output).toContain("Garching, Forschungszentrum");
    expect(output).toContain("Platform 2");

    // Check that the config is still valid for other routes
    expect(output).toContain("[[routes]]");
    expect(output).toContain("[display]");
    expect(output).toContain("[[stops]]");
  });
});
