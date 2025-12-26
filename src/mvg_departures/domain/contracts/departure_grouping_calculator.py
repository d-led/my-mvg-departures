"""Interface for calculating departure grouping display data."""

from typing import Any, Protocol

from mvg_departures.domain.models.departure import Departure


class DepartureGroupingCalculatorProtocol(Protocol):
    """Protocol for calculating display data from departure groups."""

    def calculate_display_data(
        self,
        direction_groups: list[tuple[str, str, str, list[Departure], bool | None, float | None]],
    ) -> dict[str, Any]:
        """Calculate display data structure from direction groups.

        Args:
            direction_groups: List of tuples containing (station_id, stop_name, direction_name, departures, random_header_colors, header_background_brightness).

        Returns:
            Dictionary with display data including groups_with_departures,
            stops_without_departures, has_departures, and font_size_no_departures.
        """
        ...
