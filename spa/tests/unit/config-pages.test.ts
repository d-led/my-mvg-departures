import { describe, expect, it } from "vitest";
import {
  moveConfigPage,
  readConfigPages,
  removeConfigPage,
  removeConfigStop,
} from "../../src/utils/config-pages.js";

const TWO_PAGES = `# The pages of the phone

[[routes]]
path = "/"

[[routes.display]]
title = "Home"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"

[[routes.stops]]
station_id = "de:09162:1120"
station_name = "Karlsplatz"

[[routes]]
path = "/work"

[[routes.display]]
title = "Work"

[[routes.stops]]
station_id = "de:09162:1000"
station_name = "Hauptbahnhof"

[[on_the_run]]
radius_meters = 500
`;

describe("readConfigPages", () => {
  it("names every page with its title and its stops", () => {
    expect(readConfigPages(TWO_PAGES)).toEqual([
      {
        path: "/",
        title: "Home",
        stops: [
          { stationId: "de:09162:1110", name: "Giesing" },
          { stationId: "de:09162:1120", name: "Karlsplatz" },
        ],
      },
      {
        path: "/work",
        title: "Work",
        stops: [{ stationId: "de:09162:1000", name: "Hauptbahnhof" }],
      },
    ]);
  });

  it("finds no page in an empty config", () => {
    expect(readConfigPages("")).toEqual([]);
  });

  it("falls back to the path when a page has no title", () => {
    const pages = readConfigPages(`[[routes]]\npath = "/work"\n`);

    expect(pages.map((page) => page.title)).toEqual(["/work"]);
  });
});

describe("moveConfigPage", () => {
  it("puts the second page first, comments and other tables included", () => {
    const moved = moveConfigPage(TWO_PAGES, 1, 0);
    const pages = readConfigPages(moved);

    expect(pages.map((page) => page.path)).toEqual(["/work", "/"]);
    expect(moved.startsWith("# The pages of the phone")).toBe(true);
    expect(moved).toContain("[[on_the_run]]");
    expect(moved).toContain('station_name = "Hauptbahnhof"');
  });
});

describe("removeConfigPage", () => {
  it("drops one page and leaves the other one and the rest of the file alone", () => {
    const trimmed = removeConfigPage(TWO_PAGES, 0);
    const pages = readConfigPages(trimmed);

    expect(pages.map((page) => page.path)).toEqual(["/work"]);
    expect(trimmed).not.toContain("de:09162:1110");
    expect(trimmed).toContain("# The pages of the phone");
    expect(trimmed).toContain("[[on_the_run]]");
  });

  it("leaves the config alone for a page that is not there", () => {
    expect(removeConfigPage(TWO_PAGES, 5)).toBe(TWO_PAGES);
  });
});

describe("removeConfigStop", () => {
  it("takes one stop off a page and keeps the others", () => {
    const trimmed = removeConfigStop(TWO_PAGES, 0, 0);
    const pages = readConfigPages(trimmed);

    expect(pages[0].stops).toEqual([
      { stationId: "de:09162:1120", name: "Karlsplatz" },
    ]);
    expect(pages[1].stops).toHaveLength(1);
  });

  it("leaves the config alone for a stop that is not there", () => {
    expect(removeConfigStop(TWO_PAGES, 0, 7)).toBe(TWO_PAGES);
  });
});
