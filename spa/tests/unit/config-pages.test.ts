import { describe, expect, it } from "vitest";
import {
  moveConfigPage,
  readConfigPages,
  removeConfigPage,
  removeConfigStop,
  updateConfigPage,
  type ConfigPageEdit,
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
          {
            stationId: "de:09162:1110",
            name: "Giesing",
            label: "",
            showUngrouped: false,
          },
          {
            stationId: "de:09162:1120",
            name: "Karlsplatz",
            label: "",
            showUngrouped: false,
          },
        ],
      },
      {
        path: "/work",
        title: "Work",
        stops: [
          {
            stationId: "de:09162:1000",
            name: "Hauptbahnhof",
            label: "",
            showUngrouped: false,
          },
        ],
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
      {
        stationId: "de:09162:1120",
        name: "Karlsplatz",
        label: "",
        showUngrouped: false,
      },
    ]);
    expect(pages[1].stops).toHaveLength(1);
  });

  it("leaves the config alone for a stop that is not there", () => {
    expect(removeConfigStop(TWO_PAGES, 0, 7)).toBe(TWO_PAGES);
  });
});

function editOf(pageIndex: number): ConfigPageEdit {
  const page = readConfigPages(TWO_PAGES)[pageIndex];
  return {
    path: page.path,
    title: page.title,
    stops: page.stops.map((stop) => ({
      label: stop.label,
      showUngrouped: stop.showUngrouped,
    })),
  };
}

describe("updateConfigPage", () => {
  it("renames a page without touching the rest of the file", () => {
    const edited = updateConfigPage(TWO_PAGES, 0, {
      ...editOf(0),
      title: "Wohnung",
    });

    expect(readConfigPages(edited)[0].title).toBe("Wohnung");
    expect(edited).toContain("# The pages of the phone");
    expect(edited).toContain("[[on_the_run]]");
    expect(edited).toContain('title = "Work"');
  });

  it("changes a page's path", () => {
    const edited = updateConfigPage(TWO_PAGES, 1, {
      ...editOf(1),
      path: "/office",
    });

    expect(readConfigPages(edited).map((page) => page.path)).toEqual([
      "/",
      "/office",
    ]);
  });

  it("changes what a stop shows when nothing matches a direction", () => {
    const edited = updateConfigPage(TWO_PAGES, 0, {
      ...editOf(0),
      stops: [
        { label: "Andere", showUngrouped: true },
        { label: "", showUngrouped: false },
      ],
    });
    const stops = readConfigPages(edited)[0].stops;

    expect(stops[0]).toMatchObject({ label: "Andere", showUngrouped: true });
    expect(stops[1]).toMatchObject({ label: "", showUngrouped: false });
    expect(edited).not.toContain("show_ungrouped = false");
  });

  it("adds a title table to a page that has none", () => {
    const withoutTitle = `[[routes]]\npath = "/work"\n\n[[routes.stops]]\nstation_id = "de:09162:1000"\nstation_name = "Hauptbahnhof"\n`;

    const edited = updateConfigPage(withoutTitle, 0, {
      path: "/work",
      title: "Arbeit",
      stops: [{ label: "", showUngrouped: false }],
    });

    expect(readConfigPages(edited)[0].title).toBe("Arbeit");
    expect(edited).toContain("[routes.display]");
  });

  it("drops the title table of the page whose title was cleared", () => {
    const edited = updateConfigPage(TWO_PAGES, 0, { ...editOf(0), title: "" });

    expect(readConfigPages(edited)[0].title).toBe("/");
    expect(edited).not.toContain('title = "Home"');
    expect(edited).toContain('title = "Work"');
    expect(edited).toContain("de:09162:1110");
  });

  it("leaves the file byte for byte alone when the form changed nothing", () => {
    expect(updateConfigPage(TWO_PAGES, 0, editOf(0))).toBe(TWO_PAGES);
    expect(updateConfigPage(TWO_PAGES, 1, editOf(1))).toBe(TWO_PAGES);
  });
});
