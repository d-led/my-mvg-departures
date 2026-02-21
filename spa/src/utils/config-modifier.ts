import { parse as tomlParse } from "toml-patch";
import type {
  TomlData,
  TomlRouteData,
  TomlStopData,
} from "../adapters/config/toml-types.js";

// Custom TOML stringify that properly handles direction_mappings
// This needs to preserve the TOML structure while serializing direction_mappings as sections
function stringifyToml(data: TomlData): string {
  // For main stops (parsed from TOML), we need special handling of direction_mappings
  // The toml-patch library's stringify doesn't properly handle this
  const lines: string[] = [];

  // Serialize display section if present
  if (data.display && typeof data.display === "object") {
    lines.push("[display]");
    const displayObj = data.display as Record<string, unknown>;
    for (const [key, value] of Object.entries(displayObj)) {
      lines.push(serializeKeyValue(key, value));
    }
    lines.push("");
  }

  // Serialize api section if present
  if (data.api && typeof data.api === "object") {
    lines.push("[api]");
    const apiObj = data.api as Record<string, unknown>;
    for (const [key, value] of Object.entries(apiObj)) {
      lines.push(serializeKeyValue(key, value));
    }
    lines.push("");
  }

  // Serialize main stops
  if (data.stops && Array.isArray(data.stops)) {
    for (const stop of data.stops) {
      lines.push("[[stops]]");
      const stopObj = stop as unknown as Record<string, unknown>;
      const directionMappings = stopObj.direction_mappings as
        | Record<string, unknown>
        | undefined;

      for (const [key, value] of Object.entries(stopObj)) {
        if (key !== "direction_mappings") {
          lines.push(serializeKeyValue(key, value));
        }
      }

      // Serialize direction_mappings as a TOML section if present
      if (directionMappings && Object.keys(directionMappings).length > 0) {
        lines.push("[stops.direction_mappings]");
        for (const [key, value] of Object.entries(directionMappings)) {
          lines.push(serializeKeyValue(key, value));
        }
      }

      lines.push("");
    }
  }

  // Serialize routes
  if (data.routes && Array.isArray(data.routes)) {
    for (const route of data.routes) {
      const routeObj = route as Record<string, unknown>;
      lines.push("[[routes]]");

      for (const [key, value] of Object.entries(routeObj)) {
        if (key !== "stops" && key !== "display") {
          lines.push(serializeKeyValue(key, value));
        }
      }

      // Serialize route.display if present
      // display should be an array-of-tables (from [[routes.display]])
      if (routeObj.display && Array.isArray(routeObj.display)) {
        // Array-of-tables: [[routes.display]]
        const displayArray = routeObj.display as Record<string, unknown>[];
        for (const displayObj of displayArray) {
          lines.push("[[routes.display]]");
          for (const [key, value] of Object.entries(displayObj)) {
            // Skip 'stops' - it should be serialized at route level, not inside display
            if (key !== "stops") {
              lines.push(serializeKeyValue(key, value));
            }
          }
        }
      } else if (routeObj.display && typeof routeObj.display === "object") {
        // Inline object (shouldn't happen in normal config, but handle it)
        lines.push("[routes.display]");
        const displayObj = routeObj.display as Record<string, unknown>;
        for (const [key, value] of Object.entries(displayObj)) {
          // Skip 'stops' - it should be serialized at route level, not inside display
          if (key !== "stops") {
            lines.push(serializeKeyValue(key, value));
          }
        }
      }

      // Serialize route stops as array-of-tables [[routes.stops]]
      // This allows direction_mappings to be proper TOML sections
      const routeStops = routeObj.stops as TomlStopData[] | undefined;
      if (routeStops && Array.isArray(routeStops)) {
        for (const stop of routeStops) {
          lines.push("[[routes.stops]]");
          const stopObj = stop as unknown as Record<string, unknown>;
          const directionMappings = stopObj.direction_mappings as
            | Record<string, unknown>
            | undefined;

          for (const [key, value] of Object.entries(stopObj)) {
            if (key !== "direction_mappings") {
              lines.push(serializeKeyValue(key, value));
            }
          }

          // Serialize direction_mappings as a TOML section if present
          if (directionMappings && Object.keys(directionMappings).length > 0) {
            lines.push("[routes.stops.direction_mappings]");
            for (const [key, value] of Object.entries(directionMappings)) {
              lines.push(serializeKeyValue(key, value));
            }
          }
        }
      }

      lines.push("");
    }
  }

  // Remove trailing empty lines
  while (lines.length > 0 && lines[lines.length - 1] === "") {
    lines.pop();
  }

  return lines.join("\n");
}

