import { parse } from "toml";
import type {
  AppConfig,
  RouteConfiguration,
  DisplayConfiguration,
  StopConfiguration,
  OnTheRunConfiguration,
} from "../../domain/models/index.js";
import { createStopConfiguration } from "../../domain/models/stop-configuration.js";
import type {
  TomlData,
  TomlRouteData,
  TomlStopData,
  TomlDisplayData,
  TomlOnTheRunData,
} from "./toml-types.js";

/** Path of the geolocation route; never written as a `[[routes]]` path. */
const ON_THE_RUN_PATH = "on-the-run";

/** Drops keys that were not configured, so "is anything set?" stays answerable. */
function definedOnly(display: DisplayConfiguration): DisplayConfiguration {
  return Object.fromEntries(
    Object.entries(display).filter(([, value]) => value !== undefined),
  ) as DisplayConfiguration;
}

/**
 * A route's effective display settings: the global `[display]` table with the
 * route's own values winning. `undefined` when neither sets anything.
 */
function withDefaults(
  globalDisplay: DisplayConfiguration | undefined,
  routeDisplay: DisplayConfiguration | undefined,
): DisplayConfiguration | undefined {
  const merged = {
    ...definedOnly(globalDisplay ?? {}),
    ...definedOnly(routeDisplay ?? {}),
  };
  return Object.keys(merged).length > 0 ? merged : undefined;
}

export class ConfigParser {
  parseToml(tomlString: string): AppConfig {
    const data = parse(tomlString) as TomlData;
    const display = data.display
      ? definedOnly(this.parseDisplayConfig(data.display))
      : undefined;

    const routes = this.parseRoutes(data.routes ?? [], display);
    this.attachLegacyStops(routes, this.parseStops(data.stops ?? []), display);

    const onTheRun = this.parseOnTheRun(data.on_the_run);
    if (onTheRun && !routes.some((route) => route.path === ON_THE_RUN_PATH)) {
      routes.push(this.onTheRunRoute(onTheRun, display));
    }

    return { display, routes, onTheRun };
  }

  /**
   * Top-level `[[stops]]` are the legacy spelling of the route at "/". They keep
   * working, and lead that route's stops as they lead the file.
   */
  private attachLegacyStops(
    routes: RouteConfiguration[],
    legacyStops: StopConfiguration[],
    globalDisplay: DisplayConfiguration | undefined,
  ): void {
    if (legacyStops.length === 0) {
      return;
    }

    const defaultRoute = routes.find((route) => route.path === "/");
    if (defaultRoute) {
      defaultRoute.stops = [...legacyStops, ...defaultRoute.stops];
      return;
    }

    routes.unshift({
      path: "/",
      display: withDefaults(globalDisplay, undefined),
      stops: legacyStops,
      refreshIntervalSeconds: globalDisplay?.refreshIntervalSeconds,
    });
  }

  private parseRoutes(
    routeData: TomlRouteData[],
    globalDisplay: DisplayConfiguration | undefined,
  ): RouteConfiguration[] {
    return routeData
      .map((data) => this.parseRoute(data, globalDisplay))
      .filter((route): route is RouteConfiguration => route !== null);
  }

  private onTheRunRoute(
    onTheRun: OnTheRunConfiguration,
    globalDisplay: DisplayConfiguration | undefined,
  ): RouteConfiguration {
    const radius = onTheRun.radiusMeters ?? 50;
    return {
      path: ON_THE_RUN_PATH,
      display: withDefaults(globalDisplay, {
        title: `Departures within ${radius}m`,
        randomHeaderColors: onTheRun.randomHeaderColors,
      }),
      stops: [],
      refreshIntervalSeconds: onTheRun.updateLocationIntervalSeconds,
      isOnTheRun: true,
    };
  }

  private parseRoute(
    routeData: TomlRouteData,
    globalDisplay: DisplayConfiguration | undefined,
  ): RouteConfiguration | null {
    const stops = this.parseStops(routeData.stops ?? []);
    if (stops.length === 0) {
      return null;
    }

    const display = withDefaults(
      globalDisplay,
      this.parseRouteDisplay(routeData.display),
    );

    return {
      path: routeData.path || "/",
      display,
      stops,
      refreshIntervalSeconds:
        routeData.refresh_interval_seconds ?? display?.refreshIntervalSeconds,
    };
  }

  /**
   * `[routes.display]` and `[[routes.display]]` both appear in the wild; the
   * first table wins.
   */
  private parseRouteDisplay(
    displayData: TomlDisplayData | TomlDisplayData[] | undefined,
  ): DisplayConfiguration | undefined {
    const entry = Array.isArray(displayData) ? displayData[0] : displayData;
    return entry ? definedOnly(this.parseDisplayConfig(entry)) : undefined;
  }

