"""Renderer for Inky display."""

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from mvg_departures.domain.models.departure import Departure
from mvg_departures.domain.models.grouped_departures import GroupedDepartures

from .config import InkyDisplayConfig

logger = logging.getLogger(__name__)


class InkyRenderer:
    """Renders departures to Inky display using PIL."""

    def __init__(self, config: InkyDisplayConfig, display: Any) -> None:
        """Initialize renderer.

        Args:
            config: Display configuration.
            display: Inky display instance.
        """
        self.config = config
        self.display = display
        self._font_cache: dict[int, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}
        self._icon_cache: dict[str, Image.Image | None] = {}
        self._use_relative_time = False
        self._last_time_toggle = datetime.now(UTC)
        
        # Store display colors for icon creation
        self._white = getattr(display, "WHITE", 0)
        self._black = getattr(display, "BLACK", 1)

    def _get_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Get font at specified size, with caching."""
        if size not in self._font_cache:
            try:
                # Try to use a system font
                self._font_cache[size] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
            except Exception:
                try:
                    # Fallback to default font
                    self._font_cache[size] = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", size)
                except Exception:
                    # Last resort: default PIL font
                    logger.warning(f"Could not load system font, using default for size {size}")
                    self._font_cache[size] = ImageFont.load_default()
        return self._font_cache[size]

    def _load_icon(self, transport_type: str) -> Image.Image | None:
        """Load route icon for transport type.
        
        For now, creates a simple text-based icon. In production, you could:
        - Use cairosvg to convert SVG to PNG
        - Pre-convert SVGs to PNGs and load those
        - Use a library like svglib to render SVGs
        
        Args:
            transport_type: Type of transport (U-Bahn, S-Bahn, Tram, Bus).
            
        Returns:
            PIL Image with icon, or None if not available.
        """
        if transport_type in self._icon_cache:
            return self._icon_cache[transport_type]

        # Create a simple text-based icon as placeholder
        # Transport type abbreviations
        abbrev_map = {
            "U-Bahn": "U",
            "S-Bahn": "S",
            "Tram": "T",
            "Bus": "B",
        }
        abbrev = abbrev_map.get(transport_type, "?")

        try:
            # Create icon with text (use same palette mode as main image)
            icon = Image.new("P", (self.config.route_icon_size, self.config.route_icon_size), self._white)
            # Copy palette from display if available
            if hasattr(self.display, "palette"):
                icon.putpalette(self.display.palette)
            icon_draw = ImageDraw.Draw(icon)
            
            # Use smaller font for icon
            icon_font_size = max(12, self.config.route_icon_size // 2)
            icon_font = self._get_font(icon_font_size)
            
            # Center text in icon
            bbox = icon_font.getbbox(abbrev)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (self.config.route_icon_size - text_width) // 2
            y = (self.config.route_icon_size - text_height) // 2
            
            icon_draw.text((x, y), abbrev, self._black, font=icon_font)
            
            self._icon_cache[transport_type] = icon
            return icon
        except Exception as e:
            logger.warning(f"Could not create icon for {transport_type}: {e}")
            self._icon_cache[transport_type] = None
            return None

    def _calculate_font_size(self, departures: list[Departure]) -> int:
        """Calculate optimal font size to fit all departures.

        Args:
            departures: List of departures to display.

        Returns:
            Optimal font size.
        """
        num_departures = len(departures)
        if num_departures == 0:
            return self.config.max_font_size

        # Try font sizes from max to min
        for font_size in range(
            self.config.max_font_size,
            self.config.min_font_size - 1,
            -self.config.font_size_step,
        ):
            font = self._get_font(font_size)
            # Get line height
            bbox = font.getbbox("Mg")
            line_height = bbox[3] - bbox[1] + self.config.line_spacing

            total_height = line_height * num_departures
            if total_height <= self.config.usable_height:
                return font_size

        # If nothing fits, return minimum
        return self.config.min_font_size

    def _format_time(self, departure: Departure) -> str:
        """Format departure time (absolute or relative).

        Args:
            departure: Departure to format.

        Returns:
            Formatted time string.
        """
        if not self.config.show_time:
            return ""

        now = datetime.now(UTC)
        if departure.time.tzinfo is None:
            dep_time = departure.time.replace(tzinfo=UTC)
        else:
            dep_time = departure.time.astimezone(UTC)

        # Toggle between absolute and relative time
        if (now - self._last_time_toggle).total_seconds() >= self.config.time_toggle_interval:
            self._use_relative_time = not self._use_relative_time
            self._last_time_toggle = now

        if self._use_relative_time:
            delta = dep_time - now
            minutes = int(delta.total_seconds() / 60)
            if minutes < 0:
                return "now"
            if minutes == 0:
                return "<1m"
            return f"{minutes}m"
        else:
            # Format as HH:MM
            return dep_time.strftime("%H:%M")

    def _truncate_text(
        self, text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: int
    ) -> str:
        """Truncate text to fit within max_width.

        Args:
            text: Text to truncate.
            font: Font to measure with.
            max_width: Maximum width in pixels.

        Returns:
            Truncated text with ellipsis if needed.
        """
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        if text_width <= max_width:
            return text

        # Binary search for truncation point
        low, high = 0, len(text)
        while low < high:
            mid = (low + high + 1) // 2
            truncated = text[:mid] + "..."
            bbox = font.getbbox(truncated)
            if (bbox[2] - bbox[0]) <= max_width:
                low = mid
            else:
                high = mid - 1

        if low == 0:
            return "..."
        return text[:low] + "..."

    def render(self, direction_groups: list[GroupedDepartures]) -> Image.Image:
        """Render departures to PIL Image.

        Args:
            direction_groups: List of grouped departures.

        Returns:
            PIL Image ready to display.
        """
        # Flatten all departures from all groups
        all_departures: list[Departure] = []
        for group in direction_groups:
            all_departures.extend(group.departures)

        if not all_departures:
            return self._render_no_departures()

        # Calculate optimal font size
        font_size = self._calculate_font_size(all_departures)
        font = self._get_font(font_size)

        # Create image
        img = Image.new("P", (self.config.width, self.config.height), self._white)
        # Set palette if available
        if hasattr(self.display, "palette"):
            img.putpalette(self.display.palette)
        draw = ImageDraw.Draw(img)

        # Calculate line height
        bbox = font.getbbox("Mg")
        line_height = bbox[3] - bbox[1] + self.config.line_spacing

        # Calculate starting Y position (center vertically if fill_vertical_space)
        if self.config.fill_vertical_space:
            total_height = line_height * len(all_departures)
            start_y = self.config.padding + (self.config.usable_height - total_height) // 2
        else:
            start_y = self.config.padding

        # Render each departure
        y = start_y
        for departure in all_departures:
            self._render_departure_row(draw, departure, font, y)
            y += line_height

        return img

    def _render_departure_row(
        self,
        draw: ImageDraw.ImageDraw,
        departure: Departure,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        y: int,
    ) -> None:
        """Render a single departure row.

        Args:
            draw: PIL ImageDraw instance.
            departure: Departure to render.
            font: Font to use.
            y: Y position for this row.
        """
        x = self.config.padding

        # Draw route icon
        icon = self._load_icon(departure.transport_type)
        if icon:
            # Paste icon onto main image
            img = draw._image  # type: ignore[attr-defined]
            img.paste(icon, (x, y))
        x += self.config.route_icon_size + self.config.padding

        # Draw route number
        route_text = departure.line
        draw.text((x, y), route_text, self._black, font=font)
        x += self.config.route_number_width + self.config.padding

        # Draw destination (truncate if needed)
        destination_text = self._truncate_text(
            departure.destination, font, self.config.destination_section_width
        )
        draw.text((x, y), destination_text, self._black, font=font)

        # Draw platform
        platform_text = str(departure.platform) if departure.platform else ""
        platform_x = self.config.platform_section_x
        draw.text((platform_x, y), platform_text, self._black, font=font)

        # Draw time if enabled
        if self.config.show_time:
            time_text = self._format_time(departure)
            if time_text:
                bbox = font.getbbox("Mg")
                line_height = bbox[3] - bbox[1] + self.config.line_spacing
                time_y = y + line_height // 2  # Place time below platform
                draw.text((platform_x, time_y), time_text, self._black, font=font)

    def _render_no_departures(self) -> Image.Image:
        """Render 'No departures' message.

        Returns:
            PIL Image with no departures message.
        """
        img = Image.new("P", (self.config.width, self.config.height), self._white)
        # Set palette if available
        if hasattr(self.display, "palette"):
            img.putpalette(self.display.palette)
        draw = ImageDraw.Draw(img)

        font_size = 32
        font = self._get_font(font_size)
        text = "No departures available"

        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (self.config.width - text_width) // 2
        y = (self.config.height - text_height) // 2

        draw.text((x, y), text, self._black, font=font)
        return img
