import { describe, it, expect } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { ConfigParser } from "../../src/adapters/config/config-parser.js";
import { cleanUpConfigToml } from "../../src/utils/config-cleanup.js";
import {
  readConfigPages,
  updateConfigPage,
} from "../../src/utils/config-pages.js";

const spaDir = join(dirname(fileURLToPath(import.meta.url)), "../..");

/** The examples the config dialog offers, and the API each one reads. */
const SAMPLES = [
  { file: "config.example.toml", provider: "mvg" },
  { file: "configs/muenchen-muenchner-freiheit.toml", provider: "mvg" },
  { file: "configs/berlin-alexanderplatz.toml", provider: "vbb" },
  { file: "configs/berlin-zoologischer-garten.toml", provider: "vbb" },
];

function readSample(file: string): string {
  return readFileSync(join(spaDir, file), "utf8");
}

describe("the config samples the app ships", () => {
  it("covers every sample in configs/", () => {
    const shipped = readdirSync(join(spaDir, "configs"))
      .filter((name) => name.endsWith(".toml"))
      .map((name) => `configs/${name}`)
      .sort();

    expect(shipped).toEqual(
      SAMPLES.map((sample) => sample.file)
        .filter((file) => file.startsWith("configs/"))
        .sort(),
    );
  });

  describe.each(SAMPLES)("$file", ({ file, provider }) => {
    const toml = readSample(file);

    it("opens on a route at / with stops that name their provider", () => {
      const config = new ConfigParser().parseToml(toml);
      const route = config.routes.find((candidate) => candidate.path === "/");

      expect(route).toBeDefined();
      expect(route?.stops.length).toBeGreaterThan(0);
      for (const stop of route?.stops ?? []) {
        expect(stop.stationId).not.toBe("");
        expect(stop.stationName).not.toBe("");
        expect(stop.apiProvider).toBe(provider);
      }
    });

    it("is already in the SPA's shape", () => {
      expect(cleanUpConfigToml(toml).changed).toBe(false);
    });

    it("keeps every page intact when its form is opened and applied untouched", () => {
      const pages = readConfigPages(toml);
      expect(pages.length).toBeGreaterThan(0);

      pages.forEach((page, pageIndex) => {
        const untouched = {
          path: page.path,
          title: page.title,
          stops: page.stops.map((stop) => ({
            label: stop.label,
            showUngrouped: stop.showUngrouped,
            directions: stop.directions,
          })),
        };

        expect(updateConfigPage(toml, pageIndex, untouched)).toBe(toml);
      });
    });

    it("rewrites one heading without disturbing the others", () => {
      const pages = readConfigPages(toml);
      const pageIndex = pages.findIndex((page) =>
        page.stops.some((stop) => stop.directions.length > 1),
      );
      if (pageIndex < 0) {
        return;
      }

      const page = pages[pageIndex];
      const stopIndex = page.stops.findIndex(
        (stop) => stop.directions.length > 1,
      );
      const before = page.stops[stopIndex].directions;
      const stops = page.stops.map((stop, at) =>
        at === stopIndex
          ? {
              label: stop.label,
              showUngrouped: stop.showUngrouped,
              directions: before.map((direction, index) =>
                index === 0
                  ? { ...direction, patterns: ["U9 Nichts"] }
                  : direction,
              ),
            }
          : {
              label: stop.label,
              showUngrouped: stop.showUngrouped,
              directions: stop.directions,
            },
      );

      const edited = updateConfigPage(toml, pageIndex, {
        path: page.path,
        title: page.title,
        stops,
      });
      const after =
        readConfigPages(edited)[pageIndex].stops[stopIndex].directions;

      expect(after[0].patterns).toEqual(["U9 Nichts"]);
      expect(after.slice(1)).toEqual(before.slice(1));

      // The heading the test left alone keeps the layout it had.
      const untouchedMultiLine = before
        .slice(1)
        .find((direction) => direction.patterns.length > 1);
      if (untouchedMultiLine) {
        expect(edited).toContain(`"${untouchedMultiLine.direction}" = [\n`);
      }
    });

    it("reads the direction headings the file holds", () => {
      const headings = readConfigPages(toml).flatMap((page) =>
        page.stops.flatMap((stop) => stop.directions),
      );

      if (toml.includes("direction_mappings")) {
        expect(headings.length).toBeGreaterThan(0);
      }
      for (const heading of headings) {
        expect(heading.direction).not.toBe("");
        expect(heading.patterns.length).toBeGreaterThan(0);
      }
    });

    it("uses the display settings the SPA renders", () => {
      const display = new ConfigParser().parseToml(toml).display;

      expect(display?.title).toBeTruthy();
      expect(display?.refreshIntervalSeconds).toBeGreaterThan(0);
    });

    it("finds the stops around you in the sample's own API", () => {
      const config = new ConfigParser().parseToml(toml);

      expect(config.onTheRun?.useAdapters).toEqual([provider]);
    });
  });
});
