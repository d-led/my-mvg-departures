"""Calculator for departure grouping display data."""

import hashlib
from dataclasses import dataclass
from typing import Any

from mvg_departures.adapters.config.app_config import AppConfig
from mvg_departures.domain.contracts.departure_formatter import DepartureFormatterProtocol
from mvg_departures.domain.contracts.departure_grouping_calculator import (
    DepartureGroupingCalculatorProtocol,
)
from mvg_departures.domain.models.direction_group_with_metadata import DirectionGroupWithMetadata
from mvg_departures.domain.models.stop_configuration import StopConfiguration


@dataclass(frozen=True)
class HeaderDisplaySettings:
    """Settings for header color display."""

    random_header_colors: bool = False
    header_background_brightness: float = 0.7
    random_color_salt: int = 0


@dataclass(frozen=True)
class DepartureGroupingCalculatorConfig:
    """Configuration for departure grouping calculator."""

    stop_configs: list[StopConfiguration]
    config: AppConfig


def _calculate_hsl_from_hash(hash_int: int, brightness: float) -> tuple[float, float, float]:
    """Calculate HSL values from hash and brightness."""
    hash_part1 = (hash_int >> 16) & 0xFFFF  # Upper 16 bits
    hash_part2 = hash_int & 0xFFFF  # Lower 16 bits
    hue_base = hash_part1 % 360
    hue_variation = (hash_part2 % 60) - 30  # -30 to +30 degrees
    hue = (hue_base + hue_variation) % 360

    saturation = 55 + (hash_int % 26)  # 55-80%

    brightness_adjusted = brightness**1.5
    base_lightness_min = 30 + (brightness_adjusted * 45)  # 30-75
    base_lightness_max = 40 + (brightness_adjusted * 45)  # 40-85
    lightness_range = int(base_lightness_max - base_lightness_min)
    lightness = int(base_lightness_min) + (hash_int % max(1, lightness_range))

    return hue, saturation, lightness


def _hue_to_rgb(p: float, q: float, t: float) -> float:
    """Convert hue component to RGB value."""
    if t < 0:
        t += 1
    if t > 1:
        t -= 1
    if t < 1 / 6:
        return p + (q - p) * 6 * t
    if t < 1 / 2:
        return q
    if t < 2 / 3:
        return p + (q - p) * (2 / 3 - t) * 6
    return p


def _hsl_to_rgb(hue: float, saturation: float, lightness: float) -> tuple[float, float, float]:
    """Convert HSL to RGB values."""
    h = hue / 360.0
    s = saturation / 100.0
    light = lightness / 100.0

    if s == 0:
        return light, light, light

    q = light * (1 + s) if light < 0.5 else light + s - light * s
    p = 2 * light - q
    r = _hue_to_rgb(p, q, h + 1 / 3)
    g = _hue_to_rgb(p, q, h)
    b = _hue_to_rgb(p, q, h - 1 / 3)

    return r, g, b


def _rgb_to_hex(r: float, g: float, b: float) -> str:
    """Convert RGB values to hex color code."""
    r_hex = f"{int(r * 255):02x}"
    g_hex = f"{int(g * 255):02x}"
    b_hex = f"{int(b * 255):02x}"
    return f"#{r_hex}{g_hex}{b_hex}"


def generate_pastel_color_from_text(
    text: str, brightness: float = 0.7, _index: int = 0, salt: int = 0
) -> str:
    """Generate a stable pastel color from text using hash-based mapping.

    The color is designed to work well in both light and dark modes,
    providing good contrast for both black and white text.
    Color depends only on the text and salt, not on position/index.

    Args:
        text: The text to generate a color for (e.g., route header).
        brightness: Brightness adjustment factor (0.0-1.0). Default 0.7.
                    Lower values = darker, higher values = lighter.
        _index: Deprecated parameter (kept for backward compatibility, not used).
        salt: Salt value to influence color generation (default 0).

    Returns:
        A hex color code (e.g., "#A8D5E2").
    """
    hash_obj = hashlib.md5(f"{text}:{salt}".encode())
    hash_int = int(hash_obj.hexdigest(), 16)

    hue, saturation, lightness = _calculate_hsl_from_hash(hash_int, brightness)
    r, g, b = _hsl_to_rgb(hue, saturation, lightness)
    return _rgb_to_hex(r, g, b)


