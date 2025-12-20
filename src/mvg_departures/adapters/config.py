"""12-factor configuration adapter using environment variables and TOML config."""

from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore[import-untyped,no-redef]  # Fallback for older Python

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

    # MVG API configuration
    mvg_api_timeout: int = Field(default=10, description="Timeout for MVG API requests in seconds")
    mvg_api_limit: int = Field(
        default=20, description="Maximum number of departures to fetch per station"
    )
    mvg_api_offset_minutes: int = Field(
        default=0, description="Offset in minutes for departure queries"
    )

    # Display configuration
    time_format: str = Field(default="minutes", description="Time format: 'minutes' or 'at'")
    refresh_interval_seconds: int = Field(
        default=30, description="Interval between departure updates in seconds"
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

    def get_stops_config(self) -> list[dict[str, Any]]:
        """Parse and return stops configuration as a list of dicts from TOML file.

        Loads configuration from the TOML file specified in config_file.
        Defaults to config.example.toml if available.
        """
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

            stops = toml_data.get("stops", [])
            if not isinstance(stops, list):
                raise ValueError("TOML config 'stops' must be a list")
            # Filter out stops with placeholder IDs
            stops = [s for s in stops if s.get("station_id", "").find("XXX") == -1]
            return stops
