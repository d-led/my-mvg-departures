import {
  parse as tomlParse,
  patch as tomlPatch,
  stringify as tomlStringify,
} from "toml-patch";
import type {
  TomlData,
  TomlRouteData,
  TomlStopData,
} from "../adapters/config/toml-types.js";

export type WizardStop = {
  station_id: string;
  station_name: string;
  max_departures_per_stop: number;
  max_departures_per_route: number;
  max_hours_in_advance: number;
  show_ungrouped: boolean;
  custom_title?: string;
  direction_mappings?: Record<string, string[]>;
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

  if (stop.custom_title) {
    mapped.ungrouped_title = stop.custom_title;
  }

  if (
    stop.direction_mappings &&
    Object.keys(stop.direction_mappings).length > 0
  ) {
    mapped.direction_mappings = stop.direction_mappings;
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
    return {
      ...route,
      display: [{ ...existingDisplay, title }],
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
    // For main stops, tomlPatch can handle simple array-of-tables updates
    output = existingToml.trim()
      ? tomlPatch(existingToml, parsed)
      : tomlStringify(parsed);
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
      const newRoute: TomlRouteData = ensureRouteDisplay(
        {
          path: normalizedPath,
          stops: upsertStops([], result.stops),
        },
        routeDetails.title,
      );
      parsed.routes = [...routes, newRoute];
    } else {
      const existingRoute = routes[routeIndex];
      const existingStops = existingRoute.stops ?? [];
      const updatedRoute: TomlRouteData = ensureRouteDisplay(
        {
          ...existingRoute,
          stops: upsertStops(existingStops, result.stops),
        },
        routeDetails.title,
      );
      const updatedRoutes = [...routes];
      updatedRoutes[routeIndex] = updatedRoute;
      parsed.routes = updatedRoutes;
    }
    // For routes, tomlPatch has limitations, so use tomlStringify
    output = tomlStringify(parsed);
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
