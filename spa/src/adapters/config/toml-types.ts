// Types for TOML parsing
export interface TomlDisplayData {
  title?: string;
  theme?: string;
  departures_per_page?: number;
  page_rotation_seconds?: number;
  time_format_toggle_seconds?: number;
  pagination_enabled?: boolean;
  fill_vertical_space?: boolean;
  font_scaling_factor_when_filling?: number;
  random_header_colors?: boolean;
  header_background_brightness?: number;
  refresh_interval_seconds?: number;
  banner_color?: string;
  split_show_delay?: boolean;
  font_size_route_number?: string;
  font_size_destination?: string;
  font_size_platform?: string;
  font_size_time?: string;
  font_size_stop_header?: string;
  font_size_direction_header?: string;
  font_size_pagination_indicator?: string;
  font_size_countdown_text?: string;
  font_size_delay_amount?: string;
  font_size_no_departures?: string;
  font_size_status_header?: string;
  route_icon_display?: "icon_with_text" | "badge" | "none";
}

export interface TomlApiData {
  sleep_ms_between_calls?: number;
  api_provider?: string;
}

export interface TomlStopData {
  station_id: string;
  station_name: string;
  max_departures_per_stop?: number;
  max_departures_per_route?: number;
  max_departures_fetch?: number;
  fetch_max_minutes_in_advance?: number;
  departure_leeway_minutes?: number;
  max_hours_in_advance?: number;
  show_ungrouped?: boolean;
  ungrouped_title?: string;
  exclude_destinations?: string[];
  direction_mappings?: Record<string, string | string[]>;
  platform_filter?: number;
  platform_filter_routes?: string[];
  api_provider?: string;
  random_header_colors?: boolean;
  header_background_brightness?: number;
  random_color_salt?: number;
}

export interface TomlRouteData {
  path?: string;
  display?: TomlDisplayData | TomlDisplayData[]; // Can be dict or array (for [[routes.display]])
  stops?: TomlStopData[];
  refresh_interval_seconds?: number;
}

export interface TomlOnTheRunData {
  radius_meters?: number;
  max_departures_per_stop?: number;
  max_departures_per_route?: number;
  update_location_interval_seconds?: number;
  use_adapters?: string[];
  use_precise_location?: boolean;
  smart_sub_stops?: boolean;
  random_header_colors?: boolean;
}

export interface TomlData {
  display?: TomlDisplayData;
  api?: TomlApiData;
  routes?: TomlRouteData[];
  stops?: TomlStopData[];
  on_the_run?: TomlOnTheRunData[] | TomlOnTheRunData;
}
