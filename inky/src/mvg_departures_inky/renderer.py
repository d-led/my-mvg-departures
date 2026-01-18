"""Renderer for Inky display."""

import logging
from datetime import UTC, datetime
from io import BytesIO
from typing import Any

import hitherdither
from mvg_departures.adapters.web.builders.departure_grouping_calculator import (
    DepartureGroupingCalculator,
)
from mvg_departures.domain.models.direction_group_with_metadata import (
    DirectionGroupWithMetadata,
)
from PIL import Image, ImageDraw, ImageFont

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
    if 30 <= hue_deg < 90:
        return getattr(display, "YELLOW", 5)
    if 90 <= hue_deg < 150:
        return getattr(display, "GREEN", 2)
    if 150 <= hue_deg < 270:
        return getattr(display, "BLUE", 3)
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
        self._font_cache: dict[tuple[int, bool], ImageFont.FreeTypeFont | ImageFont.ImageFont] = (
            {}
        )  # Cache key includes bold flag
        self._icon_cache: dict[tuple[str, int], Image.Image | None] = (
            {}
        )  # Cache key includes size (transport_type, target_size)
        self._use_relative_time = False  # Start with absolute time (HH:MM format)
        self._last_time_toggle = datetime.now(UTC)

        # Use actual display dimensions if available (inky.width, inky.height)
        # This ensures we use the real display size instead of hardcoded config values
        if hasattr(display, "width") and hasattr(display, "height"):
            self.config.width = display.width
            self.config.height = display.height
            logger.info(
                f"Using display dimensions from display object: {display.width}x{display.height}"
            )

        # Store display colors (Inky Impression Spectra supports 7 colors)
        # Order: black, white, green, blue, red, yellow, orange
        self._black = getattr(display, "BLACK", 0)
        self._white = getattr(display, "WHITE", 1)
        self._green = getattr(display, "GREEN", 2)
        self._blue = getattr(display, "BLUE", 3)
        self._red = getattr(display, "RED", 4)
        self._yellow = getattr(display, "YELLOW", 5)
        self._orange = getattr(display, "ORANGE", 6)

    def _get_font(
        self, size: int, bold: bool = False
    ) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Get font at specified size, with caching.

        Font priority:
        1. HK Grotesk (Bold for headers, Regular for body) - default
        2. Fredoka One (if configured as alternative)
        3. System fonts (DejaVu, Liberation)
        4. Default PIL font (last resort)

        Args:
            size: Font size in points.
            bold: Whether to use bold variant (for headers).

        Returns:
            PIL ImageFont instance.
        """
        cache_key = (size, bold)
        if cache_key not in self._font_cache:
            # Priority 1: Try HK Grotesk (default font family)
            if self.config.font_family == "hk_grotesk":
                hk_grotesk_path = self.config.get_hk_grotesk_font_path(bold=bold)
                if hk_grotesk_path and hk_grotesk_path.exists():
                    try:
                        font_obj = ImageFont.truetype(str(hk_grotesk_path), size)
                        logger.info(
                            f"Using HK Grotesk {'Bold' if bold else 'Regular'} font at size {size}"
                        )
                        self._font_cache[cache_key] = font_obj
                        return font_obj
                    except Exception as e:
                        logger.debug(f"Failed to load HK Grotesk font: {e}, trying alternatives")
                else:
                    logger.debug(
                        f"HK Grotesk {'Bold' if bold else 'Regular'} font not found at {hk_grotesk_path}, trying alternatives"
                    )

            # Priority 2: Try Fredoka One (if configured as alternative)
            if self.config.font_family == "fredoka_one":
                try:
                    from font_fredoka_one import FredokaOne

                    font_obj = ImageFont.truetype(FredokaOne, size)
                    logger.info(f"Using FredokaOne font at size {size}")
                    self._font_cache[cache_key] = font_obj
                    return font_obj
                except ImportError as e:
                    logger.debug(f"font-fredoka-one not available: {e}, trying system fonts")
                except Exception as e:
                    logger.debug(f"Failed to load FredokaOne font: {e}, trying system fonts")

            # Priority 3: Fall back to system fonts
            try:
                if bold:
                    # Try DejaVu Sans Bold
                    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                    font_obj = ImageFont.truetype(font_path, size)
                    logger.info(f"Using DejaVu Sans Bold system font at size {size}")
                    self._font_cache[cache_key] = font_obj
                    return font_obj
                else:
                    # Try DejaVu Sans (common on Linux)
                    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                    font_obj = ImageFont.truetype(font_path, size)
                    logger.info(f"Using DejaVu Sans system font at size {size}")
                    self._font_cache[cache_key] = font_obj
                    return font_obj
            except Exception as e3:
                logger.debug(f"DejaVu fonts not available: {e3}, trying Liberation")
                try:
                    if bold:
                        # Try Liberation Sans Bold
                        font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
                        font_obj = ImageFont.truetype(font_path, size)
                        logger.info(f"Using Liberation Sans Bold system font at size {size}")
                        self._font_cache[cache_key] = font_obj
                        return font_obj
                    else:
                        # Try Liberation Sans
                        font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
                        font_obj = ImageFont.truetype(font_path, size)
                        logger.info(f"Using Liberation Sans system font at size {size}")
                        self._font_cache[cache_key] = font_obj
                        return font_obj
                except Exception as e4:
                    # Last resort: default PIL font
                    logger.warning(
                        f"Could not load any font, using default PIL font for size {size}, bold={bold}. Errors: {e3}, {e4}"
                    )
                    self._font_cache[cache_key] = ImageFont.load_default()
                    return self._font_cache[cache_key]

        return self._font_cache[cache_key]

    def _convert_colored_icon_to_rgb_with_colors(
        self, icon: Image.Image, transport_type: str
    ) -> Image.Image | None:
        """Convert colored icon preserving colored background and fixing white/black inversion.

        The SVG icons have:
        - Colored backgrounds (blue #00508c/#005d79, green #009551, red #dd0b2f) - circles/squares
        - White symbols (#fff = 255,255,255) - should stay white
        - Black parts - should become white

        This function:
        1. Preserves the colored background (circle/square)
        2. Keeps white symbols white
        3. Converts black/dark parts to white

        Args:
            icon: PIL Image in RGB mode with colored background and white symbols.
            transport_type: Type of transport (for logging).

        Returns:
            PIL Image in RGB mode with colored background preserved, white symbols white, black->white.
        """
        # Create a new RGB image for the result
        result = Image.new("RGB", icon.size, (255, 255, 255))  # Start with white background
        pixels = icon.load()
        result_pixels = result.load()

        # Type check: pixels and result_pixels should not be None
        if pixels is None or result_pixels is None:
            logger.error(f"Failed to load pixels for {transport_type} icon")
            return None

        # Color thresholds
        WHITE_THRESHOLD = 240  # Pixels with all RGB >= 240 are considered white
        BLACK_THRESHOLD = 50  # Pixels with all RGB <= 50 are considered black

        white_pixels = 0
        colored_pixels = 0
        black_pixels = 0

        for y_pos in range(icon.height):
            for x_pos in range(icon.width):
                pixel_val = pixels[x_pos, y_pos]
                if isinstance(pixel_val, tuple) and len(pixel_val) >= 3:
                    r, g, b = pixel_val[0], pixel_val[1], pixel_val[2]
                else:
                    # Single value (shouldn't happen in RGB mode, but handle gracefully)
                    r, g, b = 255, 255, 255

                # Check if pixel is white (symbol) - keep it white
                if r >= WHITE_THRESHOLD and g >= WHITE_THRESHOLD and b >= WHITE_THRESHOLD:
                    result_pixels[x_pos, y_pos] = (255, 255, 255)  # White symbol -> white
                    white_pixels += 1
                # Check if pixel is black/dark - convert to white
                elif r <= BLACK_THRESHOLD and g <= BLACK_THRESHOLD and b <= BLACK_THRESHOLD:
                    result_pixels[x_pos, y_pos] = (255, 255, 255)  # Black -> white
                    black_pixels += 1
                else:
                    # Colored background (circle/square) - preserve the color
                    result_pixels[x_pos, y_pos] = (r, g, b)
                    colored_pixels += 1

        logger.info(
            f"Converted {transport_type} icon: {white_pixels} white pixels (symbols), "
            f"{colored_pixels} colored pixels (background), {black_pixels} black->white pixels"
        )

        # Verify we have some colored pixels (the background circle/square)
        if colored_pixels == 0:
            logger.warning(
                f"No colored background found in {transport_type} icon - may be invisible! "
                f"Total pixels: {icon.width * icon.height}"
            )

        return result

    def _dither_image_to_palette(self, rgb_image: Image.Image) -> Image.Image:
        """Dither RGB image to 7-color palette using hitherdither.

        This method converts an RGB image to the Inky Impression Spectra's 7-color palette
        using dithering for better color representation. Based on Pimoroni's dither.py example.

        Args:
            rgb_image: PIL Image in RGB mode.

        Returns:
            PIL Image in palette mode (P) with dithered colors.
        """
        # Get the display palette (7 colors)
        if hasattr(self.display, "_palette_blend"):
            # Use display's palette blend method if available (real hardware)
            saturation = 0.5  # Medium saturation for good color representation
            palette_rgb = self.display._palette_blend(saturation, dtype="uint24")
        elif hasattr(self.display, "palette"):
            # Use display's palette directly
            display_palette = self.display.palette
            # Convert palette to RGB tuples (first 7 colors)
            palette_rgb = []
            for i in range(7):
                idx = i * 3
                if idx + 2 < len(display_palette):
                    palette_rgb.append(
                        (display_palette[idx], display_palette[idx + 1], display_palette[idx + 2])
                    )
                else:
                    palette_rgb.append((255, 255, 255))  # Default to white
        else:
            # Fallback: use our standard 7-color palette
            palette_rgb = [
                (0, 0, 0),  # 0: Black
                (255, 255, 255),  # 1: White
                (4, 120, 87),  # 2: Green (#047857)
                (8, 123, 196),  # 3: Blue (#087BC4)
                (255, 0, 0),  # 4: Red
                (255, 255, 0),  # 5: Yellow
                (255, 165, 0),  # 6: Orange
            ]

        # Create hitherdither palette
        hither_palette = hitherdither.palette.Palette(palette_rgb)

        # Use Bayer dithering (fast and good quality, as per Pimoroni example)
        # Thresholds for snapping colors
        thresholds = [64, 64, 64]
        # Order 8 for good quality (higher = better but slower)
        dithered = hitherdither.ordered.bayer.bayer_dithering(
            rgb_image, hither_palette, thresholds, order=8
        )

        # Convert to palette mode
        return dithered.convert("P")

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
            self._icon_cache[cache_key] = None
            return None
        if not icon_path.exists():
            logger.error(f"Icon file not found at: {icon_path} (absolute: {icon_path.resolve()})")
            self._icon_cache[cache_key] = None
            return None
        logger.info(
            f"Loading SVG icon for {transport_type} from: {icon_path} (exists: {icon_path.exists()})"
        )
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

                # The SVG icons have:
                # - Colored backgrounds (blue #00508c/#005d79, green #009551, red #dd0b2f) - circles/squares
                # - White symbols (#fff = 255,255,255) - should stay white
                # - Black parts - should become white
                # We want to preserve the colored background and keep white symbols white

                # Convert icon preserving colors and fixing inversion
                icon_rgb = self._convert_colored_icon_to_rgb_with_colors(icon, transport_type)
                if icon_rgb is None:
                    self._icon_cache[cache_key] = None
                    return None

                # Keep icon in RGB mode - it will be pasted into the RGB image before dithering
                icon = icon_rgb

                # Resize to final size (always resize since we rendered at 2x)
                # Use high-quality resampling for better icon rendering
                icon = icon.resize(
                    (target_size, target_size),
                    Image.Resampling.LANCZOS,
                )

                logger.info(
                    f"Successfully loaded and converted SVG icon for {transport_type} at size {target_size}"
                )
                self._icon_cache[cache_key] = icon
                return icon
            except ImportError:
                logger.debug("cairosvg not available, trying alternative methods")
                # Try using svglib as fallback
                try:
                    from reportlab.graphics import renderPM
                    from svglib.svglib import svg2rlg

                    drawing = svg2rlg(str(icon_path))
                    if drawing:
                        # Render to PIL Image
                        img_data = renderPM.drawToString(drawing, fmt="PNG")
                        icon = Image.open(BytesIO(img_data))

                        # Convert to palette mode
                        if icon.mode != "P":
                            # Convert to grayscale first, then to palette with adaptive colors
                            icon_gray = icon.convert("L")
                            icon = icon_gray.quantize(colors=2, method=Image.Quantize.MEDIANCUT)
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
                    logger.debug("svglib not available, no SVG conversion library found")
                    # Both cairosvg and svglib are not available
                    logger.error(
                        f"Neither cairosvg nor svglib available for {transport_type} icon conversion"
                    )
                    self._icon_cache[cache_key] = None
                    return None
        except Exception as e:
            logger.error(
                f"Could not load SVG icon for {transport_type} from {icon_path}: {e}",
                exc_info=True,
            )
            # Cache the failure to avoid repeated attempts
            self._icon_cache[cache_key] = None
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
        available_height = (
            self.config.height if self.config.fill_vertical_space else self.config.usable_height
        )

        if self.config.fill_vertical_space:
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
                line_height = (
                    font_height + self.config.line_spacing
                )  # Full line height with spacing

                # Calculate header height with corresponding header font size
                # Make header only slightly larger than body text (10% larger, max +2)
                header_font_size = min(int(font_size * 1.1), font_size + 2)
                header_font = self._get_font(header_font_size, bold=True)
                header_bbox = header_font.getbbox("Mg")
                header_font_height = header_bbox[3] - header_bbox[1]
                header_height = (
                    header_font_height + self.config.line_spacing + 4
                )  # Header height with spacing

                # Calculate total height:
                # Each row takes line_height (font_height + spacing)
                # If we have N rows, we have N-1 gaps between them
                # But line_height already includes spacing for each row, so we're counting N spacings
                # The last row doesn't need spacing after it, so subtract one spacing
                total_height = (
                    (header_height * header_count)
                    + (line_height * total_items)
                    - self.config.line_spacing
                )

                if total_height <= available_height:
                    # This font size fits, use it (it's the largest we've tried so far)
                    logger.debug(
                        f"Font size {font_size} fits: total_height={total_height} <= available_height={available_height}"
                    )
                    return font_size

            # If no font size fits, return minimum (but log a warning)
            logger.warning(
                f"No font size fits! Min font size {self.config.min_font_size} will be used. Available height: {available_height}, total_items: {total_items}, header_count: {header_count}"
            )
            return self.config.min_font_size

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
            # Make header only slightly larger than body text (10% larger, max +2)
            header_font_size = min(int(font_size * 1.1), font_size + 2)
            header_font = self._get_font(header_font_size, bold=True)
            header_bbox = header_font.getbbox("Mg")
            header_font_height = header_bbox[3] - header_bbox[1]
            header_height = (
                header_font_height + self.config.line_spacing + 4
            )  # Header height with spacing

            # Calculate total height:
            # Each row takes line_height, but the last row doesn't need spacing after it
            # So subtract one spacing from total
            total_height = (
                (header_height * header_count)
                + (line_height * total_items)
                - self.config.line_spacing
            )

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
        # Make header only slightly larger than body text (10% larger, max +2)
        header_font_size = min(int(font_size * 1.1), font_size + 2)
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
        self._calculated_icon_size = int(calculated_icon_size)
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
                    max_platform_width = max(max_platform_width, int(platform_width))

                # Measure both relative and absolute time formats
                time_str_relative = dep_data.get("time_str_relative", "")
                time_str_absolute = dep_data.get("time_str_absolute", "")
                if time_str_relative:
                    time_bbox = font.getbbox(time_str_relative)
                    max_time_width = max(max_time_width, int(time_bbox[2] - time_bbox[0]))
                if time_str_absolute:
                    time_bbox = font.getbbox(time_str_absolute)
                    max_time_width = max(max_time_width, int(time_bbox[2] - time_bbox[0]))

        # Add padding for visual breathing room (like web version: fontSizes.platform * 0.3)
        platform_padding = int(platform_font_size * 0.3) if max_platform_width > 0 else 0
        time_padding = int(font_size * 0.3)
        self._platform_column_width = (
            max_platform_width + platform_padding if max_platform_width > 0 else 0
        )
        self._time_column_width = max_time_width + time_padding
        self._platform_time_gap = 6  # Gap between platform and time

        # Create RGB image first (we'll dither it later)
        # This allows us to use proper RGB colors that will be dithered to the 7-color palette
        img = Image.new("RGB", (self.config.width, self.config.height), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Calculate heights (must match the calculation in _calculate_font_size)
        bbox = font.getbbox("Mg")
        font_height = bbox[3] - bbox[1]  # Font height without spacing
        line_height = font_height + self.config.line_spacing  # Full line height with spacing
        header_bbox = header_font.getbbox("Mg")
        header_font_height = header_bbox[3] - header_bbox[1]
        header_height = (
            header_font_height + self.config.line_spacing + 4
        )  # Header height with spacing

        # Calculate total height needed
        # Each row takes line_height, but the last row doesn't need spacing after it
        # So subtract one spacing from total
        total_height = (
            (header_height * header_count)
            + (line_height * total_departures)
            - self.config.line_spacing
        )

        # Verify we're using full height when filling space
        available_height = (
            self.config.height if self.config.fill_vertical_space else self.config.usable_height
        )
        logger.info(
            f"Rendering: Total height needed: {total_height}, Available height: {available_height}, Fill vertical space: {self.config.fill_vertical_space}, Font size: {font_size}, Line height: {line_height}"
        )

        # If we're not filling the space and there's wasted space, increase font size
        if self.config.fill_vertical_space and total_height < available_height:
            # The binary search should have found the optimal font size, but if there's still space,
            # it might be due to rounding in font_size_step. Try to find a better fit.
            # Calculate how much we can increase font size
            height_diff = available_height - total_height
            if height_diff > 5:  # Only warn if significant space is wasted
                logger.warning(
                    f"Content height ({total_height}) is {height_diff}px less than available height ({available_height}). Font size: {font_size}, total_departures: {total_departures}, header_count: {header_count}"
                )

        # Calculate starting Y position
        # First header should start at the very top (y=0), not at padding
        start_y = 0

        # Render each group with header
        y = start_y
        for group in groups_with_departures:
            header = group.get("header", "")
            departures = group.get("departures", [])

            # Determine header background color
            # Use blue RGB color for headers (will be dithered to blue palette index)
            # Blue from web version: #087BC4 = RGB(8, 123, 196)
            header_bg_color_rgb = (8, 123, 196)

            # White text on colored background
            header_text_color_rgb = (255, 255, 255)

            # First header starts at y=0, subsequent headers have spacing
            draw.rectangle(
                [0, y, self.config.width, y + header_height],
                fill=header_bg_color_rgb,
            )

            # Draw header text (with padding from left edge)
            header_x = self.config.padding
            # Center text vertically in header
            # Get actual text bounding box for proper centering
            text_bbox = header_font.getbbox(header)
            text_height = text_bbox[3] - text_bbox[1]
            # Center vertically: header_y + (header_height - text_height) / 2
            # Adjust for text baseline (text_bbox[1] is negative for ascent)
            header_text_y = int(y + int(header_height - text_height) // 2 - int(text_bbox[1]))
            draw.text((header_x, header_text_y), header, header_text_color_rgb, font=header_font)
            y += header_height

            # Render departures in this group
            for dep_data in departures:
                self._render_departure_row(draw, dep_data, font, y)
                y += line_height

        # Apply dithering to convert RGB image to 7-color palette
        # This is the key step for proper color rendering on e-ink displays
        img = self._dither_image_to_palette(img)

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
            # Access internal _image attribute for pasting icons
            # This is a known PIL pattern - ImageDraw._image is the underlying Image
            img = getattr(draw, "_image", None)
            if img is None:
                logger.error("Could not access ImageDraw._image")
                return

            # Convert icon to RGB if needed (since main image is now RGB)
            if icon.mode == "P":
                # Convert palette icon to RGB
                icon = icon.convert("RGB")

            # Calculate icon position - icon should fill the entire row height
            # Since icon_size = line_height, it should start at y (text baseline)
            # But we need to align with the text baseline, so adjust for font ascent
            font_bbox = font.getbbox("Mg")
            text_ascent = -font_bbox[1]  # Negative y1 is the ascent
            # Align icon top with text baseline minus ascent (so icon aligns with text)
            icon_y = int(y - text_ascent)

            # Paste icon onto main image (both are RGB now)
            if icon.mode == "RGBA":
                # Create a temporary image with alpha channel
                img.paste(icon, (x, icon_y), icon)
            else:
                # For RGB or other modes, paste directly
                img.paste(icon, (x, icon_y))

            logger.info(
                f"Pasting icon for {transport_type} at ({x}, {icon_y}), size={icon_size}, mode={icon.mode}"
            )
        else:
            logger.warning(f"No icon loaded for transport type: {transport_type}")

        # Add proper spacing after icon (icon size + spacing between icon and route number)
        x += icon_size + self.config.route_icon_spacing

        # Draw route number
        route_text = dep_data.get("line", "")
        draw.text((x, y), route_text, (0, 0, 0), font=font)  # Black RGB
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
            destination_text = self._truncate_text(
                destination_text, font, available_destination_width
            )
        else:
            destination_text = ""  # No space for destination

        if destination_text:
            draw.text((x, y), destination_text, (0, 0, 0), font=font)  # Black RGB

        # Draw platform and time together on the right (vertically aligned like web version)
        # Platform appears as superscript before time (e.g., "1 20:19")
        right_x = self.config.width - self.config.padding

        if time_text:
            # Check if this is a realtime departure (green time in web version)
            # Use green RGB color for realtime (will be dithered to green palette index)
            # Green from web version: #047857 = RGB(4, 120, 87)
            is_realtime = dep_data.get("is_realtime", False)
            time_color_rgb = (4, 120, 87) if is_realtime else (0, 0, 0)

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
                platform_x = (
                    right_x - effective_time_width - effective_gap - self._platform_column_width
                )
                platform_y = y + baseline_offset
                draw.text(
                    (platform_x, platform_y),
                    platform_text,
                    (0, 0, 0),
                    font=self._platform_font,
                )  # Black RGB

                # Time position: right-aligned
                time_x = right_x - time_width
                draw.text((time_x, y), time_text, time_color_rgb, font=font)
            else:
                # Just time, right-aligned (green for realtime, black otherwise)
                time_x = right_x - time_width
                draw.text((time_x, y), time_text, time_color_rgb, font=font)
        elif platform_text:
            # Only platform, right-aligned in fixed column
            platform_x = right_x - self._platform_column_width
            draw.text((platform_x, y), platform_text, (0, 0, 0), font=self._platform_font)  # Black RGB

    def _render_no_departures(self) -> Image.Image:
        """Render 'No departures' message."""
        img = Image.new("RGB", (self.config.width, self.config.height), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        font_size = 32
        font = self._get_font(font_size, bold=False)
        text = "No departures available"

        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (self.config.width - text_width) // 2
        y = (self.config.height - text_height) // 2

        draw.text((x, y), text, (0, 0, 0), font=font)  # Black RGB

        # Apply dithering
        return self._dither_image_to_palette(img)
