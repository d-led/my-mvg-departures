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
}

export interface ConfigPage {
  /** The route path, "/" when the block does not say. */
  path: string;
  /** The route's display title, or the path when it has none. */
  title: string;
  stops: ConfigPageStop[];
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