  private parseStops(stopsData: TomlStopData[]): StopConfiguration[] {
    if (!Array.isArray(stopsData)) {
      return [];
    }

    // Filter out stops with placeholder IDs (matches Python: s.get("station_id", "").find("XXX") == -1)
    // Coerce station_id to string (TOML may parse unquoted values as numbers)
    return stopsData
      .filter((stop) => {
        const stationId = String(stop.station_id ?? "");
        return (
          stationId && stop.station_name && stationId.indexOf("XXX") === -1
        );
      })
      .map((stop) => {
        const directionMappings: Record<string, string[]> = {};
        if (stop.direction_mappings) {
          for (const [key, value] of Object.entries(stop.direction_mappings)) {
            directionMappings[key] = Array.isArray(value)
              ? value
              : [value as string];
          }
        }

        const stopConfigData = {
          stationId: String(stop.station_id ?? ""),
          stationName: stop.station_name,
          maxDeparturesPerStop: stop.max_departures_per_stop,
          maxDeparturesPerRoute: stop.max_departures_per_route,
          maxDeparturesFetch: stop.max_departures_fetch,
          fetchMaxMinutesInAdvance: stop.fetch_max_minutes_in_advance,
          departureLeewayMinutes: stop.departure_leeway_minutes,
          maxHoursInAdvance: stop.max_hours_in_advance,
          showUngrouped: stop.show_ungrouped,
          ungroupedTitle:
            stop.ungrouped_title != null
              ? String(stop.ungrouped_title)
              : undefined,
          excludeDestinations: stop.exclude_destinations,
          directionMappings:
            Object.keys(directionMappings).length > 0
              ? directionMappings
              : undefined,
          platformFilter: stop.platform_filter,
          platformFilterRoutes: stop.platform_filter_routes,
          apiProvider: stop.api_provider,
          randomHeaderColors: stop.random_header_colors,
          headerBackgroundBrightness: stop.header_background_brightness,
          randomColorSalt: stop.random_color_salt,
        };

        return createStopConfiguration(stopConfigData);
      });
  }

  private parseOnTheRun(
    onTheRunData?: TomlOnTheRunData[] | TomlOnTheRunData,
  ): OnTheRunConfiguration | undefined {
    const entry = Array.isArray(onTheRunData) ? onTheRunData[0] : onTheRunData;
    if (!entry) {
      return undefined;
    }

    return {
      radiusMeters: entry.radius_meters ?? 50,
      maxDeparturesPerStop: entry.max_departures_per_stop ?? 8,
      maxDeparturesPerRoute: entry.max_departures_per_route ?? 2,
      updateLocationIntervalSeconds:
        entry.refresh_interval_seconds ??
        entry.update_location_interval_seconds ??
        20,
      updateLocationOnEveryPoll: entry.update_location_on_every_poll ?? true,
      useAdapters: entry.use_adapters ?? ["mvg"],
      usePreciseLocation: entry.use_precise_location ?? true,
      smartSubStops: entry.smart_sub_stops ?? true,
      randomHeaderColors: entry.random_header_colors,
    };
  }

  private parseDisplayConfig(
    displayData: TomlDisplayData,
  ): DisplayConfiguration {
    return {
      title: displayData.title,
      theme:
        displayData.theme === "light" ||
        displayData.theme === "dark" ||
        displayData.theme === "auto"
          ? displayData.theme
          : undefined,
      timeFormatToggleSeconds: displayData.time_format_toggle_seconds,
      fillVerticalSpace: displayData.fill_vertical_space,
      fontScalingFactorWhenFilling:
        displayData.font_scaling_factor_when_filling,
      randomHeaderColors: displayData.random_header_colors,
      headerBackgroundBrightness: displayData.header_background_brightness,
      refreshIntervalSeconds: displayData.refresh_interval_seconds,
      fetchRetryAttempts: displayData.fetch_retry_attempts,
      fetchRetryDelayMs: displayData.fetch_retry_delay_ms,
      splitShowDelay: displayData.split_show_delay,
      fontSizeRouteNumber: displayData.font_size_route_number,
      fontSizeDestination: displayData.font_size_destination,
      fontSizePlatform: displayData.font_size_platform,
      fontSizeTime: displayData.font_size_time,
      fontSizeStopHeader: displayData.font_size_stop_header,
      fontSizeDirectionHeader: displayData.font_size_direction_header,
      fontSizePaginationIndicator: displayData.font_size_pagination_indicator,
      fontSizeCountdownText: displayData.font_size_countdown_text,
      fontSizeDelayAmount: displayData.font_size_delay_amount,
      fontSizeNoDepartures: displayData.font_size_no_departures,
      fontSizeStatusHeader: displayData.font_size_status_header,
      routeIconDisplay: displayData.route_icon_display,
    };
  }
}
