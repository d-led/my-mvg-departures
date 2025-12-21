"""Protocol for formatting departure times."""

from datetime import datetime, timedelta
from typing import Protocol

from mvg_departures.domain.models.departure import Departure


class DepartureFormatterProtocol(Protocol):
    """Protocol for formatting departure times and durations."""

    def format_departure_time(self, departure: Departure) -> str:
        """Format departure time according to configuration.

        Args:
            departure: The departure to format.

        Returns:
            Formatted time string (either relative like "5m" or absolute like "14:30").
        """
        ...

    def format_departure_time_relative(self, departure: Departure) -> str:
        """Format departure time as relative in compact format (e.g., '5m', '2h40m', 'now').

        Args:
            departure: The departure to format.

        Returns:
            Relative time string like "5m" or "2h40m" or "now".
        """
        ...

    def format_departure_time_absolute(self, departure: Departure) -> str:
        """Format departure time as absolute (HH:mm format).

        Args:
            departure: The departure to format.

        Returns:
            Absolute time string like "14:30".
        """
        ...

    def format_compact_duration(self, delta: timedelta) -> str:
        """Format timedelta as compact hours and minutes (e.g., '2h40m', '5m', 'now').

        Args:
            delta: The time delta to format.

        Returns:
            Compact duration string like "2h40m" or "5m" or "now".
        """
        ...

    def format_update_time(self, update_time: datetime | None) -> str:
        """Format last update time.

        Args:
            update_time: The update time to format, or None.

        Returns:
            Formatted time string or "Never" if None.
        """
        ...
