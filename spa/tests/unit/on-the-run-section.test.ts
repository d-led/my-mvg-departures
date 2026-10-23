import { describe, it, expect } from "vitest";
import {
  addOnTheRunSection,
  hasOnTheRun,
  removeOnTheRunSection,
} from "../../src/utils/on-the-run-section.js";
import { cleanUpConfigToml } from "../../src/utils/config-cleanup.js";
import { ConfigParser } from "../../src/adapters/config/config-parser.js";

const CONFIG_WITH_ROUTES = `[display]
title = "Home"

[[routes]]
path = "/"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
`;

describe("the Next to me table", () => {
  const parser = new ConfigParser();

  it("is reported as present when the config has it", () => {
    expect(hasOnTheRun(`${CONFIG_WITH_ROUTES}\n[[on_the_run]]\n`)).toBe(true);
  });

  it("is reported as missing when it was deleted", () => {
    expect(hasOnTheRun(CONFIG_WITH_ROUTES)).toBe(false);
  });

  it("comes back with settings the app can use", () => {
    const restored = addOnTheRunSection(CONFIG_WITH_ROUTES);

    expect(hasOnTheRun(restored)).toBe(true);
    expect(parser.parseToml(restored).onTheRun).toMatchObject({
      radiusMeters: 50,
      maxDeparturesPerStop: 8,
      maxDeparturesPerRoute: 2,
      updateLocationIntervalSeconds: 20,
    });
  });

  it("keeps every other table and its comments when restored", () => {
    const restored = addOnTheRunSection(CONFIG_WITH_ROUTES);

    expect(restored).toContain('title = "Home"');
    expect(restored).toContain("de:09162:1110");
    expect(restored.indexOf("[[on_the_run]]")).toBeGreaterThan(
      restored.indexOf("[[routes.stops]]"),
    );
  });

  it("is left alone when it is already there", () => {
    const withOnTheRun = `${CONFIG_WITH_ROUTES}
[[on_the_run]]
radius_meters = 250
`;

    expect(addOnTheRunSection(withOnTheRun)).toBe(withOnTheRun);
  });

  it("can be taken away again, comments included", () => {
    const withOnTheRun = `${CONFIG_WITH_ROUTES}
# Nearby departures
[[on_the_run]]
radius_meters = 250
`;

    const removed = removeOnTheRunSection(withOnTheRun);

    expect(hasOnTheRun(removed)).toBe(false);
    expect(removed).not.toContain("Nearby departures");
    expect(removed).toContain("de:09162:1110");
  });

  it("survives being removed by hand and restored", () => {
    const deleted = removeOnTheRunSection(
      `${CONFIG_WITH_ROUTES}\n[[on_the_run]]\nradius_meters = 250\n`,
    );

    const restored = addOnTheRunSection(deleted);

    expect(parser.parseToml(restored).onTheRun?.radiusMeters).toBe(50);
    expect(cleanUpConfigToml(restored).changed).toBe(false);
  });
});
