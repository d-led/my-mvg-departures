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
        
        # Use actual display dimensions if available (inky.width, inky.height)
        # This ensures we use the real display size instead of hardcoded config values
        if hasattr(display, "width") and hasattr(display, "height"):
            self.config.width = display.width
            self.config.height = display.height
            logger.info(f"Using display dimensions from display object: {display.width}x{display.height}")
        
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
                    font_obj = ImageFont.truetype(HankenGroteskBold, size)
                    logger.info(f"Using HankenGroteskBold font at size {size}")
                    self._font_cache[cache_key] = font_obj
                else:
                    from font_hanken_grotesk import HankenGroteskMedium
                    font_obj = ImageFont.truetype(HankenGroteskMedium, size)
                    logger.info(f"Using HankenGroteskMedium font at size {size}")
                    self._font_cache[cache_key] = font_obj
            except ImportError as e:
                logger.debug(f"font-hanken-grotesk not available: {e}, trying Fredoka One")
                try:
                    from font_fredoka_one import FredokaOne
                    font_obj = ImageFont.truetype(FredokaOne, size)
                    logger.info(f"Using FredokaOne font at size {size}")
                    self._font_cache[cache_key] = font_obj
                except ImportError as e2:
                    logger.debug(f"font-fredoka-one not available: {e2}, trying system fonts")
                    # Fall back to system fonts
                    try:
                        if bold:
                            # Try DejaVu Sans Bold
                            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                            font_obj = ImageFont.truetype(font_path, size)
                            logger.info(f"Using DejaVu Sans Bold system font at size {size}")
                            self._font_cache[cache_key] = font_obj
                        else:
                            # Try DejaVu Sans (common on Linux)
                            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                            font_obj = ImageFont.truetype(font_path, size)
                            logger.info(f"Using DejaVu Sans system font at size {size}")
                            self._font_cache[cache_key] = font_obj
                    except Exception as e3:
                        logger.debug(f"DejaVu fonts not available: {e3}, trying Liberation")
                        try:
                            if bold:
                                # Try Liberation Sans Bold
                                font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
                                font_obj = ImageFont.truetype(font_path, size)
                                logger.info(f"Using Liberation Sans Bold system font at size {size}")
                                self._font_cache[cache_key] = font_obj
                            else:
                                # Try Liberation Sans
                                font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
                                font_obj = ImageFont.truetype(font_path, size)
                                logger.info(f"Using Liberation Sans system font at size {size}")
                                self._font_cache[cache_key] = font_obj
                        except Exception as e4:
                            # Last resort: default PIL font
                            logger.warning(f"Could not load any font, using default PIL font for size {size}, bold={bold}. Errors: {e}, {e2}, {e3}, {e4}")
                            self._font_cache[cache_key] = ImageFont.load_default()
            except Exception as e:
                # If font package import succeeded but truetype failed, try fallbacks
                logger.warning(f"Font package available but truetype failed: {e}, trying fallbacks")
                try:
                    font_path = (
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
                        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                    )
                    font_obj = ImageFont.truetype(font_path, size)
                    logger.info(f"Using fallback DejaVu font at size {size}")
                    self._font_cache[cache_key] = font_obj
                except Exception:
                    try:
                        font_path = (
                            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
                            else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
                        )
                        font_obj = ImageFont.truetype(font_path, size)
                        logger.info(f"Using fallback Liberation font at size {size}")
                        self._font_cache[cache_key] = font_obj
                    except Exception:
                        logger.warning(f"Could not load any font, using default PIL font for size {size}, bold={bold}")
                        self._font_cache[cache_key] = ImageFont.load_default()
        return self._font_cache[cache_key]

    def _load_icon(self, transport_type: str, icon_size: int | None = None) -> Image.Image | None:
        """Load route icon for transport type from SVG file.
        
        Converts SVG to PIL Image using cairosvg or falls back to text-based icon.
        
        Args:
            transport_type: Type of transport (U-Bahn, S-Bahn, Tram, Bus).
            icon_size: Size for the icon (if None, uses config.route_icon_size).
            
        Returns:
            PIL Image with icon, or None if not available.
        """
        # Use provided icon_size or fall back to config
        target_size = icon_size if icon_size is not None else self.config.route_icon_size
        
        # Cache key includes size to support dynamic sizing
        cache_key = (transport_type, target_size)
        if cache_key in self._icon_cache:
            cached_icon = self._icon_cache[cache_key]
            if cached_icon is not None:
                return cached_icon
            # If cached as None, don't retry (to avoid repeated failures)
            logger.debug(f"Icon for {transport_type} was previously cached as None, skipping")
            return None

        # Try to load SVG icon from parent project
        icon_path = self.config.get_route_icon_path(transport_type)
        if not icon_path:
            logger.error(f"No icon path configured for transport type: {transport_type}")
            # Don't return None - let it fall through to create text icon as last resort
        elif not icon_path.exists():
            logger.error(f"Icon file not found at: {icon_path} (absolute: {icon_path.resolve()})")
            # Don't return None - let it fall through to create text icon as last resort
        else:
            logger.info(f"Loading SVG icon for {transport_type} from: {icon_path} (exists: {icon_path.exists()})")
            try:
                # Try using cairosvg to convert SVG to PNG
                try:
                    import cairosvg
                    
                    # Convert SVG to PNG bytes (RGBA format)
                    # Use a larger size for better quality, then resize
                    render_size = target_size * 2
                    png_bytes = cairosvg.svg2png(
                        url=str(icon_path),
                        output_width=render_size,
                        output_height=render_size,
                    )
                    
                    # Load PNG bytes into PIL Image
                    icon = Image.open(BytesIO(png_bytes))
                    
                    # Convert to RGB first (handle RGBA if needed)
                    if icon.mode == "RGBA":
                        # Create a white background and composite the icon on it
                        bg = Image.new("RGB", icon.size, (255, 255, 255))
                        bg.paste(icon, mask=icon.split()[3])  # Use alpha channel as mask
                        icon = bg
                    elif icon.mode != "RGB":
                        icon = icon.convert("RGB")
                    
                    # The SVG icons have colored backgrounds (blue #005d79, green #009551, red #dd0b2f) with white symbols (#fff)
                    # For e-ink, we want black symbols on white background
                    # Strategy: Extract white pixels (symbols) and make them black, everything else white
                    
                    # Create a new grayscale image for the result
                    result = Image.new("L", icon.size, 255)  # Start with white background
                    pixels = icon.load()
                    result_pixels = result.load()
                    
                    # Extract white symbols: pixels that are close to white (high RGB values)
                    # White symbols are #fff = (255, 255, 255)
                    # Use a threshold: if all RGB values are > 240, it's a white symbol (very strict)
                    black_pixels = 0
                    white_pixels = 0
                    for y_pos in range(icon.height):
                        for x_pos in range(icon.width):
                            r, g, b = pixels[x_pos, y_pos]
                            # Check if pixel is white (symbol) - all channels very high
                            # The SVG icons have white symbols (#fff = 255,255,255) on colored backgrounds
                            # Use strict threshold to catch pure white
                            if r >= 240 and g >= 240 and b >= 240:
                                # White symbol -> make it black
                                result_pixels[x_pos, y_pos] = 0
                                black_pixels += 1
                            else:
                                # Colored background -> keep it white
                                result_pixels[x_pos, y_pos] = 255
                                white_pixels += 1
                    
                    logger.info(f"Extracted {black_pixels} black pixels (symbols) and {white_pixels} white pixels (background) from {transport_type} icon")
                    
                    # Verify we actually extracted something
                    if black_pixels == 0:
                        logger.error(f"ERROR: No white symbols found in {transport_type} icon - icon will be invisible! Total pixels: {icon.width * icon.height}")
                        # Try a lower threshold as fallback
                        logger.info(f"Trying lower threshold (200) as fallback...")
                        for y_pos in range(icon.height):
                            for x_pos in range(icon.width):
                                r, g, b = pixels[x_pos, y_pos]
                                if r >= 200 and g >= 200 and b >= 200:
                                    result_pixels[x_pos, y_pos] = 0
                                    black_pixels += 1
                                else:
                                    result_pixels[x_pos, y_pos] = 255
                                    white_pixels += 1
                        logger.info(f"After fallback: {black_pixels} black pixels, {white_pixels} white pixels")
                    
                    icon = result
                    
                    # Convert to palette mode directly (don't use "1" mode as it can cause issues)
                    # Create a 2-color palette image: 0=black, 1=white
                    icon_p = Image.new("P", icon.size)
                    icon_p_pixels = icon_p.load()
                    
                    # Map grayscale values to palette indices
                    # 0 (black) -> palette index 0 (black)
                    # 255 (white) -> palette index 1 (white)
                    for y_pos in range(icon.height):
                        for x_pos in range(icon.width):
                            gray_value = result_pixels[x_pos, y_pos]
                            # 0 = black, 255 = white
                            icon_p_pixels[x_pos, y_pos] = 0 if gray_value == 0 else 1
                    
                    icon = icon_p
                    
                    # Set palette: black=0, white=1
                    icon_palette = [0, 0, 0]  # Index 0: Black
                    icon_palette.extend([255, 255, 255])  # Index 1: White
                    # Fill remaining slots with white
                    while len(icon_palette) < 768:
                        icon_palette.extend([255, 255, 255])
                    icon.putpalette(icon_palette)
                    
                    logger.debug(f"Converted icon to palette mode: size={icon.size}, mode={icon.mode}, palette indices used: {set(icon_p_pixels[x, y] for x in range(min(icon.width, 10)) for y in range(min(icon.height, 10)))}")
                    
                    # Resize to final size (always resize since we rendered at 2x)
                    # Use high-quality resampling for better icon rendering
                    icon = icon.resize(
                        (target_size, target_size),
                        Image.Resampling.LANCZOS,
                    )
                    
                    logger.info(f"Successfully loaded and converted SVG icon for {transport_type} at size {target_size}")
                    self._icon_cache[cache_key] = icon
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
                            
                            # Resize to target size
                            if icon.size != (target_size, target_size):
                                icon = icon.resize(
                                    (target_size, target_size),
                                    Image.Resampling.LANCZOS,
                                )
                            
                            self._icon_cache[cache_key] = icon
                            return icon
                    except ImportError:
                        logger.debug("svglib not available, using text-based fallback")
            except Exception as e:
                logger.error(f"Could not load SVG icon for {transport_type} from {icon_path}: {e}", exc_info=True)
                # Don't fall through to text icon - return None so we can debug
                return None

        # Fallback: Create a simple text-based icon
        abbrev_map = {
            "U-Bahn": "U",
            "S-Bahn": "S",
            "Tram": "T",
            "Bus": "B",
        }
        abbrev = abbrev_map.get(transport_type, "?")

        try:
            icon = Image.new("P", (target_size, target_size), self._white)
            if hasattr(self.display, "palette"):
                icon.putpalette(self.display.palette)
            icon_draw = ImageDraw.Draw(icon)
            
            icon_font_size = max(12, target_size // 2)
            icon_font = self._get_font(icon_font_size, bold=False)
            
            bbox = icon_font.getbbox(abbrev)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (target_size - text_width) // 2
            y = (target_size - text_height) // 2
            
            icon_draw.text((x, y), abbrev, self._black, font=icon_font)
            
            self._icon_cache[cache_key] = icon
            return icon
        except Exception as e:
            logger.warning(f"Could not create icon for {transport_type}: {e}")
            self._icon_cache[transport_type] = None
            return None

    def _calculate_font_size(self, total_items: int, header_count: int) -> int:
        """Calculate optimal font size to fit all content and maximize when filling space.
        
        When fill_vertical_space is enabled, finds the font size that makes total_height
        equal to available_height (or as close as possible).
        
        Args:
            total_items: Total number of departure rows (actual count from data).
            header_count: Number of header rows (actual count from data).
            
        Returns:
            Optimal font size.
        """
        if total_items == 0:
            return self.config.max_font_size

        # When filling space, use full height (no padding since we start at y=0)
        # When not filling, use usable height (with padding)
        available_height = self.config.height if self.config.fill_vertical_space else self.config.usable_height
        
        if self.config.fill_vertical_space:
            # Binary search for font size that makes total_height = available_height
            # We want to find the largest font size where total_height <= available_height
            low_font = self.config.min_font_size
            high_font = self.config.max_font_size
            best_font = self.config.min_font_size
            
            # Try all font sizes from max to min to find the largest that fits
            # This is more reliable than binary search for font sizing
            for font_size in range(
                self.config.max_font_size,
                self.config.min_font_size - 1,
                -self.config.font_size_step,
            ):
                font = self._get_font(font_size, bold=False)
                bbox = font.getbbox("Mg")
                font_height = bbox[3] - bbox[1]  # Font height without spacing
                line_height = font_height + self.config.line_spacing  # Full line height with spacing
                
                # Calculate header height with corresponding header font size
                header_font_size = min(font_size + 4, 40)
                header_font = self._get_font(header_font_size, bold=True)
                header_bbox = header_font.getbbox("Mg")
                header_font_height = header_bbox[3] - header_bbox[1]
                header_height = header_font_height + self.config.line_spacing + 4  # Header height with spacing

                # Calculate total height:
                # Each row takes line_height (font_height + spacing)
                # If we have N rows, we have N-1 gaps between them
                # But line_height already includes spacing for each row, so we're counting N spacings
                # The last row doesn't need spacing after it, so subtract one spacing
                total_height = (header_height * header_count) + (line_height * total_items) - self.config.line_spacing
                
                if total_height <= available_height:
                    # This font size fits, use it (it's the largest we've tried so far)
                    logger.debug(f"Font size {font_size} fits: total_height={total_height} <= available_height={available_height}")
                    return font_size
            
            # If no font size fits, return minimum (but log a warning)
            logger.warning(f"No font size fits! Min font size {self.config.min_font_size} will be used. Available height: {available_height}, total_items: {total_items}, header_count: {header_count}")
            return self.config.min_font_size
        else:
            # When not filling, just find largest that fits
            for font_size in range(
                self.config.max_font_size,
                self.config.min_font_size - 1,
                -self.config.font_size_step,
            ):
                font = self._get_font(font_size, bold=False)
                bbox = font.getbbox("Mg")
                font_height = bbox[3] - bbox[1]  # Font height without spacing
                line_height = font_height + self.config.line_spacing  # Full line height with spacing
                
                # Calculate header height with corresponding header font size
                header_font_size = min(font_size + 4, 40)
                header_font = self._get_font(header_font_size, bold=True)
                header_bbox = header_font.getbbox("Mg")
                header_font_height = header_bbox[3] - header_bbox[1]
                header_height = header_font_height + self.config.line_spacing + 4  # Header height with spacing

                # Calculate total height:
                # Each row takes line_height, but the last row doesn't need spacing after it
                # So subtract one spacing from total
                total_height = (header_height * header_count) + (line_height * total_items) - self.config.line_spacing
                
                if total_height <= available_height:
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
        
        NOTE: This method recalculates the entire layout on each call based on the
        actual number of departures and headers. This ensures optimal font sizing
        and vertical space usage when the data changes (e.g., on each API poll).
        
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

        # Count actual departures and headers from current data (not from config)
        # This ensures layout adapts to the actual number of items on each API update
        total_departures = sum(len(group.get("departures", [])) for group in groups_with_departures)
        header_count = len(groups_with_departures)
        
        # Calculate optimal font size based on actual counts
        # When fill_vertical_space is enabled, this will maximize font size to fill available height
        font_size = self._calculate_font_size(total_departures, header_count)
        font = self._get_font(font_size, bold=False)
        header_font_size = min(font_size + 4, 40)
        header_font = self._get_font(header_font_size, bold=True)
        platform_font_size = max(int(font_size * 0.7), 10)
        self._platform_font = self._get_font(platform_font_size, bold=False)
        
        # Calculate line height first (needed for icon size)
        font_bbox = font.getbbox("Mg")
        line_height = font_bbox[3] - font_bbox[1] + self.config.line_spacing
        
        # Icon size MUST be exactly the row height (line height)
        # This ensures icons fill the vertical space of each row
        calculated_icon_size = line_height
        
        # Update config with calculated icon size (for this render)
        self._calculated_icon_size = calculated_icon_size
        logger.info(f"Calculated icon size: {calculated_icon_size} (line height: {line_height})")
        
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

        # Calculate heights (must match the calculation in _calculate_font_size)
        bbox = font.getbbox("Mg")
        font_height = bbox[3] - bbox[1]  # Font height without spacing
        line_height = font_height + self.config.line_spacing  # Full line height with spacing
        header_bbox = header_font.getbbox("Mg")
        header_font_height = header_bbox[3] - header_bbox[1]
        header_height = header_font_height + self.config.line_spacing + 4  # Header height with spacing

        # Calculate total height needed
        # Each row takes line_height, but the last row doesn't need spacing after it
        # So subtract one spacing from total
        total_height = (header_height * header_count) + (line_height * total_departures) - self.config.line_spacing
        
        # Verify we're using full height when filling space
        available_height = self.config.height if self.config.fill_vertical_space else self.config.usable_height
        logger.info(f"Rendering: Total height needed: {total_height}, Available height: {available_height}, Fill vertical space: {self.config.fill_vertical_space}, Font size: {font_size}, Line height: {line_height}")
        
        # If we're not filling the space and there's wasted space, increase font size
        if self.config.fill_vertical_space and total_height < available_height:
            # The binary search should have found the optimal font size, but if there's still space,
            # it might be due to rounding in font_size_step. Try to find a better fit.
            # Calculate how much we can increase font size
            height_diff = available_height - total_height
            if height_diff > 5:  # Only warn if significant space is wasted
                logger.warning(f"Content height ({total_height}) is {height_diff}px less than available height ({available_height}). Font size: {font_size}, total_departures: {total_departures}, header_count: {header_count}")
        
        # Calculate starting Y position
        # First header should start at the very top (y=0), not at padding
        start_y = 0

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
            
            # First header starts at y=0, subsequent headers have spacing
            draw.rectangle(
                [0, y, self.config.width, y + header_height],
                fill=header_bg_color,
            )
            
            # Draw header text (with padding from left edge)
            header_x = self.config.padding
            # Center text vertically in header
            # Get actual text bounding box for proper centering
            text_bbox = header_font.getbbox(header)
            text_height = text_bbox[3] - text_bbox[1]
            # Center vertically: header_y + (header_height - text_height) / 2
            # Adjust for text baseline (text_bbox[1] is negative for ascent)
            header_text_y = y + (header_height - text_height) // 2 - text_bbox[1]
            draw.text((header_x, header_text_y), header, header_text_color, font=header_font)
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

        # Draw route icon (use dynamically calculated size)
        transport_type = dep_data.get("transport_type", "Bus")
        icon_size = getattr(self, "_calculated_icon_size", self.config.route_icon_size)
        icon = self._load_icon(transport_type, icon_size=icon_size)
        if icon:
            img = draw._image  # type: ignore[attr-defined]
            # Ensure icon has the same palette as the main image
            if icon.mode == "P":
                # Get the main image's palette
                main_palette = img.getpalette()
                if main_palette:
                    icon.putpalette(main_palette)
                elif hasattr(self.display, "palette"):
                    icon.putpalette(self.display.palette)
                else:
                    # Fallback: use a default palette
                    default_palette = [0, 0, 0, 255, 255, 255] + [255, 255, 255] * 254
                    icon.putpalette(default_palette)
            
            # Calculate icon position - icon should fill the entire row height
            # Since icon_size = line_height, it should start at y (text baseline)
            # But we need to align with the text baseline, so adjust for font ascent
            font_bbox = font.getbbox("Mg")
            text_ascent = -font_bbox[1]  # Negative y1 is the ascent
            # Align icon top with text baseline minus ascent (so icon aligns with text)
            icon_y = y - text_ascent
            
            # Paste icon onto main image
            # For palette mode, ensure icon uses main image's palette before pasting
            if icon.mode == "P":
                # Get main image palette
                main_palette = img.getpalette()
                if main_palette:
                    # Icon has: 0=black, 1=white
                    # Main image has: 0=black, 1=white, 2=green, 3=blue, etc.
                    # So indices match - just set the palette to main image's palette
                    icon.putpalette(main_palette)
                # Paste directly (palette indices should match now)
                img.paste(icon, (x, icon_y))
            elif icon.mode == "RGBA":
                # Create a temporary image with alpha channel
                img.paste(icon, (x, icon_y), icon)
            else:
                # For other modes, paste directly
                img.paste(icon, (x, icon_y))
            
            # Debug: Check if icon has any black pixels (index 0) BEFORE pasting
            if icon.mode == "P":
                icon_pixels = icon.load()
                black_count = 0
                white_count = 0
                total_pixels = icon.width * icon.height
                for py in range(icon.height):
                    for px in range(icon.width):
                        idx = icon_pixels[px, py]
                        if idx == 0:  # Black
                            black_count += 1
                        elif idx == 1:  # White
                            white_count += 1
                logger.info(f"Icon for {transport_type}: {black_count}/{total_pixels} black pixels (index 0), {white_count}/{total_pixels} white pixels (index 1)")
                
                if black_count == 0:
                    logger.error(f"WARNING: Icon for {transport_type} has NO black pixels! Icon will be invisible!")
            
            logger.info(f"Pasting icon for {transport_type} at ({x}, {icon_y}), size={icon_size}, mode={icon.mode}")
        else:
            logger.warning(f"No icon loaded for transport type: {transport_type}")
        
        # Add proper spacing after icon (icon size + spacing between icon and route number)
        x += icon_size + self.config.route_icon_spacing

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
