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

export class ConfigParser {
  parseToml(tomlString: string): AppConfig {
    const data = parse(tomlString) as TomlData;

    const routes: RouteConfiguration[] = [];
    const defaultDisplay: DisplayConfiguration = {};
    const api: { sleepMsBetweenCalls?: number; apiProvider?: string } = {};
    const onTheRun = this.parseOnTheRun(data.on_the_run);

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

    // Add on-the-run route if configured and not already present
    if (onTheRun && !routes.some((route) => route.path === "on-the-run")) {
      const radiusLabel = onTheRun.radiusMeters ?? 50;
      const onTheRunDisplay: DisplayConfiguration = {
        ...defaultDisplay,
        title: `Departures within ${radiusLabel}m`,
        randomHeaderColors:
          onTheRun.randomHeaderColors ?? defaultDisplay.randomHeaderColors,
      };
      routes.push({
        path: "on-the-run",
        display:
          Object.keys(onTheRunDisplay).length > 0 ? onTheRunDisplay : undefined,
        stops: [],
        refreshIntervalSeconds: onTheRun.updateLocationIntervalSeconds,
        isOnTheRun: true,
      });
    }

    return {
      routes,
      onTheRun,
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

    // Handle display data (can be dict or array for [[routes.display]] syntax)
    // Matches Python: _parse_display_data which handles both dict and list
    // Routes inherit from defaultDisplay for missing fields (matches user requirement)
    let routeDisplay: DisplayConfiguration;
    if (routeData.display) {
      let parsedDisplay: DisplayConfiguration;
      if (Array.isArray(routeData.display) && routeData.display.length > 0) {
        // [[routes.display]] creates an array - use first element (matches Python: lines 294-297)
        parsedDisplay = this.parseDisplayConfig(routeData.display[0]);
      } else if (!Array.isArray(routeData.display)) {
        // Single display object
        parsedDisplay = this.parseDisplayConfig(routeData.display);
      } else {
        // Empty array - use defaults
        parsedDisplay = {};
      }
      // Merge with defaultDisplay: route-specific values override defaults, missing values inherit
      // Only include defined values from parsedDisplay (undefined values should inherit from defaultDisplay)
      // Note: false is a valid value and should override defaults, only undefined should be filtered
      const definedRouteDisplay: DisplayConfiguration = {};
      for (const [key, value] of Object.entries(parsedDisplay)) {
        if (value !== undefined) {
          (definedRouteDisplay as Record<string, unknown>)[key] = value;
        }
      }
      routeDisplay = { ...defaultDisplay, ...definedRouteDisplay };
      console.log(`[config-parser] Parsed route ${path} display:`, {
        parsedDisplay,
        defaultDisplay,
        mergedRouteDisplay: routeDisplay,
        randomHeaderColors: routeDisplay.randomHeaderColors,
        headerBackgroundBrightness: routeDisplay.headerBackgroundBrightness,
      });
    } else {
      // No route display config - use default display config
      routeDisplay = { ...defaultDisplay };
    }

    const stops = this.parseStops(routeData.stops || []);

    if (stops.length === 0) {
      return null;
    }

    // Always include display config if route has any display settings (even if merged with defaults)
    // This ensures route.display is available for header color inheritance
    const hasRouteDisplay =
      routeData.display !== undefined && routeData.display !== null;
    const finalDisplay =
      hasRouteDisplay || Object.keys(routeDisplay).length > 0
        ? routeDisplay
        : undefined;

    console.log(`[config-parser] Route ${path} final display:`, {
      hasRouteDisplay,
      routeDisplayKeys: Object.keys(routeDisplay),
      finalDisplay,
      randomHeaderColors: finalDisplay?.randomHeaderColors,
    });

    return {
      path,
      display: finalDisplay,
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

        console.log(
          `[config-parser] Creating stop config for ${stopConfigData.stationName} (${stopConfigData.stationId}): random_header_colors from TOML=${stop.random_header_colors}, randomHeaderColors in data=${stopConfigData.randomHeaderColors}`,
        );

        const created = createStopConfiguration(stopConfigData);
        console.log(
          `[config-parser] Created stop config: randomHeaderColors=${created.randomHeaderColors} (type: ${typeof created.randomHeaderColors})`,
        );

        return created;
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
      routeIconDisplay: displayData.route_icon_display,
    };
  }
}
