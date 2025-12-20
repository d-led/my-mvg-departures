"""12-factor configuration adapter using environment variables and optional TOML config."""

import json
import os
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback for older Python

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
    mvg_api_timeout: int = Field(
        default=10, description="Timeout for MVG API requests in seconds"
    )
    mvg_api_limit: int = Field(
        default=20, description="Maximum number of departures to fetch per station"
    )
    mvg_api_offset_minutes: int = Field(
        default=0, description="Offset in minutes for departure queries"
    )

    # Display configuration
    time_format: str = Field(
        default="minutes", description="Time format: 'minutes' or 'at'"
    )
    refresh_interval_seconds: int = Field(
        default=30, description="Interval between departure updates in seconds"
    )

    # Stop configuration (JSON string or TOML file path)
    stops_config: str = Field(
        default='[{"station_id": "de:09162:100", "station_name": "Giesing", "direction_mappings": {"->Balanstr.": ["Messestadt", "Messestadt West"], "->Klinikum": ["Klinikum", "Klinikum Großhadern", "Klinikum Harlaching"], "->Tegernseer": ["Ackermannbogen", "Tegernseer"], "->Stadt": ["Gondrellplatz", "Marienplatz", "Hauptbahnhof"]}, "max_departures_per_stop": 30}]',
        description="JSON array of stop configurations, or path to TOML config file",
    )
    
    # TOML config file path (optional, overrides stops_config if set)
    # If not set, will try config.example.toml in project root as fallback
    config_file: str | None = Field(
        default="config.example.toml",
        description="Path to TOML configuration file for detailed stop mappings",
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

    @field_validator("stops_config")
    @classmethod
    def validate_stops_config(cls, v: str) -> str:
        """Validate stops_config is valid JSON."""
        import json

        try:
            json.loads(v)
        except json.JSONDecodeError as e:
            raise ValueError(f"stops_config must be valid JSON: {e}") from e
        return v

    def get_stops_config(self) -> list[dict[str, Any]]:
        """Parse and return stops configuration as a list of dicts.
        
        Supports both JSON string (from env var) and TOML file (from config_file).
        TOML file takes precedence if config_file is set and exists.
        Defaults to config.example.toml if available, otherwise falls back to JSON default.
        """
        # If config_file is set, try to load from TOML
        if self.config_file:
            config_path = Path(self.config_file)
            # Only use TOML if file exists (don't error on missing default)
            if config_path.exists():
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
                    
                    stops = toml_data.get("stops", [])
                    if not isinstance(stops, list):
                        raise ValueError("TOML config 'stops' must be a list")
                    # Filter out stops with placeholder IDs
                    stops = [s for s in stops if s.get("station_id", "").find("XXX") == -1]
                    if stops:
                        return stops
            # If config_file was explicitly set but doesn't exist, raise error
            elif self.config_file != "config.example.toml":  # Allow missing default
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        # Fallback to JSON from env var or default
        stops = json.loads(self.stops_config)
        return stops

