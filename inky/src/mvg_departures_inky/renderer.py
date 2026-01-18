"""Renderer for Inky display."""

import hashlib
import logging
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from mvg_departures.adapters.web.builders.departure_grouping_calculator import (
    DepartureGroupingCalculator,
    DepartureGroupingCalculatorConfig,
    HeaderDisplaySettings,
    generate_pastel_color_from_text,
)
from mvg_departures.adapters.web.formatters.departure_formatter import DepartureFormatter
from mvg_departures.domain.models.direction_group_with_metadata import (
    DirectionGroupWithMetadata,
)

from .config import InkyDisplayConfig

logger = logging.getLogger(__name__)


def _hex_to_inky_color(hex_color: str, display: Any) -> int:
    """Convert hex color to Inky e-ink color.
    
    Maps RGB hex colors to the closest e-ink color (black, white, red, yellow).
    Uses red or yellow for colored headers, preferring red for blue-ish colors.
    
    Args:
        hex_color: Hex color code (e.g., "#A8D5E2").
        display: Inky display instance.
        
    Returns:
        Inky color constant (WHITE=0, BLACK=1, RED=2, YELLOW=3).
    """
    # Remove # if present
    hex_color = hex_color.lstrip("#")
    
    # Parse RGB
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    
    # Calculate brightness
    brightness = (r * 0.299 + g * 0.587 + b * 0.114)
    
    # Very light colors -> white (but we want colored headers, so skip this)
    # Very dark colors -> black (but we want colored headers, so skip this)
    
    # For colored headers, map to red or yellow based on hue
    # Calculate hue
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    delta = max_val - min_val
    
    if delta == 0:
        # Grayscale - use red for headers
        return getattr(display, "RED", 2)
    
    # Determine hue
    if max_val == r:
        hue = ((g - b) / delta) % 6
    elif max_val == g:
        hue = (b - r) / delta + 2
    else:
        hue = (r - g) / delta + 4
    
    hue_deg = hue * 60
    
    # Map hue to red or yellow
    # Red: 0-30, 330-360 degrees (and blue-ish colors 200-270)
    # Yellow: 30-90 degrees
    # For blue-ish colors (180-270), use red as substitute
    if 30 <= hue_deg <= 90:
        return getattr(display, "YELLOW", 3)
    else:
        # Use red for everything else (including blue-ish colors)
        return getattr(display, "RED", 2)


def _get_default_header_color(display: Any) -> int:
    """Get default header color for e-ink display (blue-ish -> red).
    
    Args:
        display: Inky display instance.
        
    Returns:
        Inky color constant for headers (RED=2).
    """
    return getattr(display, "RED", 2)


