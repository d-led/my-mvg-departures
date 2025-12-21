"""Formatter for departure times."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from mvg_departures.adapters.config.app_config import AppConfig
from mvg_departures.domain.contracts.departure_formatter import DepartureFormatterProtocol
from mvg_departures.domain.models.departure import Departure


class DepartureFormatter(DepartureFormatterProtocol):
    """Formatter for departure times based on configuration."""

    def __init__(self, config: AppConfig) -> None:
        """Initialize the formatter.

        Args:
            config: Application configuration with timezone and time format settings.
        """
        self.config = config

    def format_departure_time(self, departure: Departure) -> str:
        """Format departure time according to configuration."""
        # Convert to configured timezone
        server_timezone = ZoneInfo(self.config.timezone)
        now = datetime.now(UTC).astimezone(server_timezone)
        time_until = departure.time.astimezone(server_timezone)

        if self.config.time_format == "minutes":
            delta = time_until - now
            if delta.total_seconds() < 0:
                return "now"
            # Format as compact hours and minutes (e.g., "2h40m")
            return self.format_compact_duration(delta)
        # "at" format
        return time_until.strftime("%H:%M")

    def format_departure_time_relative(self, departure: Departure) -> str:
        """Format departure time as relative in compact format (e.g., '5m', '2h40m', 'now')."""
        # Convert to configured timezone
        server_timezone = ZoneInfo(self.config.timezone)
        now = datetime.now(UTC).astimezone(server_timezone)
        time_until = departure.time.astimezone(server_timezone)
        delta = time_until - now
        if delta.total_seconds() < 0:
            return "now"
        # Format as compact hours and minutes (e.g., "2h40m")
        return self.format_compact_duration(delta)

    def format_departure_time_absolute(self, departure: Departure) -> str:
        """Format departure time as absolute (HH:mm format)."""
        # Convert to configured timezone
        server_timezone = ZoneInfo(self.config.timezone)
        time_until = departure.time.astimezone(server_timezone)
        return time_until.strftime("%H:%M")

    def format_compact_duration(self, delta: timedelta) -> str:
        """Format timedelta as compact hours and minutes (e.g., '2h40m', '5m', 'now')."""
        total_seconds = int(delta.total_seconds())
        if total_seconds < 0:
            return "now"
        if total_seconds < 60:
            return "<1m"

        total_minutes = total_seconds // 60
        if total_minutes < 60:
            return f"{total_minutes}m"

        hours = total_minutes // 60
        minutes = total_minutes % 60
        if minutes == 0:
            return f"{hours}h"
        return f"{hours}h{minutes}m"

    def format_update_time(self, update_time: datetime | None) -> str:
        """Format last update time."""
        if not update_time:
            return "Never"
        return update_time.strftime("%H:%M:%S")
