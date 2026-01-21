/**
 * Serialize AppConfig back to TOML format
 * This is a custom serializer since the 'toml' package doesn't have stringify
 */

import type { AppConfig, RouteConfiguration, DisplayConfiguration, StopConfiguration } from "../domain/models/index.js";

function escapeString(str: string): string {
  // Escape quotes and backslashes in TOML strings
  return str.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
}

function serializeDisplayConfig(display: DisplayConfiguration | undefined, indent: string = ""): string {
  if (!display || Object.keys(display).length === 0) {
    return "";
  }

  const lines: string[] = [];
  
  if (display.title !== undefined) {
    lines.push(`${indent}title = "${escapeString(display.title)}"`);
  }
  if (display.theme !== undefined) {
    lines.push(`${indent}theme = "${display.theme}"`);
  }
  if (display.departuresPerPage !== undefined) {
    lines.push(`${indent}departures_per_page = ${display.departuresPerPage}`);
  }
  if (display.pageRotationSeconds !== undefined) {
    lines.push(`${indent}page_rotation_seconds = ${display.pageRotationSeconds}`);
  }
  if (display.timeFormatToggleSeconds !== undefined) {
    lines.push(`${indent}time_format_toggle_seconds = ${display.timeFormatToggleSeconds}`);
  }
  if (display.paginationEnabled !== undefined) {
    lines.push(`${indent}pagination_enabled = ${display.paginationEnabled}`);
  }
  if (display.fillVerticalSpace !== undefined) {
    lines.push(`${indent}fill_vertical_space = ${display.fillVerticalSpace}`);
  }
  if (display.fontScalingFactorWhenFilling !== undefined) {
    lines.push(`${indent}font_scaling_factor_when_filling = ${display.fontScalingFactorWhenFilling}`);
  }
  if (display.randomHeaderColors !== undefined) {
    lines.push(`${indent}random_header_colors = ${display.randomHeaderColors}`);
  }
  if (display.headerBackgroundBrightness !== undefined) {
    lines.push(`${indent}header_background_brightness = ${display.headerBackgroundBrightness}`);
  }
  if (display.refreshIntervalSeconds !== undefined) {
    lines.push(`${indent}refresh_interval_seconds = ${display.refreshIntervalSeconds}`);
  }
  if (display.bannerColor !== undefined) {
    lines.push(`${indent}banner_color = "${display.bannerColor}"`);
  }
  if (display.splitShowDelay !== undefined) {
    lines.push(`${indent}split_show_delay = ${display.splitShowDelay}`);
  }
  if (display.fontSizeRouteNumber !== undefined) {
    lines.push(`${indent}font_size_route_number = "${display.fontSizeRouteNumber}"`);
  }
  if (display.fontSizeDestination !== undefined) {
    lines.push(`${indent}font_size_destination = "${display.fontSizeDestination}"`);
  }
  if (display.fontSizePlatform !== undefined) {
    lines.push(`${indent}font_size_platform = "${display.fontSizePlatform}"`);
  }
  if (display.fontSizeTime !== undefined) {
    lines.push(`${indent}font_size_time = "${display.fontSizeTime}"`);
  }
  if (display.fontSizeStopHeader !== undefined) {
    lines.push(`${indent}font_size_stop_header = "${display.fontSizeStopHeader}"`);
  }
  if (display.fontSizeDirectionHeader !== undefined) {
    lines.push(`${indent}font_size_direction_header = "${display.fontSizeDirectionHeader}"`);
  }
  if (display.fontSizePaginationIndicator !== undefined) {
    lines.push(`${indent}font_size_pagination_indicator = "${display.fontSizePaginationIndicator}"`);
  }
  if (display.fontSizeCountdownText !== undefined) {
    lines.push(`${indent}font_size_countdown_text = "${display.fontSizeCountdownText}"`);
  }
  if (display.fontSizeDelayAmount !== undefined) {
    lines.push(`${indent}font_size_delay_amount = "${display.fontSizeDelayAmount}"`);
  }
  if (display.fontSizeNoDepartures !== undefined) {
    lines.push(`${indent}font_size_no_departures = "${display.fontSizeNoDepartures}"`);
  }
  if (display.fontSizeStatusHeader !== undefined) {
    lines.push(`${indent}font_size_status_header = "${display.fontSizeStatusHeader}"`);
  }
  if (display.routeIconDisplay !== undefined) {
    lines.push(`${indent}route_icon_display = "${display.routeIconDisplay}"`);
  }

  return lines.join("\n");
}

