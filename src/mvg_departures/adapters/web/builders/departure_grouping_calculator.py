"""Calculator for departure grouping display data."""

import hashlib
from typing import Any

from mvg_departures.adapters.config.app_config import AppConfig
from mvg_departures.domain.contracts.departure_formatter import DepartureFormatterProtocol
from mvg_departures.domain.contracts.departure_grouping_calculator import (
    DepartureGroupingCalculatorProtocol,
)
from mvg_departures.domain.models.departure import Departure
from mvg_departures.domain.models.stop_configuration import StopConfiguration


def generate_pastel_color_from_text(text: str, brightness: float = 0.7, index: int = 0) -> str:
    """Generate a stable pastel color from text using hash-based mapping.

    The color is designed to work well in both light and dark modes,
    providing good contrast for both black and white text.
    Uses index to ensure better color distribution across headers.

    Args:
        text: The text to generate a color for (e.g., route header).
        brightness: Brightness adjustment factor (0.0-1.0). Default 0.7.
                    Lower values = darker, higher values = lighter.
        index: Optional index to add variation and ensure better distribution.

    Returns:
        A hex color code (e.g., "#A8D5E2").
    """
    # Create a stable hash from the text
    hash_obj = hashlib.md5(text.encode("utf-8"))
    hash_int = int(hash_obj.hexdigest(), 16)

    # Use index to add variation and ensure better color distribution
    # Combine hash with index using a prime multiplier for better distribution
    combined_seed = (hash_int + index * 137) % (2**32)

    # Use the hash to generate HSL values
    # Hue: Use golden ratio multiplier for better distribution across spectrum
    # This ensures colors are more evenly spread out, even for similar headers
    golden_ratio = 0.618033988749895
    # Use different parts of the hash for base hue and offset
    hash_part1 = (hash_int >> 16) & 0xFFFF  # Upper 16 bits
    hash_part2 = hash_int & 0xFFFF  # Lower 16 bits
    hue_base = hash_part1 % 360
    # Golden ratio spacing ensures headers are well-distributed even if text is similar
    hue_offset = int((index * golden_ratio * 360) % 360)
    # Also add some variation from the second hash part
    hue_variation = (hash_part2 % 60) - 30  # -30 to +30 degrees
    hue = (hue_base + hue_offset + hue_variation) % 360

    # Saturation: Increased range (55-80%) for more vibrant, distinct colors
    # Higher saturation makes colors more distinguishable and cascading
    saturation = 55 + (combined_seed % 26)  # 55-80%

    # Lightness: base range adjusted by brightness parameter
    # brightness 0.0 = very dark (30-40%), 0.2 = dark (40-50%), 0.7 = medium (65-75%), 1.0 = light (75-85%)
    # Use a non-linear mapping for better control: brightness^1.5 gives smoother transitions
    brightness_adjusted = brightness**1.5
    base_lightness_min = 30 + (brightness_adjusted * 45)  # 30-75
    base_lightness_max = 40 + (brightness_adjusted * 45)  # 40-85
    lightness_range = int(base_lightness_max - base_lightness_min)
    lightness = int(base_lightness_min) + (hash_int % max(1, lightness_range))

    # Convert HSL to RGB
    # Normalize values
    h = hue / 360.0
    s = saturation / 100.0
    light = lightness / 100.0

    # HSL to RGB conversion
    if s == 0:
        r = g = b = light
    else:

        def hue_to_rgb(p: float, q: float, t: float) -> float:
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

        q = light * (1 + s) if light < 0.5 else light + s - light * s
        p = 2 * light - q
        r = hue_to_rgb(p, q, h + 1 / 3)
        g = hue_to_rgb(p, q, h)
        b = hue_to_rgb(p, q, h - 1 / 3)

    # Convert to 0-255 range and format as hex
    r_hex = f"{int(r * 255):02x}"
    g_hex = f"{int(g * 255):02x}"
    b_hex = f"{int(b * 255):02x}"

    return f"#{r_hex}{g_hex}{b_hex}"


class DepartureGroupingCalculator(DepartureGroupingCalculatorProtocol):
    """Calculates display data structure from departure groups."""

    def __init__(
        self,
        stop_configs: list[StopConfiguration],
        config: AppConfig,
        formatter: DepartureFormatterProtocol,
        random_header_colors: bool = False,
        header_background_brightness: float = 0.7,
    ) -> None:
        """Initialize the departure grouping calculator.

        Args:
            stop_configs: List of stop configurations.
            config: Application configuration.
            formatter: Departure formatter for time formatting.
            random_header_colors: If True, generate hash-based pastel colors for headers.
            header_background_brightness: Brightness adjustment for random header colors (0.0-1.0).
        """
        self.stop_configs = stop_configs
        self.config = config
        self.formatter = formatter
        self.random_header_colors = random_header_colors
        self.header_background_brightness = header_background_brightness

    def calculate_display_data(
        self,
        direction_groups: list[tuple[str, str, str, list[Departure], bool | None, float | None]],
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

        for (
            station_id,
            stop_name,
            direction_name,
            departures,
            random_colors,
            brightness,
        ) in direction_groups:
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

                group_data: dict[str, Any] = {
                    "station_id": station_id,
                    "stop_name": stop_name,
                    "header": combined_header,
                    "departures": departure_data,
                    "is_new_stop": is_new_stop,
                    "random_header_colors": random_colors,
                    "header_background_brightness": brightness,
                }

                groups_with_departures.append(group_data)
                stops_with_departures.add(stop_name)

        # Mark first header and last group
        if groups_with_departures:
            groups_with_departures[0]["is_first_header"] = True
            groups_with_departures[0]["is_first_group"] = True
            groups_with_departures[-1]["is_last_group"] = True
            # Set flags for middle groups (if any)
            for i in range(1, len(groups_with_departures) - 1):
                groups_with_departures[i]["is_first_header"] = False
                groups_with_departures[i]["is_first_group"] = False
                groups_with_departures[i]["is_last_group"] = False
            # If more than one group, first is not last, and last is not first
            if len(groups_with_departures) > 1:
                groups_with_departures[0]["is_last_group"] = False
                groups_with_departures[-1]["is_first_header"] = False
                groups_with_departures[-1]["is_first_group"] = False

        # Generate header colors for non-first headers if random_header_colors is enabled
        # First header uses the configured banner_color, so skip it
        # Use config settings from group data (passed directly, no matching needed)
        # Track index for better color distribution
        color_index = 0
        for group in groups_with_departures:
            if not group.get("is_first_header", False):
                header_text = group.get("header", "")
                # Get settings from group data (stop-level if provided, None means use route-level)
                group_random_colors = group.get("random_header_colors")
                group_brightness = group.get("header_background_brightness")

                if header_text:
                    # Use stop-level setting if provided, otherwise use route-level default
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

                    if use_random_colors:
                        group["header_color"] = generate_pastel_color_from_text(
                            header_text, brightness, color_index
                        )
                        color_index += 1

        # Find stops without departures
        configured_stops = {stop_config.station_name for stop_config in self.stop_configs}
        stops_without_departures = sorted(configured_stops - stops_with_departures)

        return {
            "groups_with_departures": groups_with_departures,
            "stops_without_departures": stops_without_departures,
            "has_departures": len(groups_with_departures) > 0,
            "font_size_no_departures": self.config.font_size_no_departures_available,
        }
