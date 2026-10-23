/**
 * The "Next to me" page lives in one optional `[[on_the_run]]` table. Deleting
 * it (by hand, or by an editor that rewrote the file) used to mean losing the
 * page for good; this brings it back.
 */

import {
  belongsTo,
  readTomlTables,
  setTomlKey,
  tomlString,
  type TomlTable,
} from "./toml-sections.js";

const ON_THE_RUN_TABLE = "on_the_run";

/** The block written when the page is added back. */
const ON_THE_RUN_SECTION = [
  "# Nearby departures, using the browser's location",
  "[[on_the_run]]",
  "radius_meters = 50",
  "max_departures_per_stop = 8",
  "max_departures_per_route = 2",
  "refresh_interval_seconds = 20",
];

export function hasOnTheRun(toml: string): boolean {
  return readTomlTables(toml.split("\n")).some((table) =>
    belongsTo(table.name, ON_THE_RUN_TABLE),
  );
}

/** Adds the page when it is missing; an existing one is kept as it is. */
export function addOnTheRunSection(toml: string): string {
  if (hasOnTheRun(toml)) {
    return toml;
  }

  if (!toml.trim()) {
    return [...ON_THE_RUN_SECTION, ""].join("\n");
  }

  return `${toml.trimEnd()}\n\n${ON_THE_RUN_SECTION.join("\n")}\n`;
}

/** A setting of the Next to me page, and how its form presents it. */
export interface OnTheRunField {
  key: string;
  label: string;
  kind: "number" | "boolean" | "adapters";
  hint?: string;
}

export const ON_THE_RUN_FIELDS: readonly OnTheRunField[] = [
  { key: "radius_meters", label: "Radius (metres)", kind: "number" },
  {
    key: "max_departures_per_stop",
    label: "Departures per stop",
    kind: "number",
  },
  {
    key: "max_departures_per_route",
    label: "Departures per line",
    kind: "number",
  },
  {
    key: "refresh_interval_seconds",
    label: "Look around again every (seconds)",
    kind: "number",
  },
  {
    key: "update_location_on_every_poll",
    label: "Move with you on every refresh",
    kind: "boolean",
  },
  {
    key: "use_precise_location",
    label: "Use the precise location",
    kind: "boolean",
  },
  { key: "smart_sub_stops", label: "Split big stops", kind: "boolean" },
  {
    key: "random_header_colors",
    label: "Random header colours",
    kind: "boolean",
  },
  {
    key: "use_adapters",
    label: "APIs",
    kind: "adapters",
    hint: "mvg, vbb - one per network",
  },
];

export type OnTheRunValue = number | boolean | string[];

/** The settings written; a missing key means "leave it as it is". */
export type OnTheRunSettings = Record<string, OnTheRunValue | undefined>;

/** What the form holds; the adapters are a comma-separated list. */
export type OnTheRunDraft = Record<string, string | number | boolean>;

function onTheRunTable(lines: string[]): TomlTable | undefined {
  return readTomlTables(lines).find((table) =>
    belongsTo(table.name, ON_THE_RUN_TABLE),
  );
}

function rawValue(
  lines: string[],
  table: TomlTable,
  key: string,
): string | undefined {
  const pattern = new RegExp(`^\\s*${key}\\s*=\\s*(.+)$`);

  for (let line = table.headerLine + 1; line < table.endLine; line += 1) {
    const match = pattern.exec(lines[line]);
    if (match) {
      return match[1].trim();
    }
  }

  return undefined;
}

function readValue(
  lines: string[],
  table: TomlTable,
  field: OnTheRunField,
): OnTheRunValue | undefined {
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

  return [...raw.matchAll(/"([^"]*)"/g)].map((match) => match[1]);
}

/** What the file's Next to me page is set to; {} when there is no such page. */
export function readOnTheRunSettings(toml: string): OnTheRunSettings {
  const lines = toml.split("\n");
  const table = onTheRunTable(lines);
  if (!table) {
    return {};
  }

  const settings: OnTheRunSettings = {};
  for (const field of ON_THE_RUN_FIELDS) {
    const value = readValue(lines, table, field);
    if (value !== undefined) {
      settings[field.key] = value;
    }
  }

  return settings;
}

/**
 * The file with the Next to me page's settings replaced. There is no page to
 * write into when the file has none - that is what `addOnTheRunSection` is for.
 */
export function updateOnTheRunSettings(
  toml: string,
  values: OnTheRunSettings,
): string {
  const current = readOnTheRunSettings(toml);
  const edits = new Map<string, string | null>();

  for (const field of ON_THE_RUN_FIELDS) {
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
    if (!sameValue(current[field.key], wanted)) {
      edits.set(field.key, literal(field, wanted));
    }
  }

  let result = toml;
  for (const [key, value] of edits) {
    const lines = result.split("\n");
    const table = onTheRunTable(lines);
    if (!table) {
      return result;
    }
    result = setTomlKey(
      lines,
      { header: table.headerLine, end: table.endLine },
      key,
      value,
    ).join("\n");
  }

  return result;
}

function sameValue(
  current: OnTheRunValue | undefined,
  wanted: OnTheRunValue,
): boolean {
  return Array.isArray(wanted) && Array.isArray(current)
    ? wanted.join(",") === current.join(",")
    : current === wanted;
}

function literal(field: OnTheRunField, value: OnTheRunValue): string {
  if (field.kind === "adapters" && Array.isArray(value)) {
    return `[${value.map((adapter) => tomlString(adapter)).join(", ")}]`;
  }
  return String(value);
}

/** The settings as the form shows them. */
export function draftOfOnTheRun(settings: OnTheRunSettings): OnTheRunDraft {
  const draft: OnTheRunDraft = {};

  for (const field of ON_THE_RUN_FIELDS) {
    const value = settings[field.key];
    if (value === undefined) {
      draft[field.key] = "";
      continue;
    }
    draft[field.key] = Array.isArray(value) ? value.join(", ") : value;
  }

  return draft;
}

/** The settings the form holds; an emptied field means "no longer set". */
export function settingsOfOnTheRunDraft(
  draft: OnTheRunDraft,
): OnTheRunSettings {
  const settings: OnTheRunSettings = {};

  for (const field of ON_THE_RUN_FIELDS) {
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
    if (field.kind === "number") {
      settings[field.key] = Number(text);
      continue;
    }
    settings[field.key] = text
      .split(",")
      .map((adapter) => adapter.trim())
      .filter((adapter) => adapter !== "");
  }

  return settings;
}
