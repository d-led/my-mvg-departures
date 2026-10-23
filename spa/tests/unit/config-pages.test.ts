import { describe, expect, it } from "vitest";
import {
  addConfigPage,
  draftOfSettings,
  moveConfigPage,
  readConfigPages,
  readDisplaySettings,
  removeConfigPage,
  removeConfigStop,
  settingsOfDraft,
  updateConfigPage,
  updateDisplaySettings,
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
        display: {},
        stops: [
          {
            stationId: "de:09162:1110",
            name: "Giesing",
            label: "",
            showUngrouped: false,
            directions: [],
          },
          {
            stationId: "de:09162:1120",
            name: "Karlsplatz",
            label: "",
            showUngrouped: false,
            directions: [],
          },
        ],
      },
      {
        path: "/work",
        title: "Work",
        display: {},
        stops: [
          {
            stationId: "de:09162:1000",
            name: "Hauptbahnhof",
            label: "",
            showUngrouped: false,
            directions: [],
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
        directions: [],
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
      directions: stop.directions,
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

const WITH_DIRECTIONS = `[[routes]]
path = "/"

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
show_ungrouped = true

[routes.stops.direction_mappings]
"->City" = ["U2 Messestadt", "19 Pasing"]
"->Norden" = [
  "U3 Moosach",
  "U6 Fröttmaning",
]

[[routes.stops]]
station_id = "de:09162:1120"
station_name = "Karlsplatz"
`;

describe("direction headings", () => {
  it("reads one-line and multi-line lists of matches", () => {
    const [stop] = readConfigPages(WITH_DIRECTIONS)[0].stops;

    expect(stop.directions).toEqual([
      { direction: "->City", patterns: ["U2 Messestadt", "19 Pasing"] },
      { direction: "->Norden", patterns: ["U3 Moosach", "U6 Fröttmaning"] },
    ]);
  });

  it("keeps the headings and the stop table apart", () => {
    const [stop, next] = readConfigPages(WITH_DIRECTIONS)[0].stops;

    expect(stop).toMatchObject({
      name: "Giesing",
      showUngrouped: true,
      label: "",
    });
    expect(next).toMatchObject({ name: "Karlsplatz", directions: [] });
  });

  it("rewrites the headings of a stop that has them", () => {
    const edited = updateConfigPage(WITH_DIRECTIONS, 0, {
      path: "/",
      title: "/",
      stops: [
        {
          label: "",
          showUngrouped: true,
          directions: [{ direction: "->City", patterns: ["U2 Messestadt"] }],
        },
        { label: "", showUngrouped: false, directions: [] },
      ],
    });

    expect(readConfigPages(edited)[0].stops[0].directions).toEqual([
      { direction: "->City", patterns: ["U2 Messestadt"] },
    ]);
    expect(edited).not.toContain("->Norden");
    expect(edited).toContain('station_name = "Giesing"');
    expect(edited).toContain('station_name = "Karlsplatz"');
  });

  it("adds a heading table to a stop that has none", () => {
    const edited = updateConfigPage(TWO_PAGES, 0, {
      ...editOf(0),
      stops: [
        {
          label: "",
          showUngrouped: false,
          directions: [{ direction: "->City", patterns: ["U2 Messestadt"] }],
        },
        { label: "", showUngrouped: false },
      ],
    });

    expect(readConfigPages(edited)[0].stops[0].directions).toEqual([
      { direction: "->City", patterns: ["U2 Messestadt"] },
    ]);
    expect(readConfigPages(edited)[0].stops[1].directions).toEqual([]);
  });

  it("quotes a heading that is not a bare key and the matches it holds", () => {
    const edited = updateConfigPage(TWO_PAGES, 0, {
      ...editOf(0),
      stops: [
        {
          label: "",
          showUngrouped: false,
          directions: [
            { direction: "->City Centre", patterns: ['59 "Giesing" Bf'] },
          ],
        },
        { label: "", showUngrouped: false },
      ],
    });

    expect(edited).toContain('"->City Centre" = ["59 \\"Giesing\\" Bf"]');
    expect(readConfigPages(edited)[0].stops[0].directions[0]).toEqual({
      direction: "->City Centre",
      patterns: ['59 "Giesing" Bf'],
    });
  });

  it("drops the heading table when the last heading is removed", () => {
    const edited = updateConfigPage(WITH_DIRECTIONS, 0, {
      path: "/",
      title: "/",
      stops: [
        { label: "", showUngrouped: true, directions: [] },
        { label: "", showUngrouped: false, directions: [] },
      ],
    });

    expect(edited).not.toContain("direction_mappings");
    expect(edited).toContain('station_name = "Giesing"');
    expect(edited).toContain('station_name = "Karlsplatz"');
  });

  it("leaves the headings alone when the form does not send them", () => {
    const edited = updateConfigPage(WITH_DIRECTIONS, 0, {
      path: "/",
      title: "/",
      stops: [
        { label: "", showUngrouped: true },
        { label: "", showUngrouped: false },
      ],
    });

    expect(edited).toBe(WITH_DIRECTIONS);
  });

  it("takes a stop's headings with it when the stop is deleted", () => {
    const trimmed = removeConfigStop(WITH_DIRECTIONS, 0, 0);
    const [stop] = readConfigPages(trimmed)[0].stops;

    expect(stop.name).toBe("Karlsplatz");
    expect(trimmed).not.toContain("direction_mappings");
    expect(trimmed).not.toContain("U3 Moosach");
  });
});

const WITH_SETTINGS = `[display]
title = "Zuhause"
refresh_interval_seconds = 20
theme = "dark"
fill_vertical_space = true
font_size_time = "2rem"

[[routes]]
path = "/"

[routes.display]
refresh_interval_seconds = 5

[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
`;

describe("display settings", () => {
  it("reads the file's defaults, and only the ones it knows", () => {
    expect(readDisplaySettings(WITH_SETTINGS, "global")).toEqual({
      refresh_interval_seconds: 20,
      theme: "dark",
      fill_vertical_space: true,
    });
  });

  it("reads a page's own settings without mixing in the defaults", () => {
    expect(readDisplaySettings(WITH_SETTINGS, 0)).toEqual({
      refresh_interval_seconds: 5,
    });
    expect(readConfigPages(WITH_SETTINGS)[0].display).toEqual({
      refresh_interval_seconds: 5,
    });
  });

  it("changes one default and leaves the rest of the file alone", () => {
    const edited = updateDisplaySettings(WITH_SETTINGS, "global", {
      refresh_interval_seconds: 30,
    });

    expect(readDisplaySettings(edited, "global")).toEqual({
      refresh_interval_seconds: 30,
      theme: "dark",
      fill_vertical_space: true,
    });
    expect(edited).toContain('font_size_time = "2rem"');
    expect(edited).toContain("refresh_interval_seconds = 5");
  });

  it("adds a setting to a table that does not have it yet", () => {
    const edited = updateDisplaySettings(WITH_SETTINGS, "global", {
      random_header_colors: true,
      theme: "light",
    });

    expect(readDisplaySettings(edited, "global")).toMatchObject({
      random_header_colors: true,
      theme: "light",
    });
    expect(edited).toContain('title = "Zuhause"');
  });

  it("creates the defaults table in a file that has none", () => {
    const withoutDefaults = `[[routes]]\npath = "/"\n`;

    const edited = updateDisplaySettings(withoutDefaults, "global", {
      refresh_interval_seconds: 15,
    });

    expect(readDisplaySettings(edited, "global")).toEqual({
      refresh_interval_seconds: 15,
    });
    expect(readConfigPages(edited)[0].path).toBe("/");
  });

  it("creates a page's display table in front of its stops", () => {
    const edited = updateDisplaySettings(WITH_SETTINGS, 0, {
      theme: "light",
    });
    const page = readConfigPages(edited)[0];

    expect(page.display).toEqual({
      refresh_interval_seconds: 5,
      theme: "light",
    });
    expect(page.stops).toHaveLength(1);
    expect(edited.indexOf("[routes.display]")).toBeLessThan(
      edited.indexOf("[[routes.stops]]"),
    );
  });

  it("removes a setting and drops the table when it was the last one", () => {
    const withoutPageTable = updateDisplaySettings(WITH_SETTINGS, 0, {
      refresh_interval_seconds: undefined,
    });

    expect(withoutPageTable).not.toContain("[routes.display]");
    expect(readDisplaySettings(withoutPageTable, "global")).toMatchObject({
      refresh_interval_seconds: 20,
    });
  });

  it("leaves the file alone when nothing really changed", () => {
    expect(
      updateDisplaySettings(WITH_SETTINGS, "global", {
        refresh_interval_seconds: 20,
        theme: "dark",
      }),
    ).toBe(WITH_SETTINGS);
  });
});

describe("the display form's draft", () => {
  it("shows a setting as text and reads the text back as a setting", () => {
    const draft = draftOfSettings({
      refresh_interval_seconds: 20,
      theme: "dark",
      fill_vertical_space: true,
    });

    expect(draft.refresh_interval_seconds).toBe("20");
    expect(draft.theme).toBe("dark");
    expect(draft.fill_vertical_space).toBe("true");
    expect(draft.split_show_delay).toBe("");

    expect(settingsOfDraft(draft)).toMatchObject({
      refresh_interval_seconds: 20,
      theme: "dark",
      fill_vertical_space: true,
      split_show_delay: undefined,
    });
  });

  it("treats an emptied field as 'this file no longer sets it'", () => {
    const draft = draftOfSettings({ refresh_interval_seconds: 20 });

    expect(
      settingsOfDraft({ ...draft, refresh_interval_seconds: "" }),
    ).toMatchObject({
      refresh_interval_seconds: undefined,
    });
  });
});

describe("addConfigPage", () => {
  it("adds an empty page with a title after the last one", () => {
    const edited = addConfigPage(TWO_PAGES, { path: "/office", title: "Büro" });
    const pages = readConfigPages(edited);

    expect(pages.map((page) => page.title)).toEqual(["Home", "Work", "Büro"]);
    expect(pages[2].stops).toEqual([]);
    expect(edited).toContain("[[on_the_run]]");
  });

  it("keeps the Next to me table last", () => {
    const edited = addConfigPage(TWO_PAGES, { path: "/office", title: "" });

    expect(
      edited.indexOf("[[routes]]", edited.indexOf("/work")),
    ).toBeGreaterThan(-1);
    expect(edited.trimEnd().endsWith("radius_meters = 500")).toBe(true);
  });

  it("writes the first page into a file that has none", () => {
    const edited = addConfigPage(`[display]\ntitle = "Leer"\n`, {
      path: "/",
      title: "",
    });

    expect(readConfigPages(edited)).toHaveLength(1);
    expect(readConfigPages(edited)[0].path).toBe("/");
  });

  it("refuses a path that is already taken", () => {
    expect(addConfigPage(TWO_PAGES, { path: "/work", title: "" })).toBe(
      TWO_PAGES,
    );
    expect(addConfigPage(TWO_PAGES, { path: "  ", title: "" })).toBe(TWO_PAGES);
  });
});
