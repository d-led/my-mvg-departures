# Changelog

## [0.0.6]

### Features

- **Time-based filtering**: `max_hours_in_advance` option (float, per stop) to filter out departures more than N hours in the future (< 1 or unset = unfiltered)

## [0.0.5]

### Features

- **Destination exclusion**: `exclude_destinations` option (list of patterns: route "54", destination "Messestadt", or route+destination "54 Münchner Freiheit") to exclude specific routes or destinations from a stop
- **Custom ungrouped titles**: `ungrouped_title` option (string, defaults to "Other") to customize the header for ungrouped departures
- **Color palette customization**: `random_color_salt` option (integer, default 0, per stop or `routes.display`) to generate different color palettes for auto-generated header colors

## [0.0.4]

### Features

- **Physical stop filtering**: Filter departures by specific physical stop points using `stop_point_global_id` format directly as `station_id`
- **Per-stop header colors**: `random_header_colors` and `header_background_brightness` can now be set per stop (inherits from route/global if not specified)

### Improvements

- **CLI enhancements**: `mvg-config routes` displays stop point differentiation hints sorted by stop point with copy-paste ready configuration snippets
- **API integration**: Improved extraction of `stopPointGlobalId` from raw MVG API responses (mvg library doesn't include it in transformed output)

## [0.0.3]

### Improvements

- **UI enhancements**: Improved header scaling, clock display (removed seconds), fixed theming and header colors, better spacing
- **Connection management**: Connection capping, improved presence tracking, client ID management, automatic reload after 1 hour
- **Infrastructure**: TCP health check endpoint, X-Forwarded-For support, hashing fixes
- **Documentation**: Updated example config, added VVO iframe example link

## [0.0.2]

### Features

- **Multiple routes**: Configure additional routes with custom paths (e.g., `/hohenzollernplatz`) via `[[routes]]` in TOML config
- **Route-specific titles**: Custom titles per route via `routes.display.title`
- **Visual enhancements**:
  - `fill_vertical_space`: Dynamic font sizing to fill viewport height
  - `font_scaling_factor_when_filling`: Scale factor for fonts when filling vertical space
  - `random_header_colors`: Hash-based pastel colors for headers (stable colors based on header text)
  - `header_background_brightness`: Brightness adjustment for random header colors (0.0-1.0, default 0.7)
- **Clock display**: Real-time clock rendered in headers
- **Connection status**: Visual indicators for WebSocket connection state
- **Cache busting**: Static asset versioning via `STATIC_VERSION` environment variable
- **Page metadata**: Custom page title and favicon support

### Configuration Keys

- `[[routes]]`: Define additional routes with custom paths
  - `path`: Route path (e.g., `/hohenzollernplatz`)
  - `routes.display.title`: Custom title for the route
  - `routes.display.fill_vertical_space`: Enable dynamic font sizing (boolean)
  - `routes.display.font_scaling_factor_when_filling`: Font scale factor when filling (float, default 1.0)
  - `routes.display.random_header_colors`: Enable hash-based header colors (boolean)
  - `routes.display.header_background_brightness`: Header color brightness (float, 0.0-1.0, default 0.7)
  - `[[routes.stops]]`: Stops configuration for the route (same structure as `[[stops]]`)
- `STATIC_VERSION`: Environment variable for cache busting static assets

## [0.0.1]

### Features

- **Live departure updates**: Real-time departure information from MVG API
- **Configurable stops**: Monitor multiple stops with custom direction groupings via `[[stops]]` in TOML config
- **Direction grouping**: Group routes by configurable direction names (e.g., `"->Giesing"`) via `stops.direction_mappings`
- **Responsive design**: Clean, modern UI that works on all screen sizes
- **Dark/Light mode**: Automatic theme switching based on system preferences via `theme` config
- **Flexible time display**: Show departures "in minutes" or "at" specific times via `time_format`
- **Pagination**: Configurable pagination with rotation for departure lists
- **12-Factor App**: Configuration via environment variables and TOML file
- **Multiple deployment options**: Docker container, init.d service, or direct execution

### Configuration Keys

- **Environment variables**:
  - `CONFIG_FILE`: Path to TOML configuration file (default: `config.example.toml`)
  - `HOST`: Server host (default: `0.0.0.0`)
  - `PORT`: Server port (default: `8000`)
  - `RELOAD`: Enable auto-reload for development (default: `false`)
  - `TIME_FORMAT`: Display format - `minutes` or `at` (default: `minutes`)
  - `REFRESH_INTERVAL_SECONDS`: Update interval in seconds (default: `30`)
  - `TIMEZONE`: IANA timezone name (default: `Europe/Berlin`)
  - `MVG_API_TIMEOUT`: Timeout for MVG API requests in seconds (default: `10`)
  - `MVG_API_LIMIT`: Maximum departures to fetch per station (default: `20`)
  - `MVG_API_OFFSET_MINUTES`: Offset in minutes for departure queries (default: `0`)

- **TOML configuration** (`[display]` section):
  - `title`: Page title (default: `"My MVG Departures"`)
  - `departures_per_page`: Number of departures per page (default: `5`)
  - `page_rotation_seconds`: Seconds to display each page (default: `8`)
  - `time_format_toggle_seconds`: Seconds to toggle relative/absolute time (default: `5`, `0` for relative only)
  - `pagination_enabled`: Enable pagination/animation (default: `false`)
  - `refresh_interval_seconds`: Interval between updates (default: `20`)
  - `banner_color`: Header background color (hex, default: `#087BC4`)
  - `theme`: UI theme - `light`, `dark`, or `auto` (default: `light`)
  - Font size settings: `font_size_route_number`, `font_size_destination`, `font_size_platform`, `font_size_time`, `font_size_stop_header`, `font_size_direction_header`, `font_size_pagination_indicator`, `font_size_countdown_text`, `font_size_delay_amount`, `font_size_no_departures`, `font_size_no_departures_available`, `font_size_status_header`

- **TOML configuration** (`[[stops]]` section):
  - `station_id`: MVG station ID (e.g., `"de:09162:1110"`)
  - `station_name`: Display name for the station
  - `max_departures_per_stop`: Maximum departures to show per stop
  - `max_departures_per_route`: Maximum departures to show per route
  - `departure_leeway_minutes`: Filter out departures earlier than now + leeway (default: `0`)
  - `show_ungrouped`: Show unmatched departures in "Other" group (default: `true`)
  - `stops.direction_mappings`: Map direction names to destination patterns (e.g., `"->Giesing" = ["139 Klinikum Harlaching"]`)

- **TOML configuration** (`[api]` section):
  - `sleep_ms_between_calls`: Sleep time in milliseconds between API calls to avoid rate limiting (default: `500`)
