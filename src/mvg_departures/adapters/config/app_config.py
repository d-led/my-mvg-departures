"""12-factor configuration adapter using environment variables and TOML config."""

from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]  # Fallback for older Python

from pydantic import Field, field_validator, model_validator
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
        description="API provider to use: 'mvg' (default), 'db', or 'vbb'",
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
    route_icon_display: str = Field(
        default="icon_with_text",
        description="Route icon display mode: 'none' (text only), 'icon_with_text' (icon + number), or 'badge' (number in transport type shape)",
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

    @model_validator(mode="after")
    def check_rate_limit_env_var(self) -> "AppConfig":
        """Check RATE_LIMIT_PER_MINUTE environment variable and override if valid."""
        import os

        env_value = os.getenv("RATE_LIMIT_PER_MINUTE")
        if not env_value or not env_value.strip():
            return self

        try:
            value = int(env_value)
            if value >= 0:
                self.rate_limit_per_minute = value
        except ValueError:
            pass  # Ignore invalid values
        return self

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
        """Validate API provider is 'mvg', 'db', or 'vbb'."""
        if v.lower() not in ("mvg", "db", "vbb"):
            raise ValueError("api_provider must be either 'mvg', 'db', or 'vbb'")
        return v.lower()

    @field_validator("route_icon_display")
    @classmethod
    def validate_route_icon_display(cls, v: str) -> str:
        """Validate route icon display mode."""
        if v.lower() not in ("none", "icon_with_text", "badge"):
            raise ValueError("route_icon_display must be 'none', 'icon_with_text', or 'badge'")
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

    def _update_display_settings(self, display: dict[str, Any]) -> None:
        """Update display settings from TOML display section.

        Args:
            display: Display settings dictionary from TOML.
        """
        display_mappings = {
            "departures_per_page": "departures_per_page",
            "page_rotation_seconds": "page_rotation_seconds",
            "pagination_enabled": "pagination_enabled",
            "theme": "theme",
            "banner_color": "banner_color",
            "refresh_interval_seconds": "refresh_interval_seconds",
            "time_format_toggle_seconds": "time_format_toggle_seconds",
            "title": "title",
            "route_icon_display": "route_icon_display",
            "font_size_route_number": "font_size_route_number",
            "font_size_destination": "font_size_destination",
            "font_size_platform": "font_size_platform",
            "font_size_time": "font_size_time",
            "font_size_stop_header": "font_size_stop_header",
            "font_size_direction_header": "font_size_direction_header",
            "font_size_pagination_indicator": "font_size_pagination_indicator",
            "font_size_countdown_text": "font_size_countdown_text",
            "font_size_delay_amount": "font_size_delay_amount",
            "font_size_no_departures": "font_size_no_departures",
            "font_size_no_departures_available": "font_size_no_departures_available",
            "font_size_status_header": "font_size_status_header",
            "split_show_delay": "split_show_delay",
        }

        for toml_key, attr_name in display_mappings.items():
            if toml_key in display:
                setattr(self, attr_name, display[toml_key])

    def _update_api_settings(self, api_config: dict[str, Any]) -> None:
        """Update API settings from TOML api/client section.

        Args:
            api_config: API settings dictionary from TOML.
        """
        if "sleep_ms_between_calls" in api_config:
            self.sleep_ms_between_calls = api_config["sleep_ms_between_calls"]
        if "api_provider" in api_config:
            self.api_provider = api_config["api_provider"]

    def _process_display_settings(self, toml_data: dict[str, Any]) -> None:
        """Process and update display settings from TOML data."""
        if "display" in toml_data:
            display = toml_data["display"]
            if isinstance(display, dict):
                self._update_display_settings(display)

    def _process_api_settings(self, toml_data: dict[str, Any]) -> None:
        """Process and update API settings from TOML data."""
        api_config = toml_data.get("api") or toml_data.get("client", {})
        if isinstance(api_config, dict):
            self._update_api_settings(api_config)

    def _load_toml_data(self) -> dict[str, Any]:
        """Load and parse TOML file, updating display settings."""
        if not self.config_file:
            raise ValueError("config_file must be set to load stops configuration")

        config_path = Path(self.config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "rb") as f:
            toml_data = tomllib.load(f)

            self._process_display_settings(toml_data)
            self._process_api_settings(toml_data)

            return toml_data

    def _extract_display_settings(self, toml_data: dict[str, Any]) -> dict[str, Any]:
        """Extract display settings from TOML data.

        Args:
            toml_data: TOML data dictionary.

        Returns:
            Dictionary with display settings.
        """
        if "display" not in toml_data:
            return {}

        display = toml_data["display"]
        if not isinstance(display, dict):
            return {}

        display_settings: dict[str, Any] = {}
        display_keys = [
            "fill_vertical_space",
            "font_scaling_factor_when_filling",
            "random_header_colors",
            "header_background_brightness",
            "random_color_salt",
            "split_show_delay",
        ]

        for key in display_keys:
            if key in display:
                display_settings[key] = display[key]

        return display_settings

    def _create_default_route(
        self, stops: list[dict[str, Any]], toml_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Create default route from stops configuration.

        Args:
            stops: List of stop configurations.
            toml_data: TOML data dictionary.

        Returns:
            Default route dictionary, or None if no valid stops.
        """
        if not isinstance(stops, list):
            raise ValueError("TOML config 'stops' must be a list")

        filtered_stops = [s for s in stops if s.get("station_id", "").find("XXX") == -1]
        if not filtered_stops:
            return None

        default_route: dict[str, Any] = {"path": "/", "stops": filtered_stops}
        display_settings = self._extract_display_settings(toml_data)
        if display_settings:
            default_route["display"] = display_settings

        return default_route

    def _validate_and_add_routes(
        self, routes: list[dict[str, Any]], result_routes: list[dict[str, Any]]
    ) -> None:
        """Validate and add routes to result list.

        Args:
            routes: List of route configurations.
            result_routes: Result list to append to.

        Raises:
            ValueError: If routes are invalid.
        """
        if not isinstance(routes, list):
            raise ValueError("TOML config 'routes' must be a list")

        for route in routes:
            if not isinstance(route, dict):
                continue
            if "path" not in route:
                raise ValueError("All routes must have a 'path' field")
            result_routes.append(route)

    def _validate_unique_paths(self, result_routes: list[dict[str, Any]]) -> None:
        """Validate that all route paths are unique.

        Args:
            result_routes: List of route configurations.

        Raises:
            ValueError: If duplicate paths are found.
        """
        if not result_routes:
            return

        paths = [route.get("path") for route in result_routes if isinstance(route, dict)]
        if len(paths) != len(set(paths)):
            duplicates = [p for p in paths if paths.count(p) > 1]
            raise ValueError(
                f"Route paths must be unique. Duplicate paths found: {set(duplicates)}"
            )

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

        if stops:
            default_route = self._create_default_route(stops, toml_data)
            if default_route:
                result_routes.append(default_route)

        if routes:
            self._validate_and_add_routes(routes, result_routes)

        self._validate_unique_paths(result_routes)

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
