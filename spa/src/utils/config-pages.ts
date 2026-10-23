/**
 * The pages of a configuration, read and edited as whole `[[routes]]` blocks.
 * Everything the app does not own - other tables, comments, layout - is kept.
 */
import {
  belongsTo,
  leadInStart,
  readTomlTables,
  renderToml,
  tableLinesEnd,
  type TomlTable,
} from "./toml-sections.js";

export interface ConfigPageStop {
  stationId: string;
  name: string;
  /** The heading the matches that belong to no direction are shown under. */
  label: string;
  /** Whether departures that match no direction are shown at all. */
  showUngrouped: boolean;
}

export interface ConfigPage {
  /** The route path, "/" when the block does not say. */
  path: string;
  /** The route's display title, or the path when it has none. */
  title: string;
  stops: ConfigPageStop[];
}

/** What a page's form may change. */
export interface ConfigPageEdit {
  path: string;
  title: string;
  stops: { label: string; showUngrouped: boolean }[];
}

interface RouteBlock {
  startLine: number;
  endLine: number;
  tables: TomlTable[];
}

/** One block per `[[routes]]` header, sub-tables included. */
function routeBlocks(lines: string[]): RouteBlock[] {
  const blocks: RouteBlock[] = [];
  let tables: TomlTable[] = [];

  const close = () => {
    if (tables.length === 0) {
      return;
    }
    blocks.push({
      startLine: leadInStart(lines, tables[0].headerLine),
      endLine: tableLinesEnd(lines, tables[tables.length - 1]),
      tables,
    });
    tables = [];
  };

  for (const table of readTomlTables(lines)) {
    if (table.name === "routes") {
      close();
      tables = [table];
      continue;
    }
    if (tables.length > 0 && belongsTo(table.name, "routes")) {
      tables.push(table);
      continue;
    }
    close();
  }
  close();

  return blocks;
}

function stringValue(
  lines: string[],
  table: TomlTable,
  key: string,
): string | undefined {
  const pattern = new RegExp(`^\\s*${key}\\s*=\\s*["']([^"']*)["']`);

  for (let line = table.headerLine + 1; line < table.endLine; line += 1) {
    const match = pattern.exec(lines[line]);
    if (match) {
      return match[1];
    }
  }

  return undefined;
}

function literalValue(
  lines: string[],
  table: TomlTable,
  key: string,
): string | undefined {
  const pattern = new RegExp(`^\\s*${key}\\s*=\\s*(\\S+)`);

  for (let line = table.headerLine + 1; line < table.endLine; line += 1) {
    const match = pattern.exec(lines[line]);
    if (match) {
      return match[1];
    }
  }

  return undefined;
}

function readPage(lines: string[], block: RouteBlock): ConfigPage {
  const path = stringValue(lines, block.tables[0], "path") ?? "/";
  const display = block.tables.find((table) =>
    belongsTo(table.name, "routes.display"),
  );
  const title = (display && stringValue(lines, display, "title")) ?? path;

  const stops = block.tables
    .filter((table) => table.name === "routes.stops")
    .map((table) => ({
      stationId: stringValue(lines, table, "station_id") ?? "",
      name: stringValue(lines, table, "station_name") ?? "unnamed stop",
      label: stringValue(lines, table, "ungrouped_title") ?? "",
      showUngrouped: literalValue(lines, table, "show_ungrouped") === "true",
    }));

  return { path, title, stops };
}

/** The pages of the configuration, in the order the file lists them. */
export function readConfigPages(toml: string): ConfigPage[] {
  if (!toml.trim()) {
    return [];
  }

  const lines = toml.split("\n");
  return routeBlocks(lines).map((block) => readPage(lines, block));
}

/**
 * The pages in a new order. The lines between two blocks - blank lines, comments,
 * a table of another kind - stay where they are.
 */
export function moveConfigPage(toml: string, from: number, to: number): string {
  const lines = toml.split("\n");
  const blocks = routeBlocks(lines);
  if (!isPageIndex(blocks, from) || !isPageIndex(blocks, to) || from === to) {
    return toml;
  }

  const blockLines = blocks.map((block) =>
    lines.slice(block.startLine, block.endLine),
  );
  const order = blocks.map((_, index) => index);
  const [moved] = order.splice(from, 1);
  order.splice(to, 0, moved);

  const gaps = blocks
    .slice(0, -1)
    .map((block, index) =>
      lines.slice(block.endLine, blocks[index + 1].startLine),
    );

  const rebuilt: string[] = [];
  order.forEach((blockIndex, slot) => {
    rebuilt.push(...blockLines[blockIndex]);
    if (slot < gaps.length) {
      rebuilt.push(...gaps[slot]);
    }
  });

  return rerender(
    lines,
    blocks[0].startLine,
    blocks[blocks.length - 1].endLine,
    rebuilt,
  );
}

/** The file without the page at `index`; the other pages are untouched. */
export function removeConfigPage(toml: string, index: number): string {
  const lines = toml.split("\n");
  const blocks = routeBlocks(lines);
  if (!isPageIndex(blocks, index)) {
    return toml;
  }

  const removed = lineRange(blocks[index].startLine, blocks[index].endLine);
  return renderToml(lines, removed, new Map());
}

/** The page without one of its stops. */
export function removeConfigStop(
  toml: string,
  pageIndex: number,
  stopIndex: number,
): string {
  const lines = toml.split("\n");
  const blocks = routeBlocks(lines);
  if (!isPageIndex(blocks, pageIndex)) {
    return toml;
  }

  const stopTables = blocks[pageIndex].tables.filter(
    (table) => table.name === "routes.stops",
  );
  if (stopIndex < 0 || stopIndex >= stopTables.length) {
    return toml;
  }

  const table = stopTables[stopIndex];
  const removed = lineRange(
    leadInStart(lines, table.headerLine),
    tableLinesEnd(lines, table),
  );
  return renderToml(lines, removed, new Map());
}

