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

import {
  leadInStart,
  readTomlTables,
  renderToml,
  tableLinesEnd,
  tomlTableName,
  type TomlTable,
} from "./toml-sections.js";

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
  const tables = readTomlTables(lines);
  const deleted = new Set<number>();
  const insertions = new Map<number, string[]>();
  const removedSections: string[] = [];
  const removedDisplayKeys = new Set<string>();

  for (const table of tables) {
    const root = table.name.split(".")[0];

    if (root === LEGACY_STOPS_TABLE) {
      continue; // converted as a group, see moveLegacyStops
    }

    if (!SPA_TABLES.has(root)) {
      removeTable(lines, table, deleted);
      removedSections.push(`[${table.name}]`);
      continue;
    }

    removeUnusedDisplayKeys(lines, table, deleted, removedDisplayKeys);
  }

  const movedStops = moveLegacyStops(lines, tables, deleted, insertions);

  const changed = deleted.size > 0 || insertions.size > 0;

  return {
    toml: changed ? renderToml(lines, deleted, insertions) : toml,
    removedSections,
    removedDisplayKeys: [...removedDisplayKeys],
    movedStops,
    changed,
  };
}

/**
 * Deletes a table together with the comment block that documents it, and keeps
 * the blank line and the comment block that introduce the next table.
 */
function removeTable(
  lines: string[],
  table: TomlTable,
  deleted: Set<number>,
): void {
  const start = leadInStart(lines, table.headerLine);
  const end = tableLinesEnd(lines, table);
  for (let line = start; line < end; line += 1) {
    deleted.add(line);
  }
}

function removeUnusedDisplayKeys(
  lines: string[],
  table: TomlTable,
  deleted: Set<number>,
  removed: Set<string>,
): void {
  const isDisplayTable =
    table.name === "display" || table.name === "routes.display";
  if (!isDisplayTable) {
    return;
  }

  for (let line = table.headerLine + 1; line < table.endLine; line += 1) {
    const key = KEY_VALUE_PATTERN.exec(lines[line])?.[1];
    if (key && UNUSED_DISPLAY_KEYS.includes(key)) {
      for (
        let documented = leadInStart(lines, line);
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
  tables: TomlTable[],
  deleted: Set<number>,
  insertions: Map<number, string[]>,
): number {
  const groups = groupLegacyStops(tables);
  if (groups.length === 0) {
    return 0;
  }

  const stopBlocks = groups.map((group) => convertedStopBlock(lines, group));
  const moveLines = stopBlocks.flat();

  const firstLegacyLine = leadInStart(lines, groups[0][0].headerLine);
  const defaultRoute = tables.find(
    (table) => table.name === "routes" && isDefaultRoute(lines, table),
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
    const start = leadInStart(lines, group[0].headerLine);
    const end = tableLinesEnd(lines, group[group.length - 1]);
    for (let line = start; line < end; line += 1) {
      deleted.add(line);
    }
  }

  return groups.length;
}

/** Every `[[stops]]` table together with the `[stops.*]` tables that follow it. */
function groupLegacyStops(tables: TomlTable[]): TomlTable[][] {
  const groups: TomlTable[][] = [];

  for (const table of tables) {
    if (table.name.split(".")[0] !== LEGACY_STOPS_TABLE) {
      continue;
    }
    if (table.name === LEGACY_STOPS_TABLE) {
      groups.push([table]);
      continue;
    }
    groups[groups.length - 1]?.push(table);
  }

  return groups;
}

/** One `[[stops]]` table and its nested tables, spelled as `[[routes.stops]]`. */
function convertedStopBlock(lines: string[], group: TomlTable[]): string[] {
  const start = leadInStart(lines, group[0].headerLine);
  const end = tableLinesEnd(lines, group[group.length - 1]);
  const headers = new Set(group.map((table) => table.headerLine));

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

function isDefaultRoute(lines: string[], table: TomlTable): boolean {
  const body = lines.slice(table.headerLine + 1, table.endLine);
  const pathLine = body.find((line) => /^\s*path\s*=/.test(line));
  return pathLine === undefined || /^\s*path\s*=\s*["']\/["']/.test(pathLine);
}

/** Where the default route's stops end: before the next table of the route. */
function routeBodyEnd(lines: string[], route: TomlTable): number {
  for (let line = route.headerLine + 1; line < route.endLine; line += 1) {
    if (tomlTableName(lines[line]) === undefined) {
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
  return tableLinesEnd(lines, route);
}

function addInsertion(
  insertions: Map<number, string[]>,
  line: number,
  lines: string[],
): void {
  insertions.set(line, [...(insertions.get(line) ?? []), ...lines]);
}
