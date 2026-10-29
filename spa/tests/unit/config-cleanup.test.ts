import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  cleanUpConfigToml,
  describeCleanup,
} from "../../src/utils/config-cleanup.js";
import { ConfigParser } from "../../src/adapters/config/config-parser.js";

describe("cleanUpConfigToml", () => {
  it("drops the tables the SPA never reads and says which", () => {
    const toml = `
[display]
title = "Home"

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

    const result = cleanUpConfigToml(toml);

    expect(result.removedSections).toEqual(["[api]", "[inky]", "[server]"]);
    expect(result.toml).not.toContain("[api]");
    expect(result.toml).not.toContain("font_family");
    expect(result.toml).not.toContain("[server]");
    expect(result.toml).toContain('title = "Home"');
    expect(result.changed).toBe(true);
  });

  it("takes the comment block that documents a dropped table with it", () => {
    const toml = `
[display]
title = "Home"

# Set to 0 to disable delays (not recommended for production)
[api]
sleep_ms_between_calls = 500

# Kept because it documents the next table
[inky]
font_family = "hk_grotesk"
`;

    const result = cleanUpConfigToml(toml);

    expect(result.toml).not.toContain("sleep_ms_between_calls");
    expect(result.toml).not.toContain("disable delays");
    expect(result.toml).toContain('title = "Home"');
  });

  it("turns the top-level stops into the route at /", () => {
    const toml = `
[display]
title = "Home"

# Giesing is the busiest stop
[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"

[stops.direction_mappings]
"->Garching" = ["U6 Garching-Forschungszentrum"]
`;

    const result = cleanUpConfigToml(toml);

    expect(result.movedStops).toBe(1);
    expect(result.toml).not.toContain("[[stops]]");
    expect(result.toml).toContain('[[routes]]\npath = "/"');
    expect(result.toml).toContain("[[routes.stops]]");
    expect(result.toml).toContain("[routes.stops.direction_mappings]");
    expect(result.toml).toContain("# Giesing is the busiest stop");
  });

  it("adds the legacy stops to the route that already exists at /", () => {
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

    const result = cleanUpConfigToml(toml);

    expect(result.toml.match(/\[\[routes\]\]/g)).toHaveLength(1);
    expect(result.toml.match(/\[\[routes\.stops\]\]/g)).toHaveLength(2);
    expect(result.toml.indexOf("Giesing")).toBeLessThan(
      result.toml.indexOf("Balanstr."),
    );
  });

  it("drops the display keys the SPA never renders", () => {
    const toml = `
[display]
title = "Home"
banner_color = "#087BC4"
pagination_enabled = false
departures_per_page = 5
page_rotation_seconds = 8
theme = "dark"
`;

    const result = cleanUpConfigToml(toml);

    expect(result.removedDisplayKeys.sort()).toEqual([
      "banner_color",
      "departures_per_page",
      "page_rotation_seconds",
      "pagination_enabled",
    ]);
    expect(result.toml).not.toContain("banner_color");
    expect(result.toml).toContain('theme = "dark"');
  });

  it("keeps the comments and the layout of the lines it does not touch", () => {
    const toml = `# The board, as it was written
[display]
title   = "Home"     # lined up by hand
banner_color = "#087BC4"

# Read by the server only
[api]
sleep_ms_between_calls = 500
`;

    const result = cleanUpConfigToml(toml);

    expect(result.toml).toContain("# The board, as it was written");
    expect(result.toml).toContain('title   = "Home"     # lined up by hand');
    expect(result.toml).not.toContain("banner_color");
    expect(result.toml).not.toContain("# Read by the server only");
  });

  it("leaves a config that is already in SPA form untouched", () => {
    const toml = `[display]
title = "Home"

[[routes]]
path = "/"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
`;

    const result = cleanUpConfigToml(toml);

    expect(result.changed).toBe(false);
    expect(result.toml).toBe(toml);
  });

  describe("against the example config the app ships", () => {
    const exampleConfigPath = join(
      dirname(fileURLToPath(import.meta.url)),
      "../../..",
      "config.example.toml",
    );
    const example = readFileSync(exampleConfigPath, "utf8");

    it("leaves every route and stop exactly where the app had them", () => {
      const parser = new ConfigParser();

      const cleaned = cleanUpConfigToml(example);

      expect(parser.parseToml(cleaned.toml)).toEqual(parser.parseToml(example));
    });

    it("is a no-op the second time", () => {
      const cleaned = cleanUpConfigToml(example);

      expect(cleanUpConfigToml(cleaned.toml).changed).toBe(false);
    });
  });

  describe("the SPA's own example config", () => {
    const spaExamplePath = join(
      dirname(fileURLToPath(import.meta.url)),
      "../..",
      "config.example.toml",
    );
    const spaExample = readFileSync(spaExamplePath, "utf8");

    it("is already in SPA form", () => {
      expect(cleanUpConfigToml(spaExample).changed).toBe(false);
    });

    it("gives the app a screen at /, a named screen and Next to me", () => {
      const config = new ConfigParser().parseToml(spaExample);

      expect(config.routes.map((route) => route.path)).toEqual([
        "/",
        "/work",
        "on-the-run",
      ]);
      expect(config.routes[0].stops.map((stop) => stop.stationName)).toEqual([
        "Giesing",
        "Giesing S5",
        "Giesing S3",
        "Tegernseer Str.",
        "Balanstr.",
      ]);
      expect(config.routes[0].display?.title).toBe("Giesing Departures");
      expect(config.routes[1].display?.title).toBe("Work");
      expect(config.onTheRun?.radiusMeters).toBe(100);
    });
  });

  describe("describeCleanup", () => {
    it("says what happened, and that saving is still up to the user", () => {
      const cleanup = cleanUpConfigToml(`
[api]
sleep_ms_between_calls = 500

[[stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
`);

      expect(describeCleanup(cleanup)).toBe(
        'Cleaned up: removed [api]; moved 1 stop into the route at "/". Review the result, then save.',
      );
    });

    it("says so when there was nothing to do", () => {
      const cleanup = cleanUpConfigToml(`[display]
title = "Home"
`);

      expect(describeCleanup(cleanup)).toBe(
        "Nothing to clean up: this configuration already uses the SPA format.",
      );
    });
  });
});