function serializeStopConfig(stop: StopConfiguration): string {
  const lines: string[] = [];
  
  lines.push(`[[stops]]`);
  lines.push(`station_id = "${escapeString(stop.stationId)}"`);
  lines.push(`station_name = "${escapeString(stop.stationName)}"`);
  
  if (stop.maxDeparturesPerStop !== undefined) {
    lines.push(`max_departures_per_stop = ${stop.maxDeparturesPerStop}`);
  }
  if (stop.maxDeparturesPerRoute !== undefined) {
    lines.push(`max_departures_per_route = ${stop.maxDeparturesPerRoute}`);
  }
  if (stop.maxDeparturesFetch !== undefined) {
    lines.push(`max_departures_fetch = ${stop.maxDeparturesFetch}`);
  }
  if (stop.fetchMaxMinutesInAdvance !== undefined) {
    lines.push(`fetch_max_minutes_in_advance = ${stop.fetchMaxMinutesInAdvance}`);
  }
  if (stop.departureLeewayMinutes !== undefined) {
    lines.push(`departure_leeway_minutes = ${stop.departureLeewayMinutes}`);
  }
  if (stop.maxHoursInAdvance !== undefined) {
    lines.push(`max_hours_in_advance = ${stop.maxHoursInAdvance}`);
  }
  if (stop.showUngrouped !== undefined) {
    lines.push(`show_ungrouped = ${stop.showUngrouped}`);
  }
  if (stop.ungroupedTitle !== undefined) {
    lines.push(`ungrouped_title = "${escapeString(stop.ungroupedTitle)}"`);
  }
  if (stop.excludeDestinations && stop.excludeDestinations.length > 0) {
    lines.push(`exclude_destinations = [${stop.excludeDestinations.map(d => `"${escapeString(d)}"`).join(", ")}]`);
  }
  if (stop.directionMappings && Object.keys(stop.directionMappings).length > 0) {
    lines.push(`[stops.direction_mappings]`);
    for (const [key, values] of Object.entries(stop.directionMappings)) {
      lines.push(`"${escapeString(key)}" = [${values.map(v => `"${escapeString(v)}"`).join(", ")}]`);
    }
  }
  if (stop.platformFilter !== undefined) {
    lines.push(`platform_filter = ${stop.platformFilter}`);
  }
  if (stop.platformFilterRoutes && stop.platformFilterRoutes.length > 0) {
    lines.push(`platform_filter_routes = [${stop.platformFilterRoutes.map(r => `"${escapeString(r)}"`).join(", ")}]`);
  }
  if (stop.apiProvider !== undefined && stop.apiProvider !== "mvg") {
    lines.push(`api_provider = "${stop.apiProvider}"`);
  }
  if (stop.randomHeaderColors !== undefined) {
    lines.push(`random_header_colors = ${stop.randomHeaderColors}`);
  }
  if (stop.headerBackgroundBrightness !== undefined) {
    lines.push(`header_background_brightness = ${stop.headerBackgroundBrightness}`);
  }
  if (stop.randomColorSalt !== undefined && stop.randomColorSalt !== 0) {
    lines.push(`random_color_salt = ${stop.randomColorSalt}`);
  }

  return lines.join("\n");
}

export function serializeConfigToToml(config: AppConfig): string {
  const lines: string[] = [];
  
  // Serialize top-level display settings
  if (config.defaultDisplay && Object.keys(config.defaultDisplay).length > 0) {
    lines.push("[display]");
    lines.push("");
    const displayLines = serializeDisplayConfig(config.defaultDisplay);
    if (displayLines) {
      lines.push(displayLines);
      lines.push("");
    }
  }
  
  // Serialize API settings
  if (config.api && Object.keys(config.api).length > 0) {
    lines.push("[api]");
    if (config.api.sleepMsBetweenCalls !== undefined) {
      lines.push(`sleep_ms_between_calls = ${config.api.sleepMsBetweenCalls}`);
    }
    if (config.api.apiProvider !== undefined) {
      lines.push(`api_provider = "${config.api.apiProvider}"`);
    }
    lines.push("");
  }
  
  // Serialize routes
  // First, identify the default route (path === "/")
  const defaultRoute = config.routes.find(r => r.path === "/");
  const otherRoutes = config.routes.filter(r => r.path !== "/");
  
  // Serialize default route stops as top-level [[stops]]
  if (defaultRoute && defaultRoute.stops.length > 0) {
    for (const stop of defaultRoute.stops) {
      lines.push(serializeStopConfig(stop));
      lines.push("");
    }
  }
  
  // Serialize explicit routes
  if (otherRoutes.length > 0) {
    for (const route of otherRoutes) {
      lines.push("[[routes]]");
      if (route.path !== "/") {
        lines.push(`path = "${route.path}"`);
      }
      if (route.refreshIntervalSeconds !== undefined) {
        lines.push(`refresh_interval_seconds = ${route.refreshIntervalSeconds}`);
      }
      
      // Serialize route display settings
      if (route.display && Object.keys(route.display).length > 0) {
        lines.push("");
        lines.push("[routes.display]");
        const displayLines = serializeDisplayConfig(route.display);
        if (displayLines) {
          lines.push(displayLines);
        }
      }
      
      // Serialize route stops
      if (route.stops.length > 0) {
        lines.push("");
        for (const stop of route.stops) {
          lines.push(serializeStopConfig(stop));
          lines.push("");
        }
      } else {
        lines.push("");
      }
    }
  }
  
  // Also serialize default route as explicit route if it has display settings or refresh interval
  if (defaultRoute && (defaultRoute.display || defaultRoute.refreshIntervalSeconds !== undefined)) {
    lines.push("[[routes]]");
    lines.push(`path = "/"`);
    if (defaultRoute.refreshIntervalSeconds !== undefined) {
      lines.push(`refresh_interval_seconds = ${defaultRoute.refreshIntervalSeconds}`);
    }
    if (defaultRoute.display && Object.keys(defaultRoute.display).length > 0) {
      lines.push("");
      lines.push("[routes.display]");
      const displayLines = serializeDisplayConfig(defaultRoute.display);
      if (displayLines) {
        lines.push(displayLines);
      }
    }
    lines.push("");
  }
  
  // Remove trailing empty lines
  while (lines.length > 0 && lines[lines.length - 1] === "") {
    lines.pop();
  }
  
  return lines.join("\n");
}