class DepartureGroupingCalculator(DepartureGroupingCalculatorProtocol):
    """Calculates display data structure from departure groups."""

    def __init__(
        self,
        config: DepartureGroupingCalculatorConfig,
        formatter: DepartureFormatterProtocol,
        header_display: HeaderDisplaySettings | None = None,
    ) -> None:
        """Initialize the departure grouping calculator.

        Args:
            config: Configuration for the calculator.
            formatter: Departure formatter for time formatting.
            header_display: Settings for header color display. If None, uses defaults.
        """
        self.stop_configs = config.stop_configs
        self.config = config.config
        self.formatter = formatter
        header_settings = header_display or HeaderDisplaySettings()
        self.random_header_colors = header_settings.random_header_colors
        self.header_background_brightness = header_settings.header_background_brightness
        self.random_color_salt = header_settings.random_color_salt

    def _format_departure_data(self, departure: Any) -> dict[str, Any]:
        """Format a single departure for display.

        Args:
            departure: Departure object to format.

        Returns:
            Dictionary with formatted departure data.
        """
        time_str = self.formatter.format_departure_time(departure)
        time_str_relative = self.formatter.format_departure_time_relative(departure)
        time_str_absolute = self.formatter.format_departure_time_absolute(departure)

        platform_display = str(departure.platform) if departure.platform is not None else None
        platform_aria = f", Platform {platform_display}" if platform_display else ""

        delay_minutes, delay_aria, has_delay = self._format_delay(departure)
        aria_label = self._build_aria_label(departure, time_str, platform_aria, delay_aria)

        # Normalize transport_type for CSS class: "U-Bahn" -> "ubahn", "S-Bahn" -> "sbahn"
        transport_type_css = (
            departure.transport_type.lower().replace("-", "").replace(" ", "")
            if departure.transport_type
            else "bus"
        )

        return {
            "line": departure.line,
            "destination": departure.destination,
            "platform": platform_display,
            "time_str": time_str,
            "time_str_relative": time_str_relative,
            "time_str_absolute": time_str_absolute,
            "cancelled": departure.is_cancelled,
            "has_delay": has_delay,
            "delay_minutes": delay_minutes,
            "is_realtime": departure.is_realtime,
            "aria_label": aria_label,
            "transport_type": departure.transport_type,
            "transport_type_css": transport_type_css,
        }

    def _format_delay(self, departure: Any) -> tuple[int | None, str, bool]:
        """Format delay information for a departure.

        Args:
            departure: Departure object.

        Returns:
            Tuple of (delay_minutes, delay_aria, has_delay).
        """
        has_delay = departure.delay_seconds is not None and departure.delay_seconds > 60
        if not has_delay or departure.delay_seconds is None:
            return None, "", False

        delay_minutes = departure.delay_seconds // 60
        delay_aria = f", delayed by {delay_minutes} minutes"
        return delay_minutes, delay_aria, True

    def _build_aria_label(
        self, departure: Any, time_str: str, platform_aria: str, delay_aria: str
    ) -> str:
        """Build ARIA label for a departure.

        Args:
            departure: Departure object.
            time_str: Formatted time string.
            platform_aria: Platform ARIA text.
            delay_aria: Delay ARIA text.

        Returns:
            ARIA label string.
        """
        status_parts = []
        if departure.is_cancelled:
            status_parts.append("cancelled")
        if departure.is_realtime:
            status_parts.append("real-time")
        status_text = ", ".join(status_parts) if status_parts else "scheduled"

        return (
            f"Line {departure.line} to {departure.destination}"
            f"{platform_aria}"
            f", departing in {time_str}"
            f"{delay_aria}"
            f", {status_text}"
        )

    def _process_direction_groups(
        self, direction_groups: list[DirectionGroupWithMetadata]
    ) -> tuple[list[dict[str, Any]], set[str]]:
        """Process direction groups and build groups_with_departures.

        Args:
            direction_groups: List of direction groups with metadata.

        Returns:
            Tuple of (groups_with_departures, stops_with_departures).
        """
        groups_with_departures: list[dict[str, Any]] = []
        stops_with_departures: set[str] = set()
        current_stop: str | None = None

        for group in direction_groups:
            if not group.departures:
                continue

            direction_clean = group.direction_name.lstrip("->")
            combined_header = f"{group.stop_name} → {direction_clean}"

            is_new_stop = group.stop_name != current_stop
            if is_new_stop:
                current_stop = group.stop_name

            sorted_departures = sorted(group.departures, key=lambda d: d.time)
            departure_data = [self._format_departure_data(dep) for dep in sorted_departures]

            group_data: dict[str, Any] = {
                "station_id": group.station_id,
                "stop_name": group.stop_name,
                "header": combined_header,
                "departures": departure_data,
                "is_new_stop": is_new_stop,
                "random_header_colors": group.random_header_colors,
                "header_background_brightness": group.header_background_brightness,
                "random_color_salt": group.random_color_salt,
            }

            groups_with_departures.append(group_data)
            stops_with_departures.add(group.stop_name)

        return groups_with_departures, stops_with_departures

    def _mark_first_last_headers(self, groups_with_departures: list[dict[str, Any]]) -> None:
        """Mark first and last headers in groups_with_departures.

        Args:
            groups_with_departures: List of group dictionaries to modify.
        """
        if not groups_with_departures:
            return

        groups_with_departures[0]["is_first_header"] = True
        groups_with_departures[0]["is_first_group"] = True
        groups_with_departures[-1]["is_last_group"] = True

        for i in range(1, len(groups_with_departures) - 1):
            groups_with_departures[i]["is_first_header"] = False
            groups_with_departures[i]["is_first_group"] = False
            groups_with_departures[i]["is_last_group"] = False

        if len(groups_with_departures) > 1:
            groups_with_departures[0]["is_last_group"] = False
            groups_with_departures[-1]["is_first_header"] = False
            groups_with_departures[-1]["is_first_group"] = False

    def _generate_header_colors(self, groups_with_departures: list[dict[str, Any]]) -> None:
        """Generate header colors for non-first headers if enabled.

        Args:
            groups_with_departures: List of group dictionaries to modify.
        """
        for group_dict in groups_with_departures:
            if group_dict.get("is_first_header", False):
                continue

            header_text = group_dict.get("header", "")
            if not header_text:
                continue

            group_random_colors = group_dict.get("random_header_colors")
            group_brightness = group_dict.get("header_background_brightness")
            group_salt = group_dict.get("random_color_salt")

            use_random_colors = (
                group_random_colors
                if group_random_colors is not None
                else self.random_header_colors
            )
            brightness = (
                group_brightness
                if group_brightness is not None
                else self.header_background_brightness
            )
            salt = group_salt if group_salt is not None else self.random_color_salt

            if use_random_colors:
                group_dict["header_color"] = generate_pastel_color_from_text(
                    header_text, brightness, 0, salt
                )

    def _find_stops_without_departures(self, stops_with_departures: set[str]) -> list[str]:
        """Find stops that have no departures.

        Args:
            stops_with_departures: Set of stop names that have departures.

        Returns:
            Sorted list of stop names without departures.
        """
        configured_stops = {stop_config.station_name for stop_config in self.stop_configs}
        return sorted(configured_stops - stops_with_departures)

    def calculate_display_data(
        self,
        direction_groups: list[DirectionGroupWithMetadata],
    ) -> dict[str, Any]:
        """Calculate display data structure from direction groups.

        Args:
            direction_groups: List of direction groups with metadata.

        Returns:
            Dictionary with display data including groups_with_departures,
            stops_without_departures, has_departures, and font_size_no_departures.
        """
        groups_with_departures, stops_with_departures = self._process_direction_groups(
            direction_groups
        )

        self._mark_first_last_headers(groups_with_departures)
        self._generate_header_colors(groups_with_departures)

        stops_without_departures = self._find_stops_without_departures(stops_with_departures)

        return {
            "groups_with_departures": groups_with_departures,
            "stops_without_departures": stops_without_departures,
            "has_departures": len(groups_with_departures) > 0,
            "font_size_no_departures": self.config.font_size_no_departures_available,
        }
