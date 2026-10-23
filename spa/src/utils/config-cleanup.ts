/**
 * Brings a stored configuration into the SPA's shape.
 *
 * The SPA shares its TOML dialect with the server, so configs written for the
 * server keep loading. This transform makes such a config say what the SPA
 * actually reads:
 *
 * - server-only tables (`[api]`, `[inky]`, `[server]`, ...) are dropped,
 * - the legacy top-level `[[stops]]` become the route at "/",
 * - the display keys the SPA never renders are dropped.
 *
 * It works on the text, so comments and the author's layout survive.
 */

/** Tables the SPA reads; anything else is server-only. */
const SPA_TABLES = new Set(["display", "routes", "on_the_run"]);

/** Tables that hold the legacy spelling of the route at "/". */
const LEGACY_STOPS_TABLE = "stops";

/** Display keys the SPA never reads, so they only add noise. */
const UNUSED_DISPLAY_KEYS = [
  "departures_per_page",
  "page_rotation_seconds",
  "pagination_enabled",
  "banner_color",
];

const HEADER_PATTERN = /^\s*\[\[?([^\]]+)\]\]?\s*(?:#.*)?$/;
const KEY_VALUE_PATTERN = /^\s*([A-Za-z0-9_-]+)\s*=/;

export interface ConfigCleanup {
  /** The configuration in SPA form. */
  toml: string;
  /** Tables dropped because the SPA never reads them, e.g. "[api]". */
  removedSections: string[];
  /** Display keys dropped for the same reason, e.g. "banner_color". */
  removedDisplayKeys: string[];
  /** How many legacy top-level stops moved into the route at "/". */
  movedStops: number;
  /** True when the text changed. */
  changed: boolean;
}

/** What the clean-up did, in one sentence for the user. */
export function describeCleanup(cleanup: ConfigCleanup): string {
  if (!cleanup.changed) {
    return "Nothing to clean up: this configuration already uses the SPA format.";
  }

  const changes: string[] = [];
  if (cleanup.removedSections.length > 0) {
    changes.push(`removed ${cleanup.removedSections.join(", ")}`);
  }
  if (cleanup.movedStops > 0) {
    changes.push(
      `moved ${cleanup.movedStops} stop${cleanup.movedStops === 1 ? "" : "s"} into the route at "/"`,
    );
  }
  if (cleanup.removedDisplayKeys.length > 0) {
    changes.push(`dropped ${cleanup.removedDisplayKeys.join(", ")}`);
  }

  return `Cleaned up: ${changes.join("; ")}. Review the result, then save.`;
}

interface Section {
  /** Table name without brackets, e.g. "routes.stops". */
  name: string;
  headerLine: number;
  /** Index just past the last line that belongs to the table. */
  endLine: number;
}

export function cleanUpConfigToml(toml: string): ConfigCleanup {
  if (!toml.trim()) {
    return {
      toml,
      removedSections: [],
      removedDisplayKeys: [],
      movedStops: 0,
      changed: false,
    };
  }

  const lines = toml.split("\n");
  const sections = readSections(lines);
  const deleted = new Set<number>();
  const insertions = new Map<number, string[]>();
  const removedSections: string[] = [];
  const removedDisplayKeys = new Set<string>();

  for (const section of sections) {
    const root = section.name.split(".")[0];

    if (root === LEGACY_STOPS_TABLE) {
      continue; // converted as a group, see moveLegacyStops
    }

    if (!SPA_TABLES.has(root)) {
      deleteSection(lines, section, deleted);
      removedSections.push(`[${section.name}]`);
      continue;
    }

    removeUnusedDisplayKeys(lines, section, deleted, removedDisplayKeys);
  }

  const movedStops = moveLegacyStops(lines, sections, deleted, insertions);

  const changed =
    deleted.size > 0 ||
    insertions.size > 0 ||
    removedSections.length > 0 ||
    removedDisplayKeys.size > 0;

  return {
    toml: changed ? assemble(lines, deleted, insertions) : toml,
    removedSections,
    removedDisplayKeys: [...removedDisplayKeys],
    movedStops,
    changed,
  };
}

function readSections(lines: string[]): Section[] {
  const sections: Section[] = [];

  lines.forEach((line, index) => {
    const match = HEADER_PATTERN.exec(line);
    if (!match) {
      return;
    }
    if (sections.length > 0) {
      sections[sections.length - 1].endLine = index;
    }
    sections.push({
      name: match[1].trim(),
      headerLine: index,
      endLine: lines.length,
    });
  });

  return sections;
}

/**
 * Deletes a table together with the comment block that documents it, and keeps
 * the blank line and the comment block that introduce the next table.
 */
function deleteSection(
  lines: string[],
  section: Section,
  deleted: Set<number>,
): void {
  const start = commentingStart(lines, section.headerLine);
  const end = bodyEnd(lines, section);
  for (let line = start; line < end; line += 1) {
    deleted.add(line);
  }
}

/** Start of the comment block that sits directly above `line`. */
function commentingStart(lines: string[], line: number): number {
  let start = line;
  while (start > 0 && lines[start - 1].trim().startsWith("#")) {
    start -= 1;
  }
  return start;
}

/** Index just past the table's last line of its own, without the next table's lead-in. */
function bodyEnd(lines: string[], section: Section): number {
  const firstBodyLine = section.headerLine + 1;
  let end = section.endLine;

  while (end > firstBodyLine && lines[end - 1].trim().startsWith("#")) {
    end -= 1;
  }
  while (end > firstBodyLine && lines[end - 1].trim() === "") {
    end -= 1;
  }

  return end;
}

function removeUnusedDisplayKeys(
  lines: string[],
  section: Section,
  deleted: Set<number>,
  removed: Set<string>,
): void {
  const isDisplayTable =
    section.name === "display" || section.name === "routes.display";
  if (!isDisplayTable) {
    return;
  }

  for (let line = section.headerLine + 1; line < section.endLine; line += 1) {
    const key = KEY_VALUE_PATTERN.exec(lines[line])?.[1];
    if (key && UNUSED_DISPLAY_KEYS.includes(key)) {
      for (
        let documented = commentingStart(lines, line);
        documented <= line;
        documented += 1
      ) {
        deleted.add(documented);
      }
      removed.add(key);
    }
  }
}

/**
 * Moves the legacy top-level `[[stops]]` into the route at "/": into the route
 * that already exists at that path, or into a new one where the stops used to be.
 */
function moveLegacyStops(
  lines: string[],
  sections: Section[],
  deleted: Set<number>,
  insertions: Map<number, string[]>,
): number {
  const groups = groupLegacyStops(sections);
  if (groups.length === 0) {
    return 0;
  }

  const stopBlocks = groups.map((group) => convertedStopBlock(lines, group));
  const moveLines = stopBlocks.flat();

  const firstLegacyLine = commentingStart(lines, groups[0][0].headerLine);
  const defaultRoute = sections.find(
    (section) => section.name === "routes" && isDefaultRoute(lines, section),
  );

  if (defaultRoute) {
    addInsertion(insertions, routeBodyEnd(lines, defaultRoute), moveLines);
  } else {
    addInsertion(insertions, firstLegacyLine, [
      "[[routes]]",
      'path = "/"',
      "",
      ...moveLines,
    ]);
  }

  for (const group of groups) {
    const start = commentingStart(lines, group[0].headerLine);
    const end = bodyEnd(lines, group[group.length - 1]);
    for (let line = start; line < end; line += 1) {
      deleted.add(line);
    }
  }

  return groups.length;
}

/** Every `[[stops]]` table together with the `[stops.*]` tables that follow it. */
function groupLegacyStops(sections: Section[]): Section[][] {
  const groups: Section[][] = [];

  for (const section of sections) {
    if (section.name.split(".")[0] !== LEGACY_STOPS_TABLE) {
      continue;
    }
    if (section.name === LEGACY_STOPS_TABLE) {
      groups.push([section]);
      continue;
    }
    groups[groups.length - 1]?.push(section);
  }

  return groups;
}

/** One `[[stops]]` table and its nested tables, spelled as `[[routes.stops]]`. */
function convertedStopBlock(lines: string[], group: Section[]): string[] {
  const start = commentingStart(lines, group[0].headerLine);
  const end = bodyEnd(lines, group[group.length - 1]);
  const headers = new Set(group.map((section) => section.headerLine));

  const block: string[] = [];
  for (let line = start; line < end; line += 1) {
    block.push(headers.has(line) ? renamedHeader(lines[line]) : lines[line]);
  }

  // The block reads better after a blank line, whatever led into it before.
  return [...block, ""];
}

function renamedHeader(line: string): string {
  return line.replace(/\[\[?stops/, (brackets) =>
    brackets.startsWith("[[") ? "[[routes.stops" : "[routes.stops",
  );
}

function isDefaultRoute(lines: string[], section: Section): boolean {
  const body = lines.slice(section.headerLine + 1, section.endLine);
  const pathLine = body.find((line) => /^\s*path\s*=/.test(line));
  return pathLine === undefined || /^\s*path\s*=\s*["']\/["']/.test(pathLine);
}

/** Where the default route's stops end: before the next table of the route. */
function routeBodyEnd(lines: string[], route: Section): number {
  for (let line = route.headerLine + 1; line < route.endLine; line += 1) {
    if (!HEADER_PATTERN.test(lines[line])) {
      continue;
    }
    let insertAt = line;
    while (
      insertAt > route.headerLine + 1 &&
      lines[insertAt - 1].trim() === ""
    ) {
      insertAt -= 1;
    }
    return insertAt;
  }
  return bodyEnd(lines, route);
}

function addInsertion(
  insertions: Map<number, string[]>,
  line: number,
  lines: string[],
): void {
  insertions.set(line, [...(insertions.get(line) ?? []), ...lines]);
}

function assemble(
  lines: string[],
  deleted: Set<number>,
  insertions: Map<number, string[]>,
): string {
  const output: string[] = [];

  for (let line = 0; line < lines.length; line += 1) {
    output.push(...(insertions.get(line) ?? []));
    if (!deleted.has(line)) {
      output.push(lines[line]);
    }
  }
  output.push(...(insertions.get(lines.length) ?? []));

  return withSingleBlankLines(output).join("\n");
}

function withSingleBlankLines(lines: string[]): string[] {
  const result: string[] = [];

  for (const line of lines) {
    const blank = line.trim() === "";
    if (!blank) {
      result.push(line);
      continue;
    }
    if (result.length === 0 || result[result.length - 1].trim() === "") {
      continue;
    }
    result.push("");
  }

  while (result.length > 0 && result[result.length - 1].trim() === "") {
    result.pop();
  }

  return result;
}
