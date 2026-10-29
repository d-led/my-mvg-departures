/**
 * The pages of a configuration, read and edited as whole `[[routes]]` blocks.
 * Everything the app does not own - other tables, comments, layout - is kept.
 */
import {
  belongsTo,
  leadInStart,
  readTomlTables,
  renderToml,
  setTomlKey as setKey,
  tableLinesEnd,
  tomlString,
  tomlTableHasKeys as hasKeys,
  type TomlTable,
} from "./toml-sections.js";

/** One heading of a page and the departures that belong under it. */
export interface ConfigDirectionMapping {
  /** The heading, e.g. "->City". */
  direction: string;
  /** Matched against `"{line} {destination}"`; one hit is enough. */
  patterns: string[];
}

export interface ConfigPageStop {
  stationId: string;
  name: string;
  /** The heading the matches that belong to no direction are shown under. */
  label: string;
  /** Whether departures that match no direction are shown at all. */
  showUngrouped: boolean;
  directions: ConfigDirectionMapping[];
  /** `max_departures_per_stop`; absent while the file does not say. */
  maxDepartures?: number;
  /** `max_departures_per_route`, the rows one line gets. */
  perLineDepartures?: number;
  /** `max_hours_in_advance`; absent while the file does not say. */
  hoursInAdvance?: number;
}

export interface ConfigPage {
  /** The route path, "/" when the block does not say. */
  path: string;
  /** The route's display title, or the path when it has none. */
  title: string;
  /** The display settings this page sets for itself. */
  display: DisplaySettings;
  stops: ConfigPageStop[];
}

/** What one stop of a page may change. */
export interface ConfigPageStopEdit {
  label: string;
  showUngrouped: boolean;
  /** The name the board shows; absent leaves the file's name alone. */
  name?: string;
  /** Omitted means: leave the stop's direction headings exactly as they are. */
  directions?: ConfigDirectionMapping[];
  /** A number writes the key, `null` removes it, absent leaves it alone. */
  maxDepartures?: number | null;
  perLineDepartures?: number | null;
  hoursInAdvance?: number | null;
}

/** What a page's form may change. */
export interface ConfigPageEdit {
  path: string;
  title: string;
  stops: ConfigPageStopEdit[];
}

/** A stop the configurator adds to a page; everything else takes its default. */
export interface NewConfigStop {
  stationId: string;
  stationName: string;
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

/** A numeric key; a value that is not a number reads as absent. */
function numberValue(
  lines: string[],
  table: TomlTable,
  key: string,
): number | undefined {
  const raw = literalValue(lines, table, key);
  if (raw === undefined) {
    return undefined;
  }
  const value = Number(raw.replace(/[_,]/g, ""));

  return Number.isFinite(value) ? value : undefined;
}

interface StopSection {
  stop: TomlTable;
  /** `[routes.stops.direction_mappings]`, when the stop has headings. */
  mappings?: TomlTable;
}

/** The stops of a route block, each with the table that heads its directions. */
function stopSections(block: RouteBlock): StopSection[] {
  const sections: StopSection[] = [];

  for (const table of block.tables) {
    if (table.name === "routes.stops") {
      sections.push({ stop: table });
      continue;
    }
    if (
      table.name === "routes.stops.direction_mappings" &&
      sections.length > 0
    ) {
      sections[sections.length - 1].mappings = table;
    }
  }

  return sections;
}

/** The stop as the file has it. */
function readStop(lines: string[], section: StopSection): ConfigPageStop {
  const { stop, mappings } = section;

  return {
    stationId: stringValue(lines, stop, "station_id") ?? "",
    name: stringValue(lines, stop, "station_name") ?? "unnamed stop",
    label: stringValue(lines, stop, "ungrouped_title") ?? "",
    showUngrouped: literalValue(lines, stop, "show_ungrouped") === "true",
    directions: mappings ? readDirections(lines, mappings) : [],
    maxDepartures: numberValue(lines, stop, "max_departures_per_stop"),
    perLineDepartures: numberValue(lines, stop, "max_departures_per_route"),
    hoursInAdvance: numberValue(lines, stop, "max_hours_in_advance"),
  };
}

function readPage(lines: string[], block: RouteBlock): ConfigPage {
  const path = stringValue(lines, block.tables[0], "path") ?? "/";
  const display = block.tables.find((table) =>
    belongsTo(table.name, "routes.display"),
  );
  const title = (display && stringValue(lines, display, "title")) ?? path;

  const stops = stopSections(block).map((section) => readStop(lines, section));

  return { path, title, display: displaySettings(lines, display), stops };
}

/** The display settings a table sets, without touching anything else. */
function displaySettings(
  lines: string[],
  table: TomlTable | undefined,
): DisplaySettings {
  if (!table) {
    return {};
  }

  const settings: DisplaySettings = {};
  for (const field of DISPLAY_FIELDS) {
    const value = settingValue(lines, table, field);
    if (value !== undefined) {
      settings[field.key] = value;
    }
  }

  return settings;
}

/** The `direction = [patterns]` rows of a direction table, multi-line arrays included. */
function readDirections(
  lines: string[],
  table: TomlTable,
): ConfigDirectionMapping[] {
  const directions: ConfigDirectionMapping[] = [];
  const row = /^\s*(?:"([^"]*)"|'([^']*)'|([A-Za-z0-9_-]+))\s*=\s*(.*)$/;