// Generate TOML snippet for a single route
function serializeRoute(route: TomlRouteData): string {
  const lines: string[] = [];
  const routeObj = route as unknown as Record<string, unknown>;

  lines.push("[[routes]]");

  // Serialize route-level properties (except display and stops)
  for (const [key, value] of Object.entries(routeObj)) {
    if (key !== "stops" && key !== "display") {
      lines.push(serializeKeyValue(key, value));
    }
  }

  // Serialize display as [[routes.display]] if present
  if (routeObj.display && Array.isArray(routeObj.display)) {
    const displayArray = routeObj.display as Record<string, unknown>[];
    for (const displayObj of displayArray) {
      lines.push("[[routes.display]]");
      for (const [key, value] of Object.entries(displayObj)) {
        if (key !== "stops") {
          lines.push(serializeKeyValue(key, value));
        }
      }
    }
  }

  // Serialize stops as [[routes.stops]]
  const routeStops = routeObj.stops as TomlStopData[] | undefined;
  if (routeStops && Array.isArray(routeStops)) {
    for (const stop of routeStops) {
      lines.push("[[routes.stops]]");
      const stopObj = stop as unknown as Record<string, unknown>;
      const directionMappings = stopObj.direction_mappings as
        | Record<string, unknown>
        | undefined;

      for (const [key, value] of Object.entries(stopObj)) {
        if (key !== "direction_mappings") {
          lines.push(serializeKeyValue(key, value));
        }
      }

      if (directionMappings && Object.keys(directionMappings).length > 0) {
        lines.push("[routes.stops.direction_mappings]");
        for (const [key, value] of Object.entries(directionMappings)) {
          lines.push(serializeKeyValue(key, value));
        }
      }
    }
  }

  return lines.join("\n");
}

// Insert a new route at the end of the file (preserving all existing content)
function insertRouteSnippet(
  existingToml: string,
  route: TomlRouteData,
): string {
  const snippet = serializeRoute(route);
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
  const routeStarts: number[] = [];

  // Find all [[routes]] markers
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].trim() === "[[routes]]") {
      routeStarts.push(i);
    }
  }

  if (routeIndex >= routeStarts.length) {
    throw new Error(`Route index ${routeIndex} not found`);
  }

  const startLine = routeStarts[routeIndex];
  const endLine =
    routeIndex + 1 < routeStarts.length
      ? routeStarts[routeIndex + 1]
      : lines.length;

  // Generate the new route snippet
  const snippet = serializeRoute(updatedRoute);

  // Replace the route section
  const before = lines.slice(0, startLine).join("\n");
  const after = lines.slice(endLine).join("\n");

  return `${before}\n${snippet}\n${after}`;
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
  mainStopIds: string[];
  routeStopIdsByPath: Record<string, string[]>;
  hasOnTheRun: boolean;
};

function normalizeRoutePath(path: string): string {
  if (!path) {
    return "/";
  }
  return path.startsWith("/") ? path : `/${path}`;
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
  const parsed = existingToml.trim()
    ? (tomlParse(existingToml) as TomlData)
    : ({} as TomlData);

  let output: string;
  if (result.target === "main") {
    const existingStops = parsed.stops ?? [];
    parsed.stops = upsertStops(existingStops, result.stops);
    // Use custom stringify to properly handle direction_mappings as sections
    output = stringifyToml(parsed);
  } else {
    const routeDetails = result.route;
    if (!routeDetails?.path) {
      throw new Error("Route target requires a path.");
    }

    const normalizedPath = normalizeRoutePath(routeDetails.path);
    if (normalizedPath === "/" || normalizedPath === "/on-the-run") {
      throw new Error("Wizard route updates are not allowed for this target.");
    }

    const routes = parsed.routes ?? [];
    const routeIndex = routes.findIndex(
      (route) => route.path === normalizedPath,
    );

    if (routeIndex === -1) {
      // Adding a new route - generate snippet and insert at end
      const newRoute: TomlRouteData = ensureRouteDisplay(
        {
          path: normalizedPath,
          stops: upsertStops([], result.stops),
        },
        routeDetails.title,
      );
      output = insertRouteSnippet(existingToml, newRoute);
    } else {
      // Updating existing route - generate snippet and replace
      const existingRoute = routes[routeIndex];
      const existingStops = existingRoute.stops ?? [];
      const updatedRoute: TomlRouteData = ensureRouteDisplay(
        {
          ...existingRoute,
          stops: upsertStops(existingStops, result.stops),
        },
        routeDetails.title,
      );
      output = replaceRouteSnippet(existingToml, routeIndex, updatedRoute);
    }
  }

  // Validate TOML syntax after patching/stringifying
  try {
    tomlParse(output);
  } catch (e) {
    throw new Error(
      `Wizard produced invalid TOML: ${e instanceof Error ? e.message : String(e)}`,
    );
  }
  return output;
}

export function getWizardConfigContext(
  existingToml: string,
): WizardConfigContext {
  const parsed = existingToml.trim()
    ? (tomlParse(existingToml) as TomlData)
    : ({} as TomlData);

  const mainStopIds = (parsed.stops ?? [])
    .map((stop) => stop.station_id)
    .filter(Boolean);

  const routeStopIdsByPath: Record<string, string[]> = {};
  for (const route of parsed.routes ?? []) {
    if (!route.path) continue;
    routeStopIdsByPath[route.path] = (route.stops ?? [])
      .map((stop) => stop.station_id)
      .filter(Boolean);
  }

  const hasOnTheRun = Boolean(parsed.on_the_run);

  return {
    mainStopIds,
    routeStopIdsByPath,
    hasOnTheRun,
  };
}
