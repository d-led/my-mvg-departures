import { describe, it, expect } from "vitest";
import {
  addOnTheRunSection,
  draftOfOnTheRun,
  hasOnTheRun,
  readOnTheRunSettings,
  settingsOfOnTheRunDraft,
  updateOnTheRunSettings,
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

  it("survives being deleted by hand and restored", () => {
    const withoutPage = CONFIG_WITH_ROUTES;

    const restored = addOnTheRunSection(withoutPage);

    expect(parser.parseToml(restored).onTheRun?.radiusMeters).toBe(50);
    expect(cleanUpConfigToml(restored).changed).toBe(false);
  });
});

const PAGE_WITH_SETTINGS = `[[routes]]
path = "/"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"

[[on_the_run]]
radius_meters = 500
max_departures_per_stop = 8
max_departures_per_route = 2
refresh_interval_seconds = 20
use_adapters = ["vbb"]
random_header_colors = true
`;

describe("the Next to me page's settings", () => {
  it("reads the numbers, the booleans and the list of APIs", () => {
    expect(readOnTheRunSettings(PAGE_WITH_SETTINGS)).toEqual({
      radius_meters: 500,
      max_departures_per_stop: 8,
      max_departures_per_route: 2,
      refresh_interval_seconds: 20,
      use_adapters: ["vbb"],
      random_header_colors: true,
    });
  });

  it("has nothing to read in a file without the page", () => {
    expect(readOnTheRunSettings(`[[routes]]\npath = "/"\n`)).toEqual({});
  });

  it("changes one setting and leaves the rest of the file alone", () => {
    const edited = updateOnTheRunSettings(PAGE_WITH_SETTINGS, {
      radius_meters: 250,
      use_adapters: ["mvg", "vbb"],
    });

    expect(readOnTheRunSettings(edited)).toMatchObject({
      radius_meters: 250,
      use_adapters: ["mvg", "vbb"],
      refresh_interval_seconds: 20,
    });
    expect(edited).toContain('station_name = "Giesing"');
    expect(edited).toContain("random_header_colors = true");
  });

  it("removes a setting that was emptied", () => {
    const edited = updateOnTheRunSettings(PAGE_WITH_SETTINGS, {
      random_header_colors: undefined,
    });

    expect(edited).not.toContain("random_header_colors");
    expect(readOnTheRunSettings(edited)).toMatchObject({ radius_meters: 500 });
  });

  it("leaves the file alone when nothing changed", () => {
    expect(
      updateOnTheRunSettings(PAGE_WITH_SETTINGS, {
        radius_meters: 500,
        use_adapters: ["vbb"],
      }),
    ).toBe(PAGE_WITH_SETTINGS);
  });

  it("writes nothing into a file that has no such page", () => {
    const withoutPage = `[[routes]]\npath = "/"\n`;

    expect(updateOnTheRunSettings(withoutPage, { radius_meters: 100 })).toBe(
      withoutPage,
    );
  });

  it("shows the settings as a form of text and reads them back", () => {
    const draft = draftOfOnTheRun(readOnTheRunSettings(PAGE_WITH_SETTINGS));

    expect(draft.use_adapters).toBe("vbb");
    expect(draft.radius_meters).toBe(500);
    expect(draft.update_location_on_every_poll).toBe("");

    expect(
      settingsOfOnTheRunDraft({ ...draft, use_adapters: "mvg, vbb" }),
    ).toMatchObject({ use_adapters: ["mvg", "vbb"] });
  });
});