class InkyRenderer:
    """Renders departures to Inky display using PIL."""

    def __init__(
        self,
        config: InkyDisplayConfig,
        display: Any,
        grouping_calculator: DepartureGroupingCalculator,
    ) -> None:
        """Initialize renderer.

        Args:
            config: Display configuration.
            display: Inky display instance.
            grouping_calculator: Departure grouping calculator (same as web version).
        """
        self.config = config
        self.display = display
        self.grouping_calculator = grouping_calculator
        self._font_cache: dict[int, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}
        self._icon_cache: dict[str, Image.Image | None] = {}
        self._use_relative_time = False  # Start with absolute time (HH:MM format)
        self._last_time_toggle = datetime.now(UTC)
        
        # Store display colors
        self._white = getattr(display, "WHITE", 0)
        self._black = getattr(display, "BLACK", 1)
        self._red = getattr(display, "RED", 2)
        self._yellow = getattr(display, "YELLOW", 3)

    def _get_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Get font at specified size, with caching."""
        if size not in self._font_cache:
            try:
                # Try to use a system font
                self._font_cache[size] = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size
                )
            except Exception:
                try:
                    # Fallback to default font
                    self._font_cache[size] = ImageFont.truetype(
                        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", size
                    )
                except Exception:
                    # Last resort: default PIL font
                    logger.warning(f"Could not load system font, using default for size {size}")
                    self._font_cache[size] = ImageFont.load_default()
        return self._font_cache[size]

    def _load_icon(self, transport_type: str) -> Image.Image | None:
        """Load route icon for transport type from SVG file.
        
        Converts SVG to PIL Image using cairosvg or falls back to text-based icon.
        
        Args:
            transport_type: Type of transport (U-Bahn, S-Bahn, Tram, Bus).
            
        Returns:
            PIL Image with icon, or None if not available.
        """
        if transport_type in self._icon_cache:
            return self._icon_cache[transport_type]

        # Try to load SVG icon from parent project
        icon_path = self.config.get_route_icon_path(transport_type)
        if icon_path and icon_path.exists():
            try:
                # Try using cairosvg to convert SVG to PNG
                try:
                    import cairosvg
                    
                    # Convert SVG to PNG bytes (RGBA format)
                    # Use a larger size for better quality, then resize
                    render_size = self.config.route_icon_size * 2
                    png_bytes = cairosvg.svg2png(
                        url=str(icon_path),
                        output_width=render_size,
                        output_height=render_size,
                    )
                    
                    # Load PNG bytes into PIL Image
                    icon = Image.open(BytesIO(png_bytes))
                    
                    # Convert to palette mode for e-ink display
                    if icon.mode == "RGBA":
                        # Create a white background
                        bg = Image.new("RGB", icon.size, (255, 255, 255))
                        bg.paste(icon, mask=icon.split()[3])  # Use alpha channel as mask
                        icon = bg
                    
                    if icon.mode != "P":
                        # Convert to grayscale first
                        icon = icon.convert("L")
                        
                        # The SVG icons have dark colored backgrounds with white symbols
                        # For e-ink, we want black symbols on white background
                        # Original: dark background (low values) + white symbols (high values)
                        # We want: white background + black symbols
                        # So: invert the image
                        
                        # Invert: white symbols (high) -> dark (low), dark backgrounds (low) -> bright (high)
                        icon = icon.point(lambda p: 255 - p)
                        
                        # Now we have: bright background + dark symbols
                        # Apply threshold to get clean black/white
                        # Dark pixels (symbols, < threshold) -> black, bright pixels (background, >= threshold) -> white
                        threshold = 140
                        icon = icon.point(lambda p: 0 if p < threshold else 255, mode="1")
                        
                        # Convert to palette mode
                        icon = icon.convert("P")
                        
                        # Map to e-ink palette if available
                        if hasattr(self.display, "palette"):
                            icon.putpalette(self.display.palette)
                    
                    # Resize to final size (always resize since we rendered at 2x)
                    icon = icon.resize(
                        (self.config.route_icon_size, self.config.route_icon_size),
                        Image.Resampling.LANCZOS,
                    )
                    
                    self._icon_cache[transport_type] = icon
                    return icon
                except ImportError:
                    logger.debug("cairosvg not available, trying alternative methods")
                    # Try using svglib as fallback
                    try:
                        from svglib.svglib import svg2rlg
                        from reportlab.graphics import renderPM
                        
                        drawing = svg2rlg(str(icon_path))
                        if drawing:
                            # Render to PIL Image
                            img_data = renderPM.drawToString(drawing, fmt="PNG")
                            icon = Image.open(BytesIO(img_data))
                            
                            # Convert to palette mode
                            if icon.mode != "P":
                                icon = icon.convert("L").convert("P", palette=Image.ADAPTIVE, colors=2)
                            if hasattr(self.display, "palette"):
                                icon.putpalette(self.display.palette)
                            
                            # Resize if needed
                            if icon.size != (self.config.route_icon_size, self.config.route_icon_size):
                                icon = icon.resize(
                                    (self.config.route_icon_size, self.config.route_icon_size),
                                    Image.Resampling.LANCZOS,
                                )
                            
                            self._icon_cache[transport_type] = icon
                            return icon
                    except ImportError:
                        logger.debug("svglib not available, using text-based fallback")
            except Exception as e:
                logger.warning(f"Could not load SVG icon for {transport_type} from {icon_path}: {e}")

        # Fallback: Create a simple text-based icon
        abbrev_map = {
            "U-Bahn": "U",
            "S-Bahn": "S",
            "Tram": "T",
            "Bus": "B",
        }
        abbrev = abbrev_map.get(transport_type, "?")

        try:
            icon = Image.new("P", (self.config.route_icon_size, self.config.route_icon_size), self._white)
            if hasattr(self.display, "palette"):
                icon.putpalette(self.display.palette)
            icon_draw = ImageDraw.Draw(icon)
            
            icon_font_size = max(12, self.config.route_icon_size // 2)
            icon_font = self._get_font(icon_font_size)
            
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

    def _calculate_font_size(self, total_items: int, header_count: int) -> int:
        """Calculate optimal font size to fit all content.
        
        Args:
            total_items: Total number of departure rows.
            header_count: Number of header rows.
            
        Returns:
            Optimal font size.
        """
        if total_items == 0:
            return self.config.max_font_size

        # Estimate header height (larger font)
        header_font_size = min(self.config.max_font_size + 4, 40)
        header_font = self._get_font(header_font_size)
        header_bbox = header_font.getbbox("Mg")
        header_height = header_bbox[3] - header_bbox[1] + self.config.line_spacing + 4

        # Try font sizes from max to min
        for font_size in range(
            self.config.max_font_size,
            self.config.min_font_size - 1,
            -self.config.font_size_step,
        ):
            font = self._get_font(font_size)
            bbox = font.getbbox("Mg")
            line_height = bbox[3] - bbox[1] + self.config.line_spacing

            total_height = (header_height * header_count) + (line_height * total_items)
            if total_height <= self.config.usable_height:
                return font_size

        return self.config.min_font_size

    def _truncate_text(
        self, text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: int
    ) -> str:
        """Truncate text to fit within max_width."""
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        if text_width <= max_width:
            return text

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

    def render(self, direction_groups: list[DirectionGroupWithMetadata]) -> Image.Image:
        """Render departures to PIL Image using same grouping as web version.
        
        Args:
            direction_groups: List of direction groups with metadata (same as web version).
            
        Returns:
            PIL Image ready to display.
        """
        # Use the same calculator as web version to get display data
        display_data = self.grouping_calculator.calculate_display_data(direction_groups)
        
        groups_with_departures = display_data.get("groups_with_departures", [])
        
        if not groups_with_departures:
            return self._render_no_departures()

        # Count total items for font sizing
        total_departures = sum(len(group.get("departures", [])) for group in groups_with_departures)
        header_count = len(groups_with_departures)
        
        # Calculate optimal font size
        font_size = self._calculate_font_size(total_departures, header_count)
        font = self._get_font(font_size)
        header_font_size = min(font_size + 4, 40)
        header_font = self._get_font(header_font_size)

        # Create image
        img = Image.new("P", (self.config.width, self.config.height), self._white)
        if hasattr(self.display, "palette"):
            img.putpalette(self.display.palette)
        draw = ImageDraw.Draw(img)

        # Calculate heights
        bbox = font.getbbox("Mg")
        line_height = bbox[3] - bbox[1] + self.config.line_spacing
        header_bbox = header_font.getbbox("Mg")
        header_height = header_bbox[3] - header_bbox[1] + self.config.line_spacing + 4

        # Calculate total height needed
        total_height = (header_height * header_count) + (line_height * total_departures)
        
        # Calculate starting Y position
        if self.config.fill_vertical_space:
            start_y = self.config.padding + (self.config.usable_height - total_height) // 2
        else:
            start_y = self.config.padding

        # Render each group with header
        y = start_y
        for group in groups_with_departures:
            header = group.get("header", "")
            departures = group.get("departures", [])
            header_color_hex = group.get("header_color")
            is_first_header = group.get("is_first_header", False)
            
            # Determine header background color
            # For e-ink, we want ALL headers to be colorful (not just non-first like web version)
            if header_color_hex:
                # Use the generated color from grouping calculator, mapped to e-ink color
                header_bg_color = _hex_to_inky_color(header_color_hex, self.display)
            else:
                # Generate a color for this header (even if it's the first one)
                # Check if random colors are enabled for this group
                random_colors = group.get("random_header_colors")
                if random_colors is None:
                    # Check calculator's default setting
                    random_colors = self.grouping_calculator.random_header_colors
                
                if random_colors:
                    # Generate color from header text
                    brightness = group.get("header_background_brightness")
                    if brightness is None:
                        brightness = self.grouping_calculator.header_background_brightness
                    salt = group.get("random_color_salt")
                    if salt is None:
                        salt = self.grouping_calculator.random_color_salt
                    
                    generated_hex = generate_pastel_color_from_text(header, brightness, 0, salt)
                    header_bg_color = _hex_to_inky_color(generated_hex, self.display)
                else:
                    # Use default blue-ish color (red on e-ink) for all headers
                    header_bg_color = _get_default_header_color(self.display)
            
            # White text on colored background
            header_text_color = self._white
            
            draw.rectangle(
                [0, y, self.config.width, y + header_height],
                fill=header_bg_color,
            )
            
            # Draw header text
            header_x = self.config.padding
            draw.text((header_x, y + 2), header, header_text_color, font=header_font)
            y += header_height

            # Render departures in this group
            for dep_data in departures:
                self._render_departure_row(draw, dep_data, font, y)
                y += line_height

        return img

    def _render_departure_row(
        self,
        draw: ImageDraw.ImageDraw,
        dep_data: dict[str, Any],
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        y: int,
    ) -> None:
        """Render a single departure row.
        
        Args:
            draw: PIL ImageDraw instance.
            dep_data: Formatted departure data (from DepartureGroupingCalculator).
            font: Font to use.
            y: Y position for this row.
        """
        x = self.config.padding

        # Draw route icon
        transport_type = dep_data.get("transport_type", "Bus")
        icon = self._load_icon(transport_type)
        if icon:
            img = draw._image  # type: ignore[attr-defined]
            img.paste(icon, (x, y))
        x += self.config.route_icon_size + self.config.padding

        # Draw route number
        route_text = dep_data.get("line", "")
        draw.text((x, y), route_text, self._black, font=font)
        x += self.config.route_number_width + self.config.padding

        # Calculate space needed for platform+time first
        platform_text = dep_data.get("platform", "") or ""
        
        if self.config.show_time:
            now = datetime.now(UTC)
            if (now - self._last_time_toggle).total_seconds() >= self.config.time_toggle_interval:
                self._use_relative_time = not self._use_relative_time
                self._last_time_toggle = now
            
            time_text = (
                dep_data.get("time_str_relative", "")
                if self._use_relative_time
                else dep_data.get("time_str_absolute", "")
            )
        else:
            time_text = ""
        
        # Calculate total width needed for platform+time
        time_width = 0
        platform_width = 0
        platform_font = None
        
        if time_text:
            time_bbox = font.getbbox(time_text)
            time_width = time_bbox[2] - time_bbox[0]
        
        if platform_text:
            # Use smaller font for platform (superscript)
            platform_font_size = max(int(font.size * 0.7), 10)
            platform_font = self._get_font(platform_font_size)
            platform_bbox = platform_font.getbbox(platform_text)
            platform_width = platform_bbox[2] - platform_bbox[0]
        
        # Calculate spacing: platform + gap + time
        platform_time_gap = 6  # Gap between platform and time
        total_platform_time_width = platform_width + (platform_time_gap if platform_text and time_text else 0) + time_width
        
        # Calculate available width for destination (ensuring no overlap)
        right_margin = self.config.padding + total_platform_time_width
        available_destination_width = self.config.width - x - right_margin
        
        # Draw destination (truncate if needed to avoid overlap)
        destination_text = dep_data.get("destination", "")
        if available_destination_width > 0:
            destination_text = self._truncate_text(destination_text, font, available_destination_width)
        else:
            destination_text = ""  # No space for destination
        
        if destination_text:
            draw.text((x, y), destination_text, self._black, font=font)

        # Draw platform and time together on the right
        # Platform appears as superscript before time (e.g., "1 20:19")
        right_x = self.config.width - self.config.padding
        
        if time_text:
            if platform_text and platform_font:
                # Draw platform as superscript (slightly above baseline)
                platform_y = y - int(font.size * 0.15)  # Slightly above
                platform_x = right_x - time_width - platform_time_gap - platform_width
                draw.text((platform_x, platform_y), platform_text, self._black, font=platform_font)
                
                # Draw time right-aligned
                time_x = right_x - time_width
                draw.text((time_x, y), time_text, self._black, font=font)
            else:
                # Just time, right-aligned
                time_x = right_x - time_width
                draw.text((time_x, y), time_text, self._black, font=font)
        elif platform_text:
            # Only platform, right-aligned
            if platform_font:
                platform_x = right_x - platform_width
                draw.text((platform_x, y), platform_text, self._black, font=platform_font)
            else:
                platform_bbox = font.getbbox(platform_text)
                platform_width = platform_bbox[2] - platform_bbox[0]
                platform_x = right_x - platform_width
                draw.text((platform_x, y), platform_text, self._black, font=font)

    def _render_no_departures(self) -> Image.Image:
        """Render 'No departures' message."""
        img = Image.new("P", (self.config.width, self.config.height), self._white)
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