  let line = table.headerLine + 1;
  while (line < table.endLine) {
    const match = row.exec(lines[line]);
    if (!match) {
      line += 1;
      continue;
    }

    const direction = match[1] ?? match[2] ?? match[3];
    const array = collectArray(lines, line, match[4], table.endLine);
    directions.push({ direction, patterns: parseStrings(array.text) });
    line = array.lastLine + 1;
  }

  return directions;
}

interface CollectedArray {
  text: string;
  lastLine: number;
}

/** The text of an array value, joining the lines of a multi-line array. */
function collectArray(
  lines: string[],
  startLine: number,
  firstChunk: string,
  endLine: number,
): CollectedArray {
  let text = firstChunk;
  let line = startLine;

  while (depth(text) > 0 && line + 1 < endLine) {
    line += 1;
    text += ` ${lines[line].replace(/#.*$/, "")}`;
  }

  return { text, lastLine: line };
}

function depth(text: string): number {
  let brackets = 0;
  let quoted = false;

  for (const character of text) {
    if (character === '"') {
      quoted = !quoted;
    } else if (!quoted && character === "[") {
      brackets += 1;
    } else if (!quoted && character === "]") {
      brackets -= 1;
    }
  }

  return brackets;
}

/** The strings of a TOML array, in order. */
function parseStrings(text: string): string[] {
  const strings: string[] = [];
  let current = "";
  let quoted: '"' | "'" | null = null;

  for (let at = 0; at < text.length; at += 1) {
    const character = text[at];

    if (quoted === null) {
      if (character === '"' || character === "'") {
        quoted = character;
        current = "";
      }
      continue;
    }

    if (character === "\\" && quoted === '"') {
      current += text[at + 1] ?? "";
      at += 1;
      continue;
    }

    if (character === quoted) {
      strings.push(current);
      quoted = null;
      continue;
    }

    current += character;
  }

  return strings;
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

/** The page without one of its stops, its direction headings included. */
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

  const sections = stopSections(blocks[pageIndex]);
  const section = sections[stopIndex];
  if (!section) {
    return toml;
  }

  const last = section.mappings ?? section.stop;
  const removed = lineRange(
    leadInStart(lines, section.stop.headerLine),
    tableLinesEnd(lines, last),
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

  /** A table's place in the block, as it is after the edits made so far. */
  const rangeOf = (table: TomlTable) => ({
    header: table.headerLine - start,
    end: Math.min(table.endLine - start, blockLines.length),
  });

  // Bottom-up: an insert or a removal then never moves a range still to be used.
  const sections = stopSections(block);
  for (let stopIndex = sections.length - 1; stopIndex >= 0; stopIndex -= 1) {
    const wanted = edit.stops[stopIndex];
    if (!wanted) {
      continue;
    }
    blockLines = applyStopEdit(
      blockLines,
      start,
      sections[stopIndex],
      current.stops[stopIndex],
      wanted,
    );
  }

  // A title that only repeats the path is what a page without a title shows, so
  // applying the form must not write one.
  const titleText = edit.title.trim();
  const title =
    titleText === "" || titleText === edit.path.trim()
      ? null
      : tomlString(titleText);
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

/** The rows one line of a stop may show, in reading order. */
const STOP_COUNTS = [
  {
    key: "max_departures_per_stop",
    known: (stop: ConfigPageStop) => stop.maxDepartures,
    wanted: (edit: ConfigPageStopEdit) => edit.maxDepartures,
  },
  {
    key: "max_departures_per_route",
    known: (stop: ConfigPageStop) => stop.perLineDepartures,
    wanted: (edit: ConfigPageStopEdit) => edit.perLineDepartures,
  },
  {
    key: "max_hours_in_advance",
    known: (stop: ConfigPageStop) => stop.hoursInAdvance,
    wanted: (edit: ConfigPageStopEdit) => edit.hoursInAdvance,
  },
] as const;

/**
 * One stop of a block with the edit applied. Every range is looked up again
 * after each write, because a write may add or remove lines above the next one.
 */
function applyStopEdit(
  blockLines: string[],
  start: number,
  section: StopSection,
  known: ConfigPageStop,
  edit: ConfigPageStopEdit,
): string[] {
  let lines = blockLines;
  const rangeOfStop = () => ({
    header: section.stop.headerLine - start,
    end: Math.min(section.stop.endLine - start, lines.length),
  });

  if (
    edit.directions !== undefined &&
    !sameDirections(known.directions, edit.directions)
  ) {
    const asked = cleanDirections(edit.directions);
    const mappings = section.mappings;
    if (mappings) {
      const header = mappings.headerLine - start;
      const end = Math.min(mappings.endLine - start, lines.length);
      lines = replaceRange(
        lines,
        header,
        end,
        asked.length === 0
          ? []
          : patchDirectionTable(lines.slice(header, end), asked),
      );
    } else if (asked.length > 0) {
      const at = section.stop.endLine - start;
      lines = [
        ...lines.slice(0, at),
        ...directionTableLines(asked),
        ...lines.slice(at),
      ];
    }
  }

  if (edit.label.trim() !== known.label) {
    lines = setKey(
      lines,
      rangeOfStop(),
      "ungrouped_title",
      edit.label.trim() === "" ? null : tomlString(edit.label.trim()),
    );
  }
  if (edit.name !== undefined && edit.name.trim() !== known.name) {
    // An empty name would read back as "unnamed stop", so it is not written.
    if (edit.name.trim() !== "") {
      lines = setKey(
        lines,
        rangeOfStop(),
        "station_name",
        tomlString(edit.name.trim()),
      );
    }
  }
  if (edit.showUngrouped !== known.showUngrouped) {
    lines = setKey(
      lines,
      rangeOfStop(),
      "show_ungrouped",
      String(edit.showUngrouped),
    );
  }

  for (const count of STOP_COUNTS) {
    const wanted = count.wanted(edit);
    if (wanted === undefined || wanted === count.known(known)) {
      continue;
    }
    lines = setKey(
      lines,
      rangeOfStop(),
      count.key,
      wanted === null ? null : String(wanted),
    );
  }

  return lines;
}

/** One stop of a page with the settings from its form. */
export function updateConfigStop(
  toml: string,
  pageIndex: number,
  stopIndex: number,
  edit: ConfigPageStopEdit,
): string {
  const lines = toml.split("\n");
  const blocks = routeBlocks(lines);
  if (!isPageIndex(blocks, pageIndex)) {
    return toml;
  }

  const block = blocks[pageIndex];
  const section = stopSections(block)[stopIndex];
  if (!section) {
    return toml;
  }

  const start = block.startLine;
  const known = readStop(lines, section);
  const original = lines.slice(start, block.endLine);
  const edited = applyStopEdit(original, start, section, known, edit);
  const unchanged =
    edited.length === original.length &&
    edited.every((line, at) => line === original[at]);

  return unchanged ? toml : rerender(lines, start, block.endLine, edited);
}

/** The page with a stop appended; a stop the page already has adds nothing. */
export function addConfigStop(
  toml: string,
  pageIndex: number,
  stop: NewConfigStop,
): string {
  const lines = toml.split("\n");
  const blocks = routeBlocks(lines);
  if (!isPageIndex(blocks, pageIndex)) {
    return toml;
  }

  const block = blocks[pageIndex];
  // The same station may sit on a page twice, under two names - Giesing's
  // platforms are the example - so only an identical entry counts as present.
  const known = stopSections(block).map((section) => readStop(lines, section));
  if (
    known.some(
      (existing) =>
        existing.stationId === stop.stationId &&
        existing.name === stop.stationName,
    )
  ) {
    return toml;
  }

  const last = block.tables[block.tables.length - 1];
  const at = tableLinesEnd(lines, last);
  return renderToml(
    lines,
    new Set(),
    new Map([
      [
        at,
        [
          "",
          "[[routes.stops]]",
          `station_id = ${tomlString(stop.stationId)}`,
          `station_name = ${tomlString(stop.stationName)}`,
        ],
      ],
    ]),
  );
}

/** A display setting a form may edit, and how the form presents it. */
export interface DisplayField {
  key: string;
  label: string;
  kind: "number" | "boolean" | "select" | "text";
  /** The section of the form the field belongs to. */
  group: DisplayGroup;
  options?: readonly string[];
  hint?: string;
  /** What the app uses while the file does not set the field. */
  fallback?: string;
}

/** The sections a display form is read in: what it does, how it looks, its type. */
export type DisplayGroup = "Timing" | "Look" | "Fonts";

const DISPLAY_GROUPS: readonly DisplayGroup[] = ["Timing", "Look", "Fonts"];

/** The fields of one form, in the sections the dialog shows them in. */
export function displayFieldGroups(): {
  name: DisplayGroup;
  fields: DisplayField[];
}[] {
  return DISPLAY_GROUPS.map((name) => ({
    name,
    fields: DISPLAY_FIELDS.filter((field) => field.group === name),
  }));
}

/** The settings the SPA renders and the dialog offers, in reading order. */
export const DISPLAY_FIELDS: readonly DisplayField[] = [
  {
    key: "refresh_interval_seconds",
    label: "Refresh every (seconds)",
    kind: "number",
    group: "Timing",
    hint: "How often the departures are fetched again.",
  },
  {
    key: "time_format_toggle_seconds",
    label: "Relative time switches after (seconds)",
    kind: "number",
    group: "Timing",
  },
  {
    key: "fetch_retry_attempts",
    label: "Tries per stop and cycle",
    kind: "number",
    group: "Timing",
  },
  {
    key: "fetch_retry_delay_ms",
    label: "Pause between tries (ms)",
    kind: "number",
    group: "Timing",
  },
  {
    key: "theme",
    label: "Theme",
    kind: "select",
    group: "Look",
    options: ["light", "dark", "auto"],
  },
  {
    key: "fill_vertical_space",
    label: "Fill the screen height",
    kind: "boolean",
    group: "Look",
  },
  {
    key: "font_scaling_factor_when_filling",
    label: "Font scale when filling",
    kind: "number",
    group: "Look",
  },
  {
    key: "random_header_colors",
    label: "Random header colours",
    kind: "boolean",
    group: "Look",
  },
  {
    key: "header_background_brightness",
    label: "Header brightness",
    kind: "number",
    group: "Look",
  },
  {
    key: "split_show_delay",
    label: "Show the split later",
    kind: "boolean",
    group: "Look",
  },
  {
    key: "route_icon_display",
    label: "Route icon",
    kind: "select",
    group: "Look",
    options: ["icon_with_text", "badge", "none"],
  },
  // The font sizes are strings ("4rem"), so they are typed rather than counted.
  // The fallback is the size the app's own CSS gives the field.
  {
    key: "font_size_route_number",
    label: "Line",
    kind: "text",
    group: "Fonts",
    fallback: "4rem",
  },
  {
    key: "font_size_destination",
    label: "Destination",
    kind: "text",
    group: "Fonts",
    fallback: "4rem",
  },
  {
    key: "font_size_platform",
    label: "Platform",
    kind: "text",
    group: "Fonts",
    fallback: "2.5rem",
  },
  {
    key: "font_size_time",
    label: "Time",
    kind: "text",
    group: "Fonts",
    fallback: "4rem",
  },
  {
    key: "font_size_stop_header",
    label: "Stop header",
    kind: "text",
    group: "Fonts",
    fallback: "3rem",
  },
  {
    key: "font_size_direction_header",
    label: "Direction header",
    kind: "text",
    group: "Fonts",
    fallback: "2.5rem",
  },
  {
    key: "font_size_status_header",
    label: "Status header",
    kind: "text",
    group: "Fonts",
    fallback: "1.875rem",
  },
  {
    key: "font_size_pagination_indicator",
    label: "Pages",
    kind: "text",
    group: "Fonts",
    fallback: "2rem",
  },
  {
    key: "font_size_countdown_text",
    label: "Countdown",
    kind: "text",
    group: "Fonts",
    fallback: "1.8rem",
  },
  {
    key: "font_size_delay_amount",
    label: "Delay",
    kind: "text",
    group: "Fonts",
    fallback: "2rem",
  },
  {
    key: "font_size_no_departures",
    label: "No departures",
    kind: "text",
    group: "Fonts",
    fallback: "2.5rem",
  },
];

export type DisplayValue = string | number | boolean;

/** The settings that are written; a missing key means "leave it as it is". */
export type DisplaySettings = Record<string, DisplayValue | undefined>;

/** Where display settings live: the file's defaults, or one page's own. */
export type DisplayScope = "global" | number;

/** The display table of the whole file, or of one page. */
function displayTable(
  lines: string[],
  scope: DisplayScope,
): TomlTable | undefined {
  const tables = readTomlTables(lines);

  if (scope === "global") {
    return tables.find((table) => table.name === "display");
  }

  const block = routeBlocks(lines)[scope];
  return block?.tables.find((table) => belongsTo(table.name, "routes.display"));
}

/** The text after `key =`, comments stripped. */
function rawValue(
  lines: string[],
  table: TomlTable,
  key: string,
): string | undefined {
  const pattern = new RegExp(`^\\s*${key}\\s*=\\s*([^#]*)`);

  for (let line = table.headerLine + 1; line < table.endLine; line += 1) {
    const match = pattern.exec(lines[line]);
    if (match) {
      return match[1].trim();
    }
  }

  return undefined;
}

function settingValue(
  lines: string[],
  table: TomlTable,
  field: DisplayField,
): DisplayValue | undefined {
  const raw = rawValue(lines, table, field.key);
  if (raw === undefined) {
    return undefined;
  }

  if (field.kind === "boolean") {
    return raw === "true";
  }
  if (field.kind === "number") {
    const number = Number(raw);
    return Number.isFinite(number) ? number : undefined;
  }

  return raw.startsWith('"') ? raw.slice(1, raw.lastIndexOf('"')) : raw;
}

function settingLiteral(value: DisplayValue): string {
  if (typeof value === "string") {
    return tomlString(value);
  }
  return String(value);
}

/** The display settings a scope sets; settings it does not set are absent. */
export function readDisplaySettings(
  toml: string,
  scope: DisplayScope,
): DisplaySettings {
  const lines = toml.split("\n");
  return displaySettings(lines, displayTable(lines, scope));
}

/**
 * The file with the scope's display settings replaced by `values`. A `undefined`
 * value removes the setting, a setting that already says what `values` says is
 * left alone, and a scope that had no display table gets one only if needed.
 */
export function updateDisplaySettings(
  toml: string,
  scope: DisplayScope,
  values: DisplaySettings,
): string {
  const current = readDisplaySettings(toml, scope);
  const edits = new Map<string, string | null>();

  for (const field of DISPLAY_FIELDS) {
    if (!(field.key in values)) {
      continue;
    }
    const wanted = values[field.key];
    if (wanted === undefined) {
      if (field.key in current) {
        edits.set(field.key, null);
      }
      continue;
    }
    if (current[field.key] !== wanted) {
      edits.set(field.key, settingLiteral(wanted));
    }
  }

  if (edits.size === 0) {
    return toml;
  }

  const withoutTable = displayTable(toml.split("\n"), scope) === undefined;
  if (withoutTable) {
    return insertDisplayTable(toml, scope, edits);
  }

  let result = toml;
  for (const [key, value] of edits) {
    const lines = result.split("\n");
    const table = displayTable(lines, scope);
    if (!table) {
      return result;
    }
    result = setKey(
      lines,
      { header: table.headerLine, end: table.endLine },
      key,
      value,
    ).join("\n");
  }

  return dropEmptyDisplayTable(result, scope);
}

/** A display table with every setting removed is not worth keeping. */
function dropEmptyDisplayTable(toml: string, scope: DisplayScope): string {
  const lines = toml.split("\n");
  const table = displayTable(lines, scope);
  if (
    !table ||
    hasKeys(lines, { header: table.headerLine, end: table.endLine })
  ) {
    return toml;
  }

  const from =
    scope === "global"
      ? table.headerLine
      : leadInStart(lines, table.headerLine);
  return renderToml(lines, lineRange(from, table.endLine), new Map());
}

function insertDisplayTable(
  toml: string,
  scope: DisplayScope,
  edits: Map<string, string | null>,
): string {
  const entries = [...edits].filter(([, value]) => value !== null);
  if (entries.length === 0) {
    return toml;
  }

  const body = entries.map(([key, value]) => `${key} = ${value}`);
  if (scope === "global") {
    return `${toml.trimEnd()}\n\n[display]\n${body.join("\n")}\n`;
  }

  const lines = toml.split("\n");
  const block = routeBlocks(lines)[scope];
  if (!block) {
    return toml;
  }

  const blockLines = lines.slice(block.startLine, block.endLine);
  const at = firstSubTableLine(blockLines);
  const next = [
    ...blockLines.slice(0, at),
    "[routes.display]",
    ...body,
    "",
    ...blockLines.slice(at),
  ];

  return rerender(lines, block.startLine, block.endLine, next);
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

/** Directions without blank rows, blank patterns or surrounding spaces. */
function cleanDirections(
  directions: ConfigDirectionMapping[],
): ConfigDirectionMapping[] {
  return directions
    .map(({ direction, patterns }) => ({
      direction: direction.trim(),
      patterns: patterns
        .map((pattern) => pattern.trim())
        .filter((pattern) => pattern !== ""),
    }))
    .filter(({ direction }) => direction !== "");
}

function sameDirections(
  current: ConfigDirectionMapping[],
  wanted: ConfigDirectionMapping[],
): boolean {
  const cleaned = cleanDirections(wanted);
  if (cleaned.length !== current.length) {
    return false;
  }

  return cleaned.every(
    (mapping, at) =>
      mapping.direction === current[at].direction &&
      samePatterns(mapping.patterns, current[at].patterns),
  );
}

function samePatterns(current: string[], wanted: string[]): boolean {
  return (
    current.length === wanted.length &&
    current.every((pattern, at) => pattern === wanted[at])
  );
}

/** The table that heads a stop's directions, or nothing when it has none. */
function directionTableLines(directions: ConfigDirectionMapping[]): string[] {
  const cleaned = cleanDirections(directions);
  if (cleaned.length === 0) {
    return [];
  }

  return [
    "[routes.stops.direction_mappings]",
    ...cleaned.map(
      ({ direction, patterns }) =>
        `${tomlKey(direction)} = [${patterns.map(tomlString).join(", ")}]`,
    ),
  ];
}

interface DirectionRow {
  key: string;
  /** The line holding `key = [...`. */
  keyLine: number;
  /** The line holding the closing bracket. */
  endLine: number;
  patterns: string[];
}

/** The headings a table holds, and the lines each one occupies. */
function directionRows(lines: string[]): DirectionRow[] {
  const rows: DirectionRow[] = [];
  const row = /^\s*(?:"([^"]*)"|'([^']*)'|([A-Za-z0-9_-]+))\s*=\s*(.*)$/;

  let line = 1;
  while (line < lines.length) {
    const match = row.exec(lines[line]);
    if (!match) {
      line += 1;
      continue;
    }

    const array = collectArray(lines, line, match[4], lines.length);
    rows.push({
      key: match[1] ?? match[2] ?? match[3],
      keyLine: line,
      endLine: array.lastLine,
      patterns: parseStrings(array.text),
    });
    line = array.lastLine + 1;
  }

  return rows;
}

/**
 * The heading table with the rows the form asks for, line by line: a heading the
 * form did not touch keeps its comments, its layout and its multi-line array; a
 * changed one keeps its key and its trailing comment; a removed one goes; a new
 * one is appended.
 */
function patchDirectionTable(
  tableLines: string[],
  wanted: ConfigDirectionMapping[],
): string[] {
  const rows = directionRows(tableLines);
  const pending = new Map(
    wanted.map((direction) => [direction.direction, direction]),
  );
  let lines = [...tableLines];

  for (let index = rows.length - 1; index >= 0; index -= 1) {
    const row = rows[index];
    const target = pending.get(row.key);
    const from = row.keyLine;
    const to = row.endLine + 1;

    if (!target) {
      // The note directly above a heading is the heading's own: it goes with it.
      const start = leadInStart(lines, from);
      lines = [...lines.slice(0, start), ...lines.slice(to)];
      continue;
    }

    pending.delete(row.key);
    if (samePatterns(row.patterns, target.patterns)) {
      continue;
    }

    const value = target.patterns.map(tomlString).join(", ");
    lines = [
      ...lines.slice(0, from),
      `${keyLiteral(tableLines[row.keyLine])} = [${value}]${trailingComment(tableLines[row.keyLine])}`,
      ...lines.slice(to),
    ];
  }

  if (pending.size === 0) {
    return lines;
  }

  const added = [...pending.values()].map(
    (direction) =>
      `${tomlKey(direction.direction)} = [${direction.patterns.map(tomlString).join(", ")}]`,
  );
  const at = lastContentLine(lines) + 1;

  return [...lines.slice(0, at), ...added, ...lines.slice(at)];
}

/** Everything before the `=` of a key line, spacing and quotes as written. */
function keyLiteral(line: string): string {
  return line.slice(0, line.indexOf("=")).trim();
}

/** The `# ...` at the end of a line, if it is really a comment. */
function trailingComment(line: string): string {
  let quoted: '"' | "'" | null = null;

  for (let at = 0; at < line.length; at += 1) {
    const character = line[at];
    if (quoted === null) {
      if (character === '"' || character === "'") {
        quoted = character;
        continue;
      }
      if (character === "#") {
        return ` ${line.slice(at)}`;
      }
    } else if (character === quoted) {
      quoted = null;
    }
  }

  return "";
}

function lastContentLine(lines: string[]): number {
  for (let line = lines.length - 1; line >= 0; line -= 1) {
    if (lines[line].trim() !== "") {
      return line;
    }
  }

  return -1;
}

/** Bare keys stay bare, everything else is quoted the way TOML wants it. */
function tomlKey(name: string): string {
  return /^[A-Za-z0-9_-]+$/.test(name) ? name : tomlString(name);
}

function replaceRange(
  lines: string[],
  from: number,
  to: number,
  replacement: string[],
): string[] {
  return [...lines.slice(0, from), ...replacement, ...lines.slice(to)];
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

/** What a display form holds: text, plus the numbers a number input yields. */
export type DisplayDraft = Record<string, string | number | boolean>;

/** A set of settings as a form shows it. */
export function draftOfSettings(settings: DisplaySettings): DisplayDraft {
  const draft: DisplayDraft = {};

  for (const field of DISPLAY_FIELDS) {
    const value = settings[field.key];
    draft[field.key] = value === undefined ? "" : String(value);
  }

  return draft;
}

/** The settings a form holds; an emptied field means "no longer set". */
export function settingsOfDraft(draft: DisplayDraft): DisplaySettings {
  const settings: DisplaySettings = {};

  for (const field of DISPLAY_FIELDS) {
    const held = draft[field.key];
    const text = held === undefined ? "" : String(held).trim();
    if (text === "") {
      settings[field.key] = undefined;
      continue;
    }
    if (field.kind === "boolean") {
      settings[field.key] = held === true || text === "true";
      continue;
    }
    settings[field.key] = field.kind === "number" ? Number(text) : text;
  }

  return settings;
}

/** A page the user asks for: its path, and a title if they want one. */
export interface NewConfigPage {
  path: string;
  title: string;
}

/**
 * The file with a new, empty page after the last one. A path that is already
 * taken, or none at all, leaves the file exactly as it is.
 */
export function addConfigPage(toml: string, page: NewConfigPage): string {
  const path = page.path.trim();
  if (path === "") {
    return toml;
  }

  const lines = toml.split("\n");
  const blocks = routeBlocks(lines);
  const taken = blocks.some(
    (block) => (stringValue(lines, block.tables[0], "path") ?? "/") === path,
  );
  if (taken) {
    return toml;
  }

  const snippet = ["", "[[routes]]", `path = ${tomlString(path)}`];
  const title = page.title.trim();
  if (title !== "" && title !== path) {
    snippet.push("", "[routes.display]", `title = ${tomlString(title)}`);
  }

  const at =
    blocks.length > 0 ? blocks[blocks.length - 1].endLine : lines.length;
  return rerender(lines, at, at, snippet);
}
