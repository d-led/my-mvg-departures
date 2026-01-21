import { parse } from "toml";
import type {
  AppConfig,
  RouteConfiguration,
  DisplayConfiguration,
  StopConfiguration,
} from "../../domain/models/index.js";
import { createStopConfiguration } from "../../domain/models/stop-configuration.js";
import type {
  TomlData,
  TomlRouteData,
  TomlStopData,
  TomlDisplayData,
} from "./toml-types.js";

export class ConfigParser {
  parseToml(tomlString: string): AppConfig {
    const data = parse(tomlString) as TomlData;

    const routes: RouteConfiguration[] = [];
    const defaultDisplay: DisplayConfiguration = {};
    const api: { sleepMsBetweenCalls?: number; apiProvider?: string } = {};

    // Parse default display settings
    if (data.display) {
      Object.assign(defaultDisplay, this.parseDisplayConfig(data.display));
    }

    // Parse API settings
    if (data.api) {
      if (data.api.sleep_ms_between_calls !== undefined) {
        api.sleepMsBetweenCalls = data.api.sleep_ms_between_calls;
      }
      if (data.api.api_provider !== undefined) {
        api.apiProvider = data.api.api_provider;
      }
    }

    // Parse top-level stops first to create default route (matches Python: get_routes_config)
    // Python logic: if stops exist, create default route at "/" with those stops
    const defaultStops = this.parseStops(data.stops || []);
    if (defaultStops.length > 0) {
      // Create default route with top-level display settings (matches Python: _create_default_route)
      const defaultRoute: RouteConfiguration = {
        path: "/",
        stops: defaultStops,
      };
      // Only include display if there are display settings (matches Python: if display_settings: default_route["display"] = display_settings)
      if (Object.keys(defaultDisplay).length > 0) {
        defaultRoute.display = defaultDisplay;
      }
      routes.push(defaultRoute);
    }

    // Parse explicit routes (these are in addition to the default route)
    if (data.routes && Array.isArray(data.routes)) {
      for (const routeData of data.routes) {
        const route = this.parseRoute(routeData, defaultDisplay);
        if (route) {
          routes.push(route);
        }
      }
    }

    return {
      routes,
      defaultDisplay:
        Object.keys(defaultDisplay).length > 0 ? defaultDisplay : undefined,
      api: Object.keys(api).length > 0 ? api : undefined,
    };
  }

  private parseRoute(
    routeData: TomlRouteData,
    defaultDisplay: DisplayConfiguration,
  ): RouteConfiguration | null {
    const path = routeData.path || "/";
    const routeDisplay = routeData.display
      ? this.parseDisplayConfig(routeData.display)
      : { ...defaultDisplay };
    const stops = this.parseStops(routeData.stops || []);

    if (stops.length === 0) {
      return null;
    }

    return {
      path,
      display: Object.keys(routeDisplay).length > 0 ? routeDisplay : undefined,
      stops,
      refreshIntervalSeconds:
        routeData.refresh_interval_seconds ??
        routeDisplay.refreshIntervalSeconds,
    };
  }

  private parseStops(stopsData: TomlStopData[]): StopConfiguration[] {
    if (!Array.isArray(stopsData)) {
      return [];
    }

    // Filter out stops with placeholder IDs (matches Python: s.get("station_id", "").find("XXX") == -1)
    return stopsData
      .filter((stop) => {
        const stationId = stop.station_id || "";
        return stationId && stop.station_name && stationId.indexOf("XXX") === -1;
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

        return createStopConfiguration({
          stationId: stop.station_id,
          stationName: stop.station_name,
          maxDeparturesPerStop: stop.max_departures_per_stop,
          maxDeparturesPerRoute: stop.max_departures_per_route,
          maxDeparturesFetch: stop.max_departures_fetch,
          fetchMaxMinutesInAdvance: stop.fetch_max_minutes_in_advance,
          departureLeewayMinutes: stop.departure_leeway_minutes,
          maxHoursInAdvance: stop.max_hours_in_advance,
          showUngrouped: stop.show_ungrouped,
          ungroupedTitle: stop.ungrouped_title,
          excludeDestinations: stop.exclude_destinations,
          directionMappings:
            Object.keys(directionMappings).length > 0
              ? directionMappings
              : undefined,
          platformFilter: stop.platform_filter,
          platformFilterRoutes: stop.platform_filter_routes,
          apiProvider: stop.api_provider,
          randomHeaderColors: stop.random_header_colors,
          randomColorSalt: stop.random_color_salt,
        });
      });
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
      departuresPerPage: displayData.departures_per_page,
      pageRotationSeconds: displayData.page_rotation_seconds,
      timeFormatToggleSeconds: displayData.time_format_toggle_seconds,
      paginationEnabled: displayData.pagination_enabled,
      fillVerticalSpace: displayData.fill_vertical_space,
      fontScalingFactorWhenFilling:
        displayData.font_scaling_factor_when_filling,
      randomHeaderColors: displayData.random_header_colors,
      headerBackgroundBrightness: displayData.header_background_brightness,
      refreshIntervalSeconds: displayData.refresh_interval_seconds,
      bannerColor: displayData.banner_color,
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
    };
  }
}