function isPageIndex(blocks: RouteBlock[], index: number): boolean {
  return Number.isInteger(index) && index >= 0 && index < blocks.length;
}

/**
 * The page with the settings from its form. Keys that already say what the form
 * says are left untouched, so applying an unchanged form changes nothing.
 */
export function updateConfigPage(
  toml: string,
  index: number,
  edit: ConfigPageEdit,
): string {
  const lines = toml.split("\n");
  const blocks = routeBlocks(lines);
  if (!isPageIndex(blocks, index)) {
    return toml;
  }

  const block = blocks[index];
  const start = block.startLine;
  const current = readPage(lines, block);
  let blockLines = lines.slice(start, block.endLine);

  const rangeOf = (table: TomlTable) => ({
    header: table.headerLine - start,
    end: Math.min(table.endLine - start, blockLines.length),
  });

  // Bottom-up: an insert or a removal then never moves a range still to be used.
  const stopTables = block.tables.filter(
    (table) => table.name === "routes.stops",
  );
  for (let stopIndex = stopTables.length - 1; stopIndex >= 0; stopIndex -= 1) {
    const wanted = edit.stops[stopIndex];
    const known = current.stops[stopIndex];
    if (!wanted) {
      continue;
    }
    const range = rangeOf(stopTables[stopIndex]);

    if (wanted.label.trim() !== known.label) {
      blockLines = setKey(
        blockLines,
        range,
        "ungrouped_title",
        wanted.label.trim() === "" ? null : tomlString(wanted.label.trim()),
      );
    }
    if (wanted.showUngrouped !== known.showUngrouped) {
      blockLines = setKey(
        blockLines,
        range,
        "show_ungrouped",
        String(wanted.showUngrouped),
      );
    }
  }

  const title = edit.title.trim() === "" ? null : tomlString(edit.title.trim());
  const display = block.tables.find((table) =>
    belongsTo(table.name, "routes.display"),
  );
  if (display) {
    const range = rangeOf(display);
    const titleWasAll = !hasKeys(blockLines, range, "title");
    blockLines = setKey(blockLines, range, "title", title);

    if (title === null && titleWasAll) {
      // The removed line moved everything below it, so find the next table anew.
      const end = nextSubTableLine(blockLines, range.header);
      blockLines = [
        ...blockLines.slice(0, range.header),
        ...blockLines.slice(end),
      ];
    }
  }

  blockLines = setKey(
    blockLines,
    rangeOf(block.tables[0]),
    "path",
    tomlString(edit.path),
  );

  if (!display && title !== null) {
    const insertAt = firstSubTableLine(blockLines);
    blockLines = [
      ...blockLines.slice(0, insertAt),
      "[routes.display]",
      `title = ${title}`,
      "",
      ...blockLines.slice(insertAt),
    ];
  }

  const original = lines.slice(start, block.endLine);
  const unchanged =
    blockLines.length === original.length &&
    blockLines.every((line, at) => line === original[at]);

  return unchanged ? toml : rerender(lines, start, block.endLine, blockLines);
}

interface LineRange {
  /** The table's header line. */
  header: number;
  /** Index just past the table's own lines. */
  end: number;
}

/** The line of `key` inside the table, or -1. */
function keyLine(lines: string[], range: LineRange, key: string): number {
  const pattern = new RegExp(`^\\s*${key}\\s*=`);

  for (let line = range.header + 1; line < range.end; line += 1) {
    if (pattern.test(lines[line])) {
      return line;
    }
  }

  return -1;
}

/** True when the table still holds anything but comments and `exceptKey`. */
function hasKeys(
  lines: string[],
  range: LineRange,
  exceptKey?: string,
): boolean {
  const skip = exceptKey ? new RegExp(`^\\s*${exceptKey}\\s*=`) : null;

  return lines.slice(range.header + 1, range.end).some((line) => {
    const trimmed = line.trim();
    return trimmed !== "" && !trimmed.startsWith("#") && !skip?.test(line);
  });
}

/** Replaces, adds or (for `null`) removes one `key = value` line. */
function setKey(
  lines: string[],
  range: LineRange,
  key: string,
  value: string | null,
): string[] {
  const line = keyLine(lines, range, key);
  const replacement = value === null ? null : `${key} = ${value}`;

  if (line === -1) {
    return replacement === null
      ? lines
      : [
          ...lines.slice(0, range.header + 1),
          replacement,
          ...lines.slice(range.header + 1),
        ];
  }
  if (replacement === null) {
    return [...lines.slice(0, line), ...lines.slice(line + 1)];
  }

  return lines.map((existing, index) =>
    index === line ? replacement : existing,
  );
}

/** The line of the first sub-table of a route block, or its end. */
function firstSubTableLine(lines: string[]): number {
  return nextSubTableLine(lines, 0);
}

/** The first header line after `from`, or the end of the lines. */
function nextSubTableLine(lines: string[], from: number): number {
  const index = lines.findIndex((line, at) => at > from && /^\s*\[/.test(line));
  return index === -1 ? lines.length : index;
}

function tomlString(value: string): string {
  return `"${value.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
}

function lineRange(startLine: number, endLine: number): Set<number> {
  const range = new Set<number>();
  for (let line = startLine; line < endLine; line += 1) {
    range.add(line);
  }
  return range;
}

/** Replaces the lines between two indexes with `replacement`. */
function rerender(
  lines: string[],
  startLine: number,
  endLine: number,
  replacement: string[],
): string {
  const removed = lineRange(startLine, endLine);
  return renderToml(lines, removed, new Map([[startLine, replacement]]));
}
