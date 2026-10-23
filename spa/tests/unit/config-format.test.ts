import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { parse as tomlParse } from "toml-patch";
import { formatConfigToml } from "../../src/utils/config-format.js";
import { readConfigPages } from "../../src/utils/config-pages.js";

const spaDir = join(dirname(fileURLToPath(import.meta.url)), "../..");

const MESSY = `# my phone screen
[[routes]]
path = "/"

[[routes.stops]]
station_name = "Giesing"
station_id = "de:09162:1110"
show_ungrouped = true
max_departures_per_stop = 12

[routes.stops.direction_mappings]
"->City" = ["U2 Messestadt", "19 Pasing"]

[[routes.display]]
title = "Zuhause"
refresh_interval_seconds = 5

[[on_the_run]]
use_adapters = ["mvg"]
radius_meters = 500
`;

describe("formatConfigToml", () => {
  it("writes the pages first, in the order a reader wants", () => {
    const formatted = formatConfigToml(MESSY);

    expect(formatted).toBe(`[[routes]]
path = "/"

[[routes.display]]
title = "Zuhause"
refresh_interval_seconds = 5

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
max_departures_per_stop = 12
show_ungrouped = true

[routes.stops.direction_mappings]
"->City" = ["U2 Messestadt", "19 Pasing"]

[[on_the_run]]
radius_meters = 500
use_adapters = ["mvg"]
`);
  });

  it("keeps what the configuration says, key by key", () => {
    expect(tomlParse(formatConfigToml(MESSY))).toEqual(tomlParse(MESSY));
  });

  it("is stable: formatting a formatted document changes nothing", () => {
    const once = formatConfigToml(MESSY);

    expect(formatConfigToml(once)).toBe(once);
  });

  it("reads the pages back as the same pages", () => {
    const before = readConfigPages(MESSY);
    const after = readConfigPages(formatConfigToml(MESSY));

    expect(after).toEqual(before);
  });

  it("writes nothing for an empty document", () => {
    expect(formatConfigToml("  \n")).toBe("");
  });

  it("keeps the settings and stop keys it does not know", () => {
    const withExtras = `[[routes]]
path = "/"

[routes.display]
title = "Zuhause"
font_size_time = "3rem"
api_provider = "vbb"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
platform_filter = 9
`;

    const formatted = formatConfigToml(withExtras);

    expect(tomlParse(formatted)).toEqual(tomlParse(withExtras));
    expect(formatted).toContain('font_size_time = "3rem"');
    expect(formatted).toContain("platform_filter = 9");
  });

  describe.each([
    "config.example.toml",
    ...readdirSync(join(spaDir, "configs")).map((name) => `configs/${name}`),
  ])("the shipped %s", (file) => {
    const toml = readFileSync(join(spaDir, file), "utf8");

    it("keeps every value when formatted", () => {
      expect(tomlParse(formatConfigToml(toml))).toEqual(tomlParse(toml));
    });

    it("is already formatted as it would write itself", () => {
      expect(formatConfigToml(formatConfigToml(toml))).toBe(
        formatConfigToml(toml),
      );
    });
  });
});
