import { parse as tomlParse } from "toml-patch";
import type {
  TomlData,
  TomlRouteData,
  TomlStopData,
} from "../adapters/config/toml-types.js";
import { cleanUpConfigToml } from "./config-cleanup.js";
import { belongsTo, tomlTableName } from "./toml-sections.js";

/** The route the app opens by default. */
const DEFAULT_ROUTE_PATH = "/";

/** The lines of one `[[routes]]` block, stops and direction mappings included. */
function serializeRouteLines(route: TomlRouteData): string[] {
  const lines: string[] = ["[[routes]]"];
  const routeObj = route as unknown as Record<string, unknown>;

  for (const [key, value] of Object.entries(routeObj)) {
    if (key !== "stops" && key !== "display") {
      lines.push(serializeKeyValue(key, value));
    }
  }

  // `[routes.display]` and `[[routes.display]]` are both in use; keep the shape
  // the config already had.
  const routeDisplay = routeObj.display as
    Record<string, unknown> | Record<string, unknown>[] | undefined;
  if (Array.isArray(routeDisplay)) {
    for (const display of routeDisplay) {
      lines.push("[[routes.display]]", ...displayLines(display));
    }
  } else if (routeDisplay) {
    lines.push("[routes.display]", ...displayLines(routeDisplay));
  }

  for (const stop of (routeObj.stops as TomlStopData[] | undefined) ?? []) {
    lines.push("[[routes.stops]]", ...stopLines(stop));
  }

  return lines;
}

function displayLines(display: Record<string, unknown>): string[] {
  return Object.entries(display)
    .filter(([key]) => key !== "stops")
    .map(([key, value]) => serializeKeyValue(key, value));
}

function stopLines(stop: TomlStopData): string[] {
  const stopObj = stop as unknown as Record<string, unknown>;
  const lines = Object.entries(stopObj)
    .filter(([key]) => key !== "direction_mappings")
    .map(([key, value]) => serializeKeyValue(key, value));

  const directionMappings = stopObj.direction_mappings as
    Record<string, unknown> | undefined;
  if (directionMappings && Object.keys(directionMappings).length > 0) {
    lines.push("[routes.stops.direction_mappings]");
    for (const [direction, values] of Object.entries(directionMappings)) {
      lines.push(serializeKeyValue(direction, values));
    }
  }

  return lines;
}

// Insert a new route at the end of the file (preserving all existing content)
function insertRouteSnippet(
  existingToml: string,
  route: TomlRouteData,
): string {
  const snippet = serializeRouteLines(route).join("\n");
  const trimmed = existingToml.trimEnd();
  return `${trimmed}\n\n${snippet}\n`;
}

// Replace an existing route with updated version (preserving everything else)
function replaceRouteSnippet(
  existingToml: string,
  routeIndex: number,
  updatedRoute: TomlRouteData,
): string {
  const lines = existingToml.split("\n");
  const routeStarts = lines
    .map((line, index) => (isRouteHeader(line) ? index : -1))
    .filter((index) => index >= 0);

  if (routeIndex >= routeStarts.length) {
    throw new Error(`Route index ${routeIndex} not found`);
  }

  const startLine = routeStarts[routeIndex];
  const endLine = routeBlockEnd(lines, startLine);

  // Generate the new route snippet
  const snippet = serializeRouteLines(updatedRoute).join("\n");

  // Replace the route section
  const before = lines.slice(0, startLine).join("\n");
  const after = lines.slice(endLine).join("\n");

  return `${before}\n${snippet}\n${after}`;
}

/** `[[routes]]` - the header that opens a route block. */
function isRouteHeader(line: string): boolean {
  return tomlTableName(line) === "routes";
}

/**
 * The line after the route's own tables. Whatever follows - another route, the
 * Next to me table, anything else - belongs to another table and is kept.
 */
function routeBlockEnd(lines: string[], startLine: number): number {
  for (let line = startLine + 1; line < lines.length; line += 1) {
    const name = tomlTableName(lines[line]);
    if (name !== undefined && !belongsTo(name, "routes")) {
      return line;
    }
  }
  return lines.length;
}

function needsQuoting(key: string): boolean {
  // TOML keys need quotes if they contain special characters
  return !/^[A-Za-z0-9_-]+$/.test(key);
}

function quoteKey(key: string): string {
  if (needsQuoting(key)) {
    const escaped = key.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
    return `"${escaped}"`;
  }
  return key;
}

