/**
 * Writes a configuration the way the app wants it read: `[display]` first, then
 * one block per page, then the Next to me table. Values keep what they mean -
 * keys this module has never heard of are written too, after the known ones.
 */
import { parse as tomlParse } from "toml-patch";
import { tomlString } from "./toml-sections.js";

/** The order a display table reads best in. */
const DISPLAY_ORDER = [
  "title",
  "theme",
  "time_format_toggle_seconds",
  "fill_vertical_space",
  "font_scaling_factor_when_filling",
  "random_header_colors",
  "header_background_brightness",
  "refresh_interval_seconds",
  "fetch_retry_attempts",
  "fetch_retry_delay_ms",
  "split_show_delay",
  "route_icon_display",
];

/** The order a stop reads best in. */
const STOP_ORDER = [
  "station_id",
  "station_name",
  "max_departures_per_stop",
  "max_departures_per_route",
  "max_hours_in_advance",
  "show_ungrouped",
  "ungrouped_title",
  "platform_filter",
  "platform_filter_routes",
  "api_provider",
  "exclude_destinations",
];

/** The order the Next to me page reads best in. */
const ON_THE_RUN_ORDER = [
  "radius_meters",
  "max_departures_per_stop",
  "max_departures_per_route",
  "refresh_interval_seconds",
  "update_location_on_every_poll",
  "use_precise_location",
  "smart_sub_stops",
  "random_header_colors",
  "use_adapters",
];

/** The canonical text of a configuration; throws when the TOML is not valid. */
export function formatConfigToml(toml: string): string {
  if (toml.trim() === "") {
    return "";
  }

  const data = tomlParse(toml) as Record<string, unknown>;
  const blocks: string[] = [];

  blocks.push(...section("display", data.display, DISPLAY_ORDER, false));

  for (const route of asTables(data.routes)) {
    blocks.push(routeBlock(route));
  }

  blocks.push(
    ...section("on_the_run", data.on_the_run, ON_THE_RUN_ORDER, true),
  );

  return `${blocks.filter((block) => block !== "").join("\n\n")}\n`;
}

function routeBlock(route: Record<string, unknown>): string {
  const lines = ["[[routes]]"];

  for (const key of valueKeys(route, ["path"])) {
    lines.push(`${keyOf(key)} = ${literal(route[key])}`);
  }

  // The shape the file used - `[display]` or `[[display]]` - is kept.
  const parts = [
    lines.join("\n"),
    ...section("routes.display", route.display, DISPLAY_ORDER, false),
  ];

  for (const stop of asTables(route.stops)) {
    parts.push(stopBlock(stop));
  }

  return parts.join("\n\n");
}

function stopBlock(stop: Record<string, unknown>): string {
  const lines = ["[[routes.stops]]"];
  const mappings = asTable(stop.direction_mappings);

  for (const key of valueKeys(stop, STOP_ORDER)) {
    lines.push(`${keyOf(key)} = ${literal(stop[key])}`);
  }

  const parts = [lines.join("\n")];
  if (mappings) {
    parts.push(table("routes.stops.direction_mappings", [], mappings, []));
  }

  return parts.join("\n\n");
}

/**
 * One table, or every table of an array-of-tables, written with the shape the
 * value has: `[name]` for a table, `[[name]]` for a list of them.
 */
function section(
  name: string,
  value: unknown,
  order: readonly string[],
  preferArray: boolean,
): string[] {
  const tables = asTable(value) ? [asTable(value)!] : asTables(value);
  if (tables.length === 0) {
    return [];
  }

  const asArray = preferArray || Array.isArray(value);
  return tables.map((data) => table(name, [], data, order, asArray));
}

function table(
  name: string,
  parents: string[],
  data: Record<string, unknown>,
  order: readonly string[],
  arrayOfTables = false,
): string {
  const header = arrayOfTables ? `[[${name}]]` : `[${name}]`;
  const lines = [header];

  for (const key of valueKeys(data, order)) {
    lines.push(`${keyOf(key)} = ${literal(data[key])}`);
  }

  for (const [key, value] of Object.entries(data)) {
    const nested = asTable(value) ?? asTables(value)[0];
    if (nested) {
      lines.push("", table([...parents, name, key].join("."), [], nested, []));
    }
  }

  return lines.join("\n");
}

/** Keys whose value is written as `key = value`, known ones first. */
function valueKeys(
  data: Record<string, unknown>,
  order: readonly string[],
): string[] {
  const written = Object.keys(data).filter(
    (key) => data[key] !== undefined && !isTableish(data[key]),
  );
  const known = order.filter((key) => written.includes(key));

  return [...known, ...written.filter((key) => !order.includes(key))];
}

/** Tables and arrays of tables are written as sections, not as values. */
function isTableish(value: unknown): boolean {
  return (
    asTable(value) !== undefined ||
    (Array.isArray(value) && value.some((item) => asTable(item) !== undefined))
  );
}

function keyOf(key: string): string {
  return /^[A-Za-z0-9_-]+$/.test(key) ? key : tomlString(key);
}

function literal(value: unknown): string {
  if (typeof value === "string") {
    return tomlString(value);
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((item) => literal(item)).join(", ")}]`;
  }
  if (value instanceof Date) {
    return value.toISOString();
  }

  throw new Error(`Cannot write a ${typeof value} into TOML`);
}

function asTable(value: unknown): Record<string, unknown> | undefined {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return undefined;
  }
  return value as Record<string, unknown>;
}

function asTables(value: unknown): Record<string, unknown>[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((entry) => asTable(entry))
    .filter((entry): entry is Record<string, unknown> => entry !== undefined);
}
