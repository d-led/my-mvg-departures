import { describe, it, expect } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { ConfigParser } from "../../src/adapters/config/config-parser.js";
import { cleanUpConfigToml } from "../../src/utils/config-cleanup.js";

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

    it("uses the display settings the SPA renders", () => {
      const display = new ConfigParser().parseToml(toml).display;

      expect(display?.title).toBeTruthy();
      expect(display?.refreshIntervalSeconds).toBeGreaterThan(0);
    });
  });
});