function serializeKeyValue(key: string, value: unknown): string {
  const quotedKey = quoteKey(key);

  if (value === null || value === undefined) {
    return `${quotedKey} = ""`;
  }
  if (typeof value === "string") {
    const escaped = value.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
    return `${quotedKey} = "${escaped}"`;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return `${quotedKey} = ${value}`;
  }
  if (Array.isArray(value)) {
    const items = value.map((v) => {
      if (typeof v === "string") {
        const escaped = v.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
        return `"${escaped}"`;
      }
      return String(v);
    });
    return `${quotedKey} = [${items.join(", ")}]`;
  }
  // For inline table objects
  if (typeof value === "object") {
    const obj = value as Record<string, unknown>;
    const entries = Object.entries(obj)
      .map(([k, v]) => {
        const quotedInlineKey = quoteKey(k);
        if (typeof v === "string") {
          const escaped = v.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
          return `${quotedInlineKey} = "${escaped}"`;
        }
        if (typeof v === "number" || typeof v === "boolean") {
          return `${quotedInlineKey} = ${v}`;
        }
        if (Array.isArray(v)) {
          const items = (v as unknown[]).map((vi) => {
            if (typeof vi === "string") {
              const escaped = vi.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
              return `"${escaped}"`;
            }
            return String(vi);
          });
          return `${quotedInlineKey} = [${items.join(", ")}]`;
        }
        // Skip complex nested objects in inline tables
        return null;
      })
      .filter((entry): entry is string => entry !== null)
      .join(", ");
    return `${quotedKey} = { ${entries} }`;
  }
  return `${quotedKey} = ""`;
}

export type WizardStop = {
  station_id: string;
  station_name: string;
  max_departures_per_stop: number;
  max_departures_per_route: number;
  max_hours_in_advance: number;
  show_ungrouped: boolean;
  custom_title?: string;
  direction_mappings?: Record<string, string[]>;
  platform_filter_routes?: string[];
};

export type WizardTarget = "main" | "route";

export type WizardRouteDetails = {
  path: string;
  title?: string;
};

export type WizardResult = {
  target: WizardTarget;
  route?: WizardRouteDetails;
  stops: WizardStop[];
};

export type WizardConfigContext = {
  routeStopIdsByPath: Record<string, string[]>;
  hasOnTheRun: boolean;
};

function normalizeRoutePath(path: string): string {
  if (!path) {
    return DEFAULT_ROUTE_PATH;
  }
  return path.startsWith("/") ? path : `/${path}`;
}

function isOnTheRunPath(path: string): boolean {
  return path === "/on-the-run";
}

function mapWizardStop(stop: WizardStop): TomlStopData {
  const mapped: TomlStopData = {
    station_id: stop.station_id,
    station_name: stop.station_name,
    max_departures_per_stop: stop.max_departures_per_stop,
    max_departures_per_route: stop.max_departures_per_route,
    max_hours_in_advance: stop.max_hours_in_advance,
    show_ungrouped: stop.show_ungrouped,
  };

  if (stop.custom_title != null && stop.custom_title !== "") {
    mapped.ungrouped_title = String(stop.custom_title);
  }

  if (
    stop.direction_mappings &&
    Object.keys(stop.direction_mappings).length > 0
  ) {
    mapped.direction_mappings = stop.direction_mappings;
  }

  if (stop.platform_filter_routes && stop.platform_filter_routes.length > 0) {
    mapped.platform_filter_routes = stop.platform_filter_routes;
  }

  return mapped;
}

function mergeStop(
  existingStop: TomlStopData,
  newStop: TomlStopData,
): TomlStopData {
  const existingMappings =
    (existingStop.direction_mappings as Record<string, string[]> | undefined) ??
    {};
  const newMappings =
    (newStop.direction_mappings as Record<string, string[]> | undefined) ?? {};
  const mergedMappings = { ...existingMappings, ...newMappings };

  const merged: TomlStopData = {
    ...existingStop,
    ...newStop,
  };

  if (Object.keys(mergedMappings).length > 0) {
    merged.direction_mappings = mergedMappings;
  }

  return merged;
}

