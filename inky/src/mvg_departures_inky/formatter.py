"""Inky-specific departure formatter with slow refresh compensation."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from mvg_departures.domain.contracts.departure_formatter import DepartureFormatterProtocol
from mvg_departures.domain.models.departure import Departure

from .config import InkyDisplayConfig


class InkyDepartureFormatter(DepartureFormatterProtocol):
    """Departure formatter for Inky displays with slow refresh compensation.

    Wraps the base DepartureFormatter and applies compensation for slow e-ink refresh.
    When calculating relative times, assumes we are at now() + compensation seconds
    (when the display will finish updating).
    """

    def __init__(
        self, base_formatter: DepartureFormatterProtocol, inky_config: InkyDisplayConfig
    ) -> None:
        """Initialize Inky departure formatter.

        Args:
            base_formatter: Base formatter to wrap (typically DepartureFormatter).
            inky_config: Inky display configuration with compensation settings.
        """
        self.base_formatter = base_formatter
        self.config = base_formatter.config if hasattr(base_formatter, "config") else None
        self.compensation_seconds = inky_config.account_for_slow_refresh_seconds

    def format_departure_time(self, departure: Departure) -> str:
        """Format departure time according to configuration."""
        # For absolute format, use base formatter (no compensation needed)
        if self.config and self.config.time_format == "at":
            return self.base_formatter.format_departure_time(departure)

        # For relative format, apply compensation
        return self.format_departure_time_relative(departure)

    def format_departure_time_relative(self, departure: Departure) -> str:
        """Format departure time as relative with compensation applied."""
        if self.compensation_seconds <= 0:
            return self.base_formatter.format_departure_time_relative(departure)

        # Apply compensation: assume we are at now() + compensation
        # Convert to configured timezone
        server_timezone = ZoneInfo(self.config.timezone) if self.config else ZoneInfo("UTC")
        now = datetime.now(UTC).astimezone(server_timezone)
        # Add compensation to "now" to simulate being in the future
        compensated_now = now + timedelta(seconds=self.compensation_seconds)
        time_until = departure.time.astimezone(server_timezone)
        delta = time_until - compensated_now

        if delta.total_seconds() < 0:
            return "now"

        # Use base formatter's format_compact_duration method
        return self.base_formatter.format_compact_duration(delta)

    def format_departure_time_absolute(self, departure: Departure) -> str:
        """Format departure time as absolute (HH:mm format)."""
        # Absolute times don't need compensation (they're just clock times)
        return self.base_formatter.format_departure_time_absolute(departure)

    def format_compact_duration(self, delta: timedelta) -> str:
        """Format timedelta as compact hours and minutes."""
        return self.base_formatter.format_compact_duration(delta)

    def format_update_time(self, update_time: datetime | None) -> str:
        """Format last update time."""
        return self.base_formatter.format_update_time(update_time)
