"""Calculator for departure grouping display data."""

from typing import Any

from mvg_departures.adapters.config.app_config import AppConfig
from mvg_departures.domain.contracts.departure_formatter import DepartureFormatterProtocol
from mvg_departures.domain.contracts.departure_grouping_calculator import (
    DepartureGroupingCalculatorProtocol,
)
from mvg_departures.domain.models.departure import Departure
from mvg_departures.domain.models.stop_configuration import StopConfiguration


class DepartureGroupingCalculator(DepartureGroupingCalculatorProtocol):
    """Calculates display data structure from departure groups."""

    def __init__(
        self,
        stop_configs: list[StopConfiguration],
        config: AppConfig,
        formatter: DepartureFormatterProtocol,
    ) -> None:
        """Initialize the departure grouping calculator.

        Args:
            stop_configs: List of stop configurations.
            config: Application configuration.
            formatter: Departure formatter for time formatting.
        """
        self.stop_configs = stop_configs
        self.config = config
        self.formatter = formatter

    def calculate_display_data(
        self, direction_groups: list[tuple[str, str, list[Departure]]]
    ) -> dict[str, Any]:
        """Calculate display data structure from direction groups.

        Args:
            direction_groups: List of tuples containing (stop_name, direction_name, departures).

        Returns:
            Dictionary with display data including groups_with_departures,
            stops_without_departures, has_departures, and font_size_no_departures.
        """
        # Separate groups with departures from stops that have no departures
        groups_with_departures: list[dict[str, Any]] = []
        stops_with_departures: set[str] = set()
        current_stop: str | None = None

        for stop_name, direction_name, departures in direction_groups:
            if departures:
                direction_clean = direction_name.lstrip("->")
                combined_header = f"{stop_name} → {direction_clean}"

                # Check if this is a new stop
                is_new_stop = stop_name != current_stop
                if is_new_stop:
                    current_stop = stop_name

                # Prepare departures for this group
                sorted_departures = sorted(departures, key=lambda d: d.time)
                departure_data = []
                for departure in sorted_departures:
                    time_str = self.formatter.format_departure_time(departure)
                    time_str_relative = self.formatter.format_departure_time_relative(departure)
                    time_str_absolute = self.formatter.format_departure_time_absolute(departure)

                    # Format platform
                    platform_display = (
                        str(departure.platform) if departure.platform is not None else None
                    )
                    platform_aria = f", Platform {platform_display}" if platform_display else ""

                    # Format delay
                    delay_display = None
                    delay_aria = ""
                    has_delay = departure.delay_seconds is not None and departure.delay_seconds > 60
                    if has_delay and departure.delay_seconds is not None:
                        delay_minutes = departure.delay_seconds // 60
                        delay_display = f'<span class="delay-amount" aria-hidden="true">{delay_minutes}m 😞</span>'
                        delay_aria = f", delayed by {delay_minutes} minutes"

                    # Build ARIA label
                    status_parts = []
                    if departure.is_cancelled:
                        status_parts.append("cancelled")
                    if departure.is_realtime:
                        status_parts.append("real-time")
                    status_text = ", ".join(status_parts) if status_parts else "scheduled"

                    aria_label = (
                        f"Line {departure.line} to {departure.destination}"
                        f"{platform_aria}"
                        f", departing in {time_str}"
                        f"{delay_aria}"
                        f", {status_text}"
                    )

                    departure_data.append(
                        {
                            "line": departure.line,
                            "destination": departure.destination,
                            "platform": platform_display,
                            "time_str": time_str,
                            "time_str_relative": time_str_relative,
                            "time_str_absolute": time_str_absolute,
                            "cancelled": departure.is_cancelled,
                            "has_delay": has_delay,
                            "delay_display": delay_display,
                            "is_realtime": departure.is_realtime,
                            "aria_label": aria_label,
                        }
                    )

                groups_with_departures.append(
                    {
                        "stop_name": stop_name,
                        "header": combined_header,
                        "departures": departure_data,
                        "is_new_stop": is_new_stop,
                    }
                )
                stops_with_departures.add(stop_name)

        # Mark first header and last group
        if groups_with_departures:
            groups_with_departures[0]["is_first_header"] = True
            groups_with_departures[0]["is_first_group"] = True
            groups_with_departures[-1]["is_last_group"] = True
            for i in range(1, len(groups_with_departures) - 1):
                groups_with_departures[i]["is_first_header"] = False
                groups_with_departures[i]["is_first_group"] = False
                groups_with_departures[i]["is_last_group"] = False
            if len(groups_with_departures) > 1:
                groups_with_departures[-1]["is_first_header"] = False
                groups_with_departures[-1]["is_first_group"] = False

        # Find stops without departures
        configured_stops = {stop_config.station_name for stop_config in self.stop_configs}
        stops_without_departures = sorted(configured_stops - stops_with_departures)

        return {
            "groups_with_departures": groups_with_departures,
            "stops_without_departures": stops_without_departures,
            "has_departures": len(groups_with_departures) > 0,
            "font_size_no_departures": self.config.font_size_no_departures_available,
        }