function upsertStops(
  existingStops: TomlStopData[],
  wizardStops: WizardStop[],
): TomlStopData[] {
  const updatedStops = [...existingStops];
  const stopIndexById = new Map(
    existingStops.map((stop, index) => [stop.station_id, index]),
  );

  for (const stop of wizardStops) {
    const mappedStop = mapWizardStop(stop);
    const existingIndex = stopIndexById.get(stop.station_id);

    if (existingIndex !== undefined) {
      updatedStops[existingIndex] = mergeStop(
        updatedStops[existingIndex],
        mappedStop,
      );
    } else {
      updatedStops.push(mappedStop);
    }
  }

  return updatedStops;
}

function ensureRouteDisplay(
  route: TomlRouteData,
  title?: string,
): TomlRouteData {
  if (!title) {
    return route;
  }

  // Always use array format [[routes.display]] to match config.example.toml structure
  // This ensures compatibility when merging with existing configs
  const existingDisplay = route.display;

  if (Array.isArray(existingDisplay)) {
    // Update first element's title
    if (existingDisplay.length === 0) {
      return { ...route, display: [{ title }] };
    }
    const updatedDisplay = [...existingDisplay];
    updatedDisplay[0] = { ...updatedDisplay[0], title };
    return { ...route, display: updatedDisplay };
  }

  // If display is an inline table, convert to array format
  if (existingDisplay && typeof existingDisplay === "object") {
    // Exclude 'stops' from display - it belongs at route level
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { stops, ...displayWithoutStops } = existingDisplay as Record<
      string,
      unknown
    >;
    return {
      ...route,
      display: [{ ...displayWithoutStops, title }],
    };
  }

  // No existing display, create array format
  return { ...route, display: [{ title }] };
}

export function applyWizardConfig(
  existingToml: string,
  result: WizardResult,
): string {
  // The wizard only speaks the SPA's shape: legacy top-level stops become the
  // route at "/" before anything is merged.
  const source = cleanUpConfigToml(existingToml).toml;
  const path = targetRoutePath(result);
  const parsed = source.trim()
    ? (tomlParse(source) as TomlData)
    : ({} as TomlData);

  const routes = parsed.routes ?? [];
  const routeIndex = routes.findIndex(
    (route) => (route.path ?? DEFAULT_ROUTE_PATH) === path,
  );
  const updatedRoute = withWizardStops(routes[routeIndex], path, result);

  // Only the target route is rewritten; every other table of the file - the
  // Next to me settings among them - is left exactly as it is.
  const output =
    routeIndex === -1
      ? insertRouteSnippet(source, updatedRoute)
      : replaceRouteSnippet(source, routeIndex, updatedRoute);

  // Validate TOML syntax after patching
  try {
    tomlParse(output);
  } catch (e) {
    throw new Error(
      `Wizard produced invalid TOML: ${e instanceof Error ? e.message : String(e)}`,
      { cause: e },
    );
  }
  return output;
}

/** The route the wizard writes to: the route at "/" for the main target. */
function targetRoutePath(result: WizardResult): string {
  if (result.target === "main") {
    return DEFAULT_ROUTE_PATH;
  }

  const path = result.route?.path;
  if (!path) {
    throw new Error("Route target requires a path.");
  }

  const normalizedPath = normalizeRoutePath(path);
  if (normalizedPath === DEFAULT_ROUTE_PATH || isOnTheRunPath(normalizedPath)) {
    throw new Error("Wizard route updates are not allowed for this target.");
  }

  return normalizedPath;
}

/** The route with the wizard's stops merged in, keeping what it already had. */
function withWizardStops(
  existing: TomlRouteData | undefined,
  path: string,
  result: WizardResult,
): TomlRouteData {
  return ensureRouteDisplay(
    {
      ...existing,
      path,
      stops: upsertStops(existing?.stops ?? [], result.stops),
    },
    result.route?.title,
  );
}

export function getWizardConfigContext(
  existingToml: string,
): WizardConfigContext {
  const source = cleanUpConfigToml(existingToml).toml;
  const parsed = source.trim()
    ? (tomlParse(source) as TomlData)
    : ({} as TomlData);

  const routeStopIdsByPath: Record<string, string[]> = {};
  for (const route of parsed.routes ?? []) {
    routeStopIdsByPath[route.path ?? DEFAULT_ROUTE_PATH] = (route.stops ?? [])
      .map((stop) => stop.station_id)
      .filter(Boolean);
  }

  return {
    routeStopIdsByPath,
    hasOnTheRun: Boolean(parsed.on_the_run),
  };
}
