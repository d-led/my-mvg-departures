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
    """Convert hex color to Inky Impression Spectra color.
    
    Maps RGB hex colors to the closest e-ink color.
    Inky Impression Spectra supports 7 colors: black, white, green, blue, red, yellow, orange.
    
    Args:
        hex_color: Hex color code (e.g., "#A8D5E2").
        display: Inky display instance.
        
    Returns:
        Inky color constant (BLACK=0, WHITE=1, GREEN=2, BLUE=3, RED=4, YELLOW=5, ORANGE=6).
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
    
    # Map hue to closest color (Spectra supports 7 colors)
    # Red: 0-30, 330-360 degrees -> RED (4)
    # Yellow: 30-90 degrees -> YELLOW (5)
    # Green: 90-150 degrees -> GREEN (2)
    # Blue: 150-270 degrees -> BLUE (3)
    # Orange: 15-30 degrees (overlap with red) -> ORANGE (6)
    if 15 <= hue_deg < 30:
        return getattr(display, "ORANGE", 6)
    elif 30 <= hue_deg < 90:
        return getattr(display, "YELLOW", 5)
    elif 90 <= hue_deg < 150:
        return getattr(display, "GREEN", 2)
    elif 150 <= hue_deg < 270:
        return getattr(display, "BLUE", 3)
    else:
        return getattr(display, "RED", 4)


def _get_default_header_color(display: Any) -> int:
    """Get default header color for e-ink display.
    
    Uses blue for headers (as requested).
    
    Args:
        display: Inky display instance.
        
    Returns:
        Inky color constant for headers (BLUE=3).
    """
    return getattr(display, "BLUE", 3)


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
        
        # Store display colors (Inky Impression Spectra supports 7 colors)
        # Order: black, white, green, blue, red, yellow, orange
        self._black = getattr(display, "BLACK", 0)
        self._white = getattr(display, "WHITE", 1)
        self._green = getattr(display, "GREEN", 2)
        self._blue = getattr(display, "BLUE", 3)
        self._red = getattr(display, "RED", 4)
        self._yellow = getattr(display, "YELLOW", 5)
        self._orange = getattr(display, "ORANGE", 6)

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Get font at specified size, with caching.
        
        Tries Pimoroni font packages first (like in their examples), then falls back
        to system fonts. Uses bold variant if requested and available.
        
        Args:
            size: Font size in points.
            bold: Whether to use bold variant (for headers).
            
        Returns:
            PIL ImageFont instance.
        """
        cache_key = (size, bold)
        if cache_key not in self._font_cache:
            # Try Pimoroni font packages first (like in their examples)
            try:
                if bold:
                    from font_hanken_grotesk import HankenGroteskBold
                    self._font_cache[cache_key] = ImageFont.truetype(HankenGroteskBold, size)
                    logger.debug(f"Using HankenGroteskBold font at size {size}")
                else:
                    from font_hanken_grotesk import HankenGroteskMedium
                    self._font_cache[cache_key] = ImageFont.truetype(HankenGroteskMedium, size)
                    logger.debug(f"Using HankenGroteskMedium font at size {size}")
            except ImportError:
                try:
                    from font_fredoka_one import FredokaOne
                    self._font_cache[cache_key] = ImageFont.truetype(FredokaOne, size)
                    logger.debug(f"Using FredokaOne font at size {size}")
                except ImportError:
                    # Fall back to system fonts
                    try:
                        if bold:
                            # Try DejaVu Sans Bold
                            self._font_cache[cache_key] = ImageFont.truetype(
                                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size
                            )
                            logger.debug(f"Using DejaVu Sans Bold system font at size {size}")
                        else:
                            # Try DejaVu Sans (common on Linux)
                            self._font_cache[cache_key] = ImageFont.truetype(
                                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size
                            )
                            logger.debug(f"Using DejaVu Sans system font at size {size}")
                    except Exception:
                        try:
                            if bold:
                                # Try Liberation Sans Bold
                                self._font_cache[cache_key] = ImageFont.truetype(
                                    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", size
                                )
                                logger.debug(f"Using Liberation Sans Bold system font at size {size}")
                            else:
                                # Try Liberation Sans
                                self._font_cache[cache_key] = ImageFont.truetype(
                                    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", size
                                )
                                logger.debug(f"Using Liberation Sans system font at size {size}")
                        except Exception:
                            # Last resort: default PIL font
                            logger.warning(f"Could not load any font, using default PIL font for size {size}")
                            self._font_cache[cache_key] = ImageFont.load_default()
            except Exception as e:
                # If font package import succeeded but truetype failed, try fallbacks
                logger.debug(f"Font package available but truetype failed: {e}, trying fallbacks")
                try:
                    font_path = (
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
                        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                    )
                    self._font_cache[cache_key] = ImageFont.truetype(font_path, size)
                except Exception:
                    try:
                        font_path = (
                            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
                            else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
                        )
                        self._font_cache[cache_key] = ImageFont.truetype(font_path, size)
                    except Exception:
                        logger.warning(f"Could not load any font, using default PIL font for size {size}")
                        self._font_cache[cache_key] = ImageFont.load_default()
        return self._font_cache[cache_key]

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
        if icon_path:
            logger.debug(f"Looking for icon at: {icon_path}")
        if icon_path and icon_path.exists():
            logger.debug(f"Found icon at: {icon_path}")
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
            icon_font = self._get_font(icon_font_size, bold=False)
            
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
        """Calculate optimal font size to fit all content and maximize when filling space.
        
        When fill_vertical_space is enabled, finds the largest font size that fits
        to maximize use of available vertical space.
        
        Args:
            total_items: Total number of departure rows.
            header_count: Number of header rows.
            
        Returns:
            Optimal font size.
        """
        if total_items == 0:
            return self.config.max_font_size

        # Try font sizes from max to min to find largest that fits
        for font_size in range(
            self.config.max_font_size,
            self.config.min_font_size - 1,
            -self.config.font_size_step,
        ):
            font = self._get_font(font_size, bold=False)
            bbox = font.getbbox("Mg")
            line_height = bbox[3] - bbox[1] + self.config.line_spacing
            
            # Calculate header height with corresponding header font size
            header_font_size = min(font_size + 4, 40)
            header_font = self._get_font(header_font_size, bold=True)
            header_bbox = header_font.getbbox("Mg")
            header_height = header_bbox[3] - header_bbox[1] + self.config.line_spacing + 4

            total_height = (header_height * header_count) + (line_height * total_items)
            
            # When filling space, use largest font that fits (maximize)
            # When not filling, just need to fit
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
        
        # Calculate optimal font size first
        font_size = self._calculate_font_size(total_departures, header_count)
        font = self._get_font(font_size, bold=False)
        header_font_size = min(font_size + 4, 40)
        header_font = self._get_font(header_font_size, bold=True)
        platform_font_size = max(int(font_size * 0.7), 10)
        self._platform_font = self._get_font(platform_font_size, bold=False)
        
        # Pre-calculate maximum platform and time widths for vertical alignment (like web version)
        # Use actual font sizes to measure
        max_platform_width = 0
        max_time_width = 0
        
        # Measure all platforms and times to find maximum widths
        for group in groups_with_departures:
            for dep_data in group.get("departures", []):
                platform_text = dep_data.get("platform", "") or ""
                if platform_text:
                    platform_bbox = self._platform_font.getbbox(platform_text)
                    platform_width = platform_bbox[2] - platform_bbox[0]
                    max_platform_width = max(max_platform_width, platform_width)
                
                # Measure both relative and absolute time formats
                time_str_relative = dep_data.get("time_str_relative", "")
                time_str_absolute = dep_data.get("time_str_absolute", "")
                if time_str_relative:
                    time_bbox = font.getbbox(time_str_relative)
                    max_time_width = max(max_time_width, time_bbox[2] - time_bbox[0])
                if time_str_absolute:
                    time_bbox = font.getbbox(time_str_absolute)
                    max_time_width = max(max_time_width, time_bbox[2] - time_bbox[0])
        
        # Add padding for visual breathing room (like web version: fontSizes.platform * 0.3)
        platform_padding = int(platform_font_size * 0.3) if max_platform_width > 0 else 0
        time_padding = int(font_size * 0.3)
        self._platform_column_width = max_platform_width + platform_padding if max_platform_width > 0 else 0
        self._time_column_width = max_time_width + time_padding
        self._platform_time_gap = 6  # Gap between platform and time

        # Create image with proper color palette support
        img = Image.new("P", (self.config.width, self.config.height), self._white)
        if hasattr(self.display, "palette"):
            img.putpalette(self.display.palette)
        else:
            # Create a basic color palette for mock mode (white, black, red, yellow)
            palette = []
            # Order: black, white, green, blue, red, yellow, orange
            # Using web version colors for blue and green (less saturated)
            # Black (index 0)
            palette.extend([0, 0, 0])
            # White (index 1)
            palette.extend([255, 255, 255])
            # Green (index 2) - for realtime times (#047857 - darker green from web version)
            palette.extend([4, 120, 87])
            # Blue (index 3) - for headers (#087BC4 - less saturated blue from web version)
            palette.extend([8, 123, 196])
            # Red (index 4)
            palette.extend([255, 0, 0])
            # Yellow (index 5)
            palette.extend([255, 255, 0])
            # Orange (index 6)
            palette.extend([255, 165, 0])
            # Fill remaining palette slots with white
            while len(palette) < 768:  # 256 colors * 3 RGB values
                palette.extend([255, 255, 255])
            img.putpalette(palette)
        draw = ImageDraw.Draw(img)

        # Calculate heights
        bbox = font.getbbox("Mg")
        line_height = bbox[3] - bbox[1] + self.config.line_spacing
        header_bbox = header_font.getbbox("Mg")
        header_height = header_bbox[3] - header_bbox[1] + self.config.line_spacing + 4

        # Calculate total height needed
        total_height = (header_height * header_count) + (line_height * total_departures)
        
        # Calculate starting Y position
        # Always start at top when filling vertical space (don't center, fill from top)
        start_y = self.config.padding

        # Render each group with header
        y = start_y
        for group in groups_with_departures:
            header = group.get("header", "")
            departures = group.get("departures", [])
            header_color_hex = group.get("header_color")
            is_first_header = group.get("is_first_header", False)
            
            # Determine header background color
            # Always use blue for headers (as requested)
            header_bg_color = self._blue
            
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
            # Ensure icon has the same palette as the main image
            if icon.mode == "P":
                if hasattr(self.display, "palette"):
                    icon.putpalette(self.display.palette)
                else:
                    # Use main image's palette
                    icon.putpalette(img.getpalette() or [255, 255, 255, 0, 0, 0] + [255, 255, 255] * 254)
            # Paste icon onto main image (ensure no overlap with route number)
            # Calculate icon position to align with text baseline
            icon_y = y
            img.paste(icon, (x, icon_y))
        # Add proper spacing after icon (icon size + spacing between icon and route number)
        x += self.config.route_icon_size + self.config.route_icon_spacing

        # Draw route number
        route_text = dep_data.get("line", "")
        draw.text((x, y), route_text, self._black, font=font)
        x += self.config.route_number_width + self.config.padding

        # Get platform and time text
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
        
        # Calculate total width needed for platform+time using pre-calculated column widths
        # Platform column width (fixed for all rows)
        effective_platform_width = self._platform_column_width if platform_text else 0
        # Time column width (fixed for all rows)
        effective_time_width = self._time_column_width if time_text else 0
        # Gap between platform and time (only if both exist)
        effective_gap = self._platform_time_gap if (platform_text and time_text) else 0
        
        total_platform_time_width = effective_platform_width + effective_gap + effective_time_width
        
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

        # Draw platform and time together on the right (vertically aligned like web version)
        # Platform appears as superscript before time (e.g., "1 20:19")
        right_x = self.config.width - self.config.padding
        
        if time_text:
            # Check if this is a realtime departure (green time in web version)
            # Use actual green color (Spectra supports green!)
            is_realtime = dep_data.get("is_realtime", False)
            time_color = self._green if is_realtime else self._black
            
            # Calculate actual time width for this specific time text
            time_bbox = font.getbbox(time_text)
            time_width = time_bbox[2] - time_bbox[0]
            
            if platform_text:
                # Calculate baseline alignment for platform and time
                time_ascent = -time_bbox[1]  # Negative y1 is the ascent
                
                platform_bbox = self._platform_font.getbbox(platform_text)
                platform_ascent = -platform_bbox[1]
                
                # Align baselines: platform should be on same baseline as time
                baseline_offset = time_ascent - platform_ascent
                
                # Platform position: fixed column width, left-aligned within column
                platform_x = right_x - effective_time_width - effective_gap - self._platform_column_width
                platform_y = y + baseline_offset
                draw.text((platform_x, platform_y), platform_text, self._black, font=self._platform_font)
                
                # Time position: right-aligned
                time_x = right_x - time_width
                draw.text((time_x, y), time_text, time_color, font=font)
            else:
                # Just time, right-aligned (green for realtime, black otherwise)
                time_x = right_x - time_width
                draw.text((time_x, y), time_text, time_color, font=font)
        elif platform_text:
            # Only platform, right-aligned in fixed column
            platform_x = right_x - self._platform_column_width
            draw.text((platform_x, y), platform_text, self._black, font=self._platform_font)

    def _render_no_departures(self) -> Image.Image:
        """Render 'No departures' message."""
        img = Image.new("P", (self.config.width, self.config.height), self._white)
        if hasattr(self.display, "palette"):
            img.putpalette(self.display.palette)
        draw = ImageDraw.Draw(img)

        font_size = 32
        font = self._get_font(font_size, bold=False)
        text = "No departures available"

        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (self.config.width - text_width) // 2
        y = (self.config.height - text_height) // 2

        draw.text((x, y), text, self._black, font=font)
        return img
