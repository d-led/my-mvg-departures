"""12-factor configuration adapter using environment variables and TOML config."""

from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]  # Fallback for older Python

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Application configuration following 12-factor principles."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server configuration
    host: str = Field(default="0.0.0.0", description="Host to bind the server to")
    port: int = Field(default=8000, description="Port to bind the server to")
    reload: bool = Field(default=False, description="Enable auto-reload for development")

    # API provider configuration
    api_provider: str = Field(
        default="mvg",
        description="API provider to use: 'mvg' (default) or 'hafas' (optional)",
    )
    hafas_profile: str | None = Field(
        default=None,
        description="HAFAS profile to use when api_provider='hafas' (e.g., 'db', 'vvo'). None = auto-detect",
    )

    # MVG API configuration
    mvg_api_timeout: int = Field(default=10, description="Timeout for MVG API requests in seconds")
    mvg_api_limit: int = Field(
        default=20, description="Maximum number of departures to fetch per station"
    )
    mvg_api_offset_minutes: int = Field(
        default=0, description="Offset in minutes for departure queries"
    )
    sleep_ms_between_calls: int = Field(
        default=0,
        description="Sleep time in milliseconds between API calls to avoid rate limiting",
    )

    # Display configuration
    time_format: str = Field(default="minutes", description="Time format: 'minutes' or 'at'")
    refresh_interval_seconds: int = Field(
        default=30, description="Interval between departure updates in seconds"
    )
    timezone: str = Field(
        default="Europe/Berlin",
        description="Timezone for displaying server time (IANA timezone name, e.g., 'Europe/Berlin')",
    )
    title: str = Field(
        default="My MVG Departures",
        description="Page title displayed in browser tab",
    )

    # TOML config file path
    # If not set, will try config.example.toml in project root as fallback
    config_file: str | None = Field(
        default="config.example.toml",
        description="Path to TOML configuration file for stop mappings and display settings",
    )

    # Display pagination/animation
    pagination_enabled: bool = Field(
        default=True,
        description="Enable pagination/animation for departures and groups",
    )
    departures_per_page: int = Field(
        default=5,
        description="Number of departures to show per page within a route group",
    )
    page_rotation_seconds: int = Field(
        default=8,
        description="Seconds to display each page before rotating",
    )
    time_format_toggle_seconds: int = Field(
        default=3,
        description="Seconds to toggle between relative and absolute time (0 for relative time only)",
    )
    theme: str = Field(
        default="light",
        description="UI theme: 'light', 'dark', or 'auto' (follows system preference)",
    )
    banner_color: str = Field(
        default="#087BC4",
        description="Banner/header background color (hex color code)",
    )

    # Font size configuration (in rem units)
    font_size_route_number: str = Field(
        default="4rem",
        description="Font size for route numbers",
    )
    font_size_destination: str = Field(
        default="3.5rem",
        description="Font size for destination text",
    )
    font_size_platform: str = Field(
        default="2.5rem",
        description="Font size for platform numbers",
    )
    font_size_time: str = Field(
        default="4rem",
        description="Font size for departure times",
    )
    font_size_stop_header: str = Field(
        default="3rem",
        description="Font size for stop headers",
    )
    font_size_direction_header: str = Field(
        default="2.5rem",
        description="Font size for direction headers",
    )
    font_size_pagination_indicator: str = Field(
        default="2rem",
        description="Font size for pagination indicator",
    )
    font_size_countdown_text: str = Field(
        default="1.8rem",
        description="Font size for countdown text",
    )
    font_size_delay_amount: str = Field(
        default="2rem",
        description="Font size for delay amount text",
    )
    font_size_no_departures: str = Field(
        default="2.5rem",
        description="Font size for 'No departures' message",
    )
    font_size_no_departures_available: str = Field(
        default="3rem",
        description="Font size for main 'No departures available' message",
    )
    font_size_status_header: str = Field(
        default="1.875rem",
        description="Font size for status header (date/time, connection status, error indicator) - default is 0.75 of direction_header",
    )

    # Rate limiting configuration
    rate_limit_per_minute: int = Field(
        default=100,
        description="Maximum number of requests allowed per IP address per minute",
    )

    # Admin command token for privileged maintenance endpoints (e.g. connection reset)
    # Set via ADMIN_COMMAND_TOKEN environment variable. If not set, admin endpoints
    # remain disabled.
    admin_command_token: str | None = Field(
        default=None,
        description="Shared secret token required for admin maintenance commands",
    )

    # Cache busting version for static assets
    # Set via STATIC_VERSION environment variable, or defaults to timestamp-based version
    static_version: str | None = Field(
        default=None,
        description="Version string for cache busting static assets (set via STATIC_VERSION env var)",
    )

    # Client reload coordination
    enable_server_start_reload: bool = Field(
        default=True,
        description=(
            "When true, bump reload_request_id once on server start so that long-lived "
            "browser tabs perform a single hard reload per new server process."
        ),
    )

    max_sessions_per_browser: int = Field(
        default=15,
        description=(
            "Maximum number of concurrent sockets allowed per browser identifier. "
            "Connections with browser_id == 'unknown' are not limited."
        ),
    )

    @field_validator("time_format")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Validate time format is either 'minutes' or 'at'."""
        if v not in ("minutes", "at"):
            raise ValueError("time_format must be either 'minutes' or 'at'")
        return v

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, v: str) -> str:
        """Validate theme is either 'light', 'dark', or 'auto'."""
        if v.lower() not in ("light", "dark", "auto"):
            raise ValueError("theme must be either 'light', 'dark', or 'auto'")
        return v.lower()

    @field_validator("api_provider")
    @classmethod
    def validate_api_provider(cls, v: str) -> str:
        """Validate API provider is either 'mvg' or 'hafas'."""
        if v.lower() not in ("mvg", "hafas"):
            raise ValueError("api_provider must be either 'mvg' or 'hafas'")
        return v.lower()

    @classmethod
    def for_testing(cls, **kwargs: Any) -> "AppConfig":
        """Create an AppConfig instance for testing without loading .env file.

        This method creates an AppConfig instance with .env file loading disabled,
        making tests environment-independent. All other parameters are passed through
        to the constructor.

        Args:
            **kwargs: Any parameters to pass to AppConfig constructor

        Returns:
            AppConfig instance with .env file loading disabled
        """

        # Create a subclass with modified model_config to disable .env file loading
        class TestAppConfig(cls):  # type: ignore[misc, valid-type]
            model_config = SettingsConfigDict(
                env_file=None,  # Disable .env file loading
                env_file_encoding="utf-8",
                case_sensitive=False,
                extra="ignore",
            )

        return TestAppConfig(**kwargs)

    def _load_toml_data(self) -> dict[str, Any]:
        """Load and parse TOML file, updating display settings."""
        if not self.config_file:
            raise ValueError("config_file must be set to load stops configuration")

        config_path = Path(self.config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "rb") as f:
            toml_data = tomllib.load(f)

            # Update display settings from TOML if present
            if "display" in toml_data:
                display = toml_data["display"]
                if "departures_per_page" in display:
                    self.departures_per_page = display["departures_per_page"]
                if "page_rotation_seconds" in display:
                    self.page_rotation_seconds = display["page_rotation_seconds"]
                if "pagination_enabled" in display:
                    self.pagination_enabled = display["pagination_enabled"]
                if "theme" in display:
                    self.theme = display["theme"]
                if "banner_color" in display:
                    self.banner_color = display["banner_color"]
                if "refresh_interval_seconds" in display:
                    self.refresh_interval_seconds = display["refresh_interval_seconds"]
                if "time_format_toggle_seconds" in display:
                    self.time_format_toggle_seconds = display["time_format_toggle_seconds"]
                if "title" in display:
                    self.title = display["title"]
                # Font sizes
                if "font_size_route_number" in display:
                    self.font_size_route_number = display["font_size_route_number"]
                if "font_size_destination" in display:
                    self.font_size_destination = display["font_size_destination"]
                if "font_size_platform" in display:
                    self.font_size_platform = display["font_size_platform"]
                if "font_size_time" in display:
                    self.font_size_time = display["font_size_time"]
                if "font_size_stop_header" in display:
                    self.font_size_stop_header = display["font_size_stop_header"]
                if "font_size_direction_header" in display:
                    self.font_size_direction_header = display["font_size_direction_header"]
                if "font_size_pagination_indicator" in display:
                    self.font_size_pagination_indicator = display["font_size_pagination_indicator"]
                if "font_size_countdown_text" in display:
                    self.font_size_countdown_text = display["font_size_countdown_text"]
                if "font_size_delay_amount" in display:
                    self.font_size_delay_amount = display["font_size_delay_amount"]
                if "font_size_no_departures" in display:
                    self.font_size_no_departures = display["font_size_no_departures"]
                if "font_size_no_departures_available" in display:
                    self.font_size_no_departures_available = display[
                        "font_size_no_departures_available"
                    ]
                if "font_size_status_header" in display:
                    self.font_size_status_header = display["font_size_status_header"]

            # Update API settings from TOML if present
            # Support both [api] and [client] sections for backward compatibility
            api_config = toml_data.get("api") or toml_data.get("client", {})
            if "sleep_ms_between_calls" in api_config:
                self.sleep_ms_between_calls = api_config["sleep_ms_between_calls"]
            if "api_provider" in api_config:
                self.api_provider = api_config["api_provider"]
            if "hafas_profile" in api_config:
                hafas_profile_value = api_config["hafas_profile"]
                # Convert empty string to None for auto-detection
                self.hafas_profile = hafas_profile_value if hafas_profile_value else None

            return toml_data

    def get_routes_config(self) -> list[dict[str, Any]]:
        """Parse and return routes configuration as a list of dicts from TOML file.

        Returns a list of route configurations, each with 'path' and 'stops' keys.
        Supports mixing formats:
        - If [[stops]] are defined, creates a default route at "/" with those stops
        - If [[routes]] are defined, uses those routes
        - Both can be used together (default route from stops + additional routes)

        Raises ValueError if route paths are not unique (including conflict with default "/").
        """
        toml_data = self._load_toml_data()

        routes = toml_data.get("routes", [])
        stops = toml_data.get("stops", [])

        result_routes: list[dict[str, Any]] = []

        # If stops are defined, create default route at "/"
        if stops:
            if not isinstance(stops, list):
                raise ValueError("TOML config 'stops' must be a list")
            # Filter out stops with placeholder IDs
            filtered_stops = [s for s in stops if s.get("station_id", "").find("XXX") == -1]
            if filtered_stops:
                # Include display settings from [display] section for the main route
                default_route: dict[str, Any] = {"path": "/", "stops": filtered_stops}
                if "display" in toml_data:
                    display = toml_data["display"]
                    # Include fill_vertical_space, font_scaling_factor_when_filling, and random_header_colors if set
                    # display is a dict from [display] section, not a list
                    if isinstance(display, dict):
                        display_settings: dict[str, Any] = {}
                        if "fill_vertical_space" in display:
                            display_settings["fill_vertical_space"] = display["fill_vertical_space"]
                        if "font_scaling_factor_when_filling" in display:
                            display_settings["font_scaling_factor_when_filling"] = display[
                                "font_scaling_factor_when_filling"
                            ]
                        if "random_header_colors" in display:
                            display_settings["random_header_colors"] = display[
                                "random_header_colors"
                            ]
                        if "header_background_brightness" in display:
                            display_settings["header_background_brightness"] = display[
                                "header_background_brightness"
                            ]
                        if "random_color_salt" in display:
                            display_settings["random_color_salt"] = display["random_color_salt"]
                        if display_settings:
                            default_route["display"] = display_settings
                result_routes.append(default_route)

        # If routes are defined, add them
        if routes:
            if not isinstance(routes, list):
                raise ValueError("TOML config 'routes' must be a list")

            # Validate all routes have paths
            for route in routes:
                if not isinstance(route, dict):
                    continue
                if "path" not in route:
                    raise ValueError("All routes must have a 'path' field")
                result_routes.append(route)

        # Validate unique paths (including checking for "/" conflict)
        if result_routes:
            paths = [route.get("path") for route in result_routes if isinstance(route, dict)]
            if len(paths) != len(set(paths)):
                duplicates = [p for p in paths if paths.count(p) > 1]
                raise ValueError(
                    f"Route paths must be unique. Duplicate paths found: {set(duplicates)}"
                )

        return result_routes

    def get_stops_config(self) -> list[dict[str, Any]]:
        """Parse and return stops configuration as a list of dicts from TOML file.

        Loads configuration from the TOML file specified in config_file.
        Defaults to config.example.toml if available.

        This method is kept for backward compatibility. For new code, use get_routes_config().
        """
        toml_data = self._load_toml_data()

        stops = toml_data.get("stops", [])
        if not isinstance(stops, list):
            raise ValueError("TOML config 'stops' must be a list")
        # Filter out stops with placeholder IDs
        return [s for s in stops if s.get("station_id", "").find("XXX") == -1]
