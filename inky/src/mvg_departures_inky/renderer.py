"""Renderer for Inky display."""

import logging
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import hitherdither
else:
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

        # Use actual display dimensions if available (inky.width, inky.height)
        # BUT: If config dimensions don't match display dimensions, it means the adapter
        # already swapped them for portrait rendering - don't overwrite!
        if hasattr(display, "width") and hasattr(display, "height"):
            # Only set if display has actual numeric values (not MagicMock)
            display_width = display.width
            display_height = display.height
            if isinstance(display_width, (int, float)) and isinstance(display_height, (int, float)):
                # Only overwrite if config dimensions match display (no swap was done)
                # If they don't match, adapter already swapped them for rotation - preserve them!
                config_before = (self.config.width, self.config.height)
                if self.config.width == display_width and self.config.height == display_height:
                    # Config matches display - use display dimensions (no swap needed)
                    self.config.width = int(display_width)
                    self.config.height = int(display_height)
                    logger.debug(
                        f"Renderer: config matched display, using display dimensions: "
                        f"{self.config.width}x{self.config.height}"
                    )
                else:
                    # Config was already swapped by adapter - keep the swapped dimensions!
                    logger.info(
                        f"Renderer: preserving swapped config dimensions: "
                        f"{self.config.width}x{self.config.height} "
                        f"(display is {display_width}x{display_height}, "
                        f"config was {config_before})"
                    )
            logger.info(
                f"Renderer final dimensions: {self.config.width}x{self.config.height} "
                f"(display: {display.width}x{display.height})"
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

        Font selection:
        - Headers (bold=True): HK Grotesk Bold
        - Routes (bold=False): Fredoka One
        - Fallback: System fonts (DejaVu, Liberation) or default PIL font

        Args:
            size: Font size in points.
            bold: Whether to use bold variant (True for headers, False for routes).

        Returns:
            PIL ImageFont instance.
        """
        cache_key = (size, bold)
        if cache_key not in self._font_cache:
            if bold:
                # Headers: Use HK Grotesk Bold
                hk_grotesk_path = self.config.get_hk_grotesk_font_path(bold=True)
                if hk_grotesk_path and hk_grotesk_path.exists():
                    try:
                        font_obj = ImageFont.truetype(str(hk_grotesk_path), size)
                        logger.info(f"Using HK Grotesk Bold font at size {size} for header")
                        self._font_cache[cache_key] = font_obj
                        return font_obj
                    except Exception as e:
                        logger.debug(
                            f"Failed to load HK Grotesk Bold font: {e}, trying alternatives"
                        )
                else:
                    logger.debug(
                        f"HK Grotesk Bold font not found at {hk_grotesk_path}, trying alternatives"
                    )
            else:
                # Routes: Use Fredoka One
                try:
                    from font_fredoka_one import FredokaOne

                    font_obj = ImageFont.truetype(FredokaOne, size)
                    logger.info(f"Using FredokaOne font at size {size} for route")
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
        white_threshold = 240  # Pixels with all RGB >= 240 are considered white
        black_threshold = 50  # Pixels with all RGB <= 50 are considered black

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
                if r >= white_threshold and g >= white_threshold and b >= white_threshold:
                    result_pixels[x_pos, y_pos] = (255, 255, 255)  # White symbol -> white
                    white_pixels += 1
                # Check if pixel is black/dark - convert to white
                elif r <= black_threshold and g <= black_threshold and b <= black_threshold:
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
        palette_rgb = None
        if hasattr(self.display, "_palette_blend"):
            # Use display's palette blend method if available (real hardware)
            try:
                saturation = 0.5  # Medium saturation for good color representation
                palette_uint24 = self.display._palette_blend(saturation, dtype="uint24")
                # Convert 24-bit RGB values (0xRRGGBB) to (R, G, B) tuples
                if palette_uint24 is not None:
                    palette_rgb = []
                    for color_value in palette_uint24:
                        if isinstance(color_value, int):
                            # Extract R, G, B from 24-bit value: 0xRRGGBB
                            r = int((color_value >> 16) & 0xFF)
                            g = int((color_value >> 8) & 0xFF)
                            b = int(color_value & 0xFF)
                            palette_rgb.append((r, g, b))
                        elif isinstance(color_value, (tuple, list)) and len(color_value) >= 3:
                            # Already in (R, G, B) format
                            palette_rgb.append(
                                (int(color_value[0]), int(color_value[1]), int(color_value[2]))
                            )
            except (AttributeError, TypeError, ValueError) as e:
                logger.debug(f"Could not use _palette_blend: {e}")

        if palette_rgb is None and hasattr(self.display, "palette") and self.display.palette:
            # Use display's palette directly
            try:
                display_palette = self.display.palette
                # Check if it's a real list/array with enough elements
                if isinstance(display_palette, (list, tuple)) and len(display_palette) >= 21:
                    # Convert palette to RGB tuples (first 7 colors)
                    palette_rgb = []
                    for i in range(7):
                        idx = i * 3
                        if idx + 2 < len(display_palette):
                            palette_rgb.append(
                                (
                                    display_palette[idx],
                                    display_palette[idx + 1],
                                    display_palette[idx + 2],
                                )
                            )
                        else:
                            palette_rgb.append((255, 255, 255))  # Default to white
            except (TypeError, AttributeError, IndexError):
                pass

        # Fallback: use our standard 7-color palette
        if palette_rgb is None or len(palette_rgb) == 0:
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
        # hitherdither.Palette can accept a list of RGB tuples
        # Ensure we have at least one color
        if not palette_rgb or len(palette_rgb) == 0:
            logger.error("Empty palette_rgb, using fallback")
            palette_rgb = [
                (0, 0, 0),  # 0: Black
                (255, 255, 255),  # 1: White
            ]
        # hitherdither.Palette accepts list of RGB tuples (it will convert internally if needed)
        hither_palette = hitherdither.palette.Palette(palette_rgb)

        # Use Bayer dithering (fast and good quality, as per Pimoroni example)
        # Thresholds for snapping colors
        thresholds = [64, 64, 64]
        # Order 8 for good quality (higher = better but slower)
        dithered = hitherdither.ordered.bayer.bayer_dithering(
            rgb_image, hither_palette, thresholds, order=8
        )

        # Convert to palette mode
        # hitherdither returns Any, but convert("P") returns Image.Image
        return dithered.convert("P")  # type: ignore[no-any-return]  # hitherdither.bayer_dithering returns Any, but convert() returns Image.Image

    def _get_display_palette_rgb(self) -> list[tuple[int, int, int]]:
        """Get the 7-color palette as RGB tuples.

        Returns:
            List of (R, G, B) tuples for the 7 colors.
        """
        palette_rgb: list[tuple[int, int, int]] | None = None
        if hasattr(self.display, "palette") and self.display.palette:
            try:
                display_palette = self.display.palette
                # Check if it's a real list/array with enough elements
                if isinstance(display_palette, (list, tuple)) and len(display_palette) >= 21:
                    # Convert palette to RGB tuples (first 7 colors)
                    palette_rgb = []
                    for i in range(7):
                        idx = i * 3
                        if idx + 2 < len(display_palette):
                            palette_rgb.append(
                                (
                                    int(display_palette[idx]),
                                    int(display_palette[idx + 1]),
                                    int(display_palette[idx + 2]),
                                )
                            )
                        else:
                            palette_rgb.append((255, 255, 255))  # Default to white
            except (TypeError, AttributeError, IndexError) as e:
                logger.debug(f"Could not use display.palette: {e}")

        # Fallback to default 7-color palette if display palette not available
        if palette_rgb is None or len(palette_rgb) < 7:
            palette_rgb = [
                (0, 0, 0),  # 0: Black
                (255, 255, 255),  # 1: White
                (4, 120, 87),  # 2: Green (#047857 - darker green for realtime)
                (8, 123, 196),  # 3: Blue (#087BC4 - less saturated blue for headers)
                (255, 0, 0),  # 4: Red
                (255, 255, 0),  # 5: Yellow
                (255, 165, 0),  # 6: Orange
            ]

        return palette_rgb

    def _load_refresh_icon(self, icon_size: int) -> Image.Image | None:
        """Load refresh icon from SVG file.

        Converts SVG to PIL Image using cairosvg or falls back to text-based icon.

        Args:
            icon_size: Size for the icon.

        Returns:
            PIL Image with icon, or None if not available.
        """
        # Cache key includes size to support dynamic sizing
        cache_key = ("refresh_icon", icon_size)
        if cache_key in self._icon_cache:
            cached_icon = self._icon_cache[cache_key]
            if cached_icon is not None:
                return cached_icon
            # If cached as None, don't retry (to avoid repeated failures)
            logger.debug("Refresh icon was previously cached as None, skipping")
            return None

        # Get path to refresh icon in parent project's static/assets directory
        # Path structure: inky/src/mvg_departures_inky/renderer.py
        # Need to go up 4 levels: renderer.py -> mvg_departures_inky -> src -> inky -> project root
        parent_project = Path(__file__).parent.parent.parent.parent
        icon_path = parent_project / "static" / "assets" / "refresh-icon.svg"

        if not icon_path.exists():
            logger.error(
                f"Refresh icon file not found at: {icon_path} (absolute: {icon_path.resolve()})"
            )
            self._icon_cache[cache_key] = None
            return None

        logger.info(f"Loading refresh icon from: {icon_path} (exists: {icon_path.exists()})")
        try:
            # Try using cairosvg to convert SVG to PNG
            try:
                import cairosvg

                # Convert SVG to PNG bytes (RGBA format)
                # Use a larger size for better quality, then resize
                render_size = icon_size * 2
                png_bytes = cairosvg.svg2png(
                    url=str(icon_path),
                    output_width=render_size,
                    output_height=render_size,
                )

                # Load PNG bytes into PIL Image
                icon = Image.open(BytesIO(png_bytes))

                # Keep icon in RGBA mode to preserve transparency
                # We'll convert black icon shape to white while keeping transparent background
                if icon.mode != "RGBA":
                    icon = icon.convert("RGBA")  # type: ignore[assignment]

                # For refresh icon, we want white icon on colored background
                # Convert black parts to white while preserving transparency
                pixels = icon.load()
                if pixels is None:
                    logger.error("Failed to load pixels for refresh icon")
                    self._icon_cache[cache_key] = None
                    return None

                # Convert black/dark pixels to white, keep transparent pixels transparent
                black_threshold = 50
                for y_pos in range(icon.height):
                    for x_pos in range(icon.width):
                        pixel_val = pixels[x_pos, y_pos]
                        if isinstance(pixel_val, tuple) and len(pixel_val) >= 4:
                            r, g, b, a = pixel_val[0], pixel_val[1], pixel_val[2], pixel_val[3]
                            # If pixel is black/dark and not transparent, make it white
                            if (
                                a > 0
                                and r <= black_threshold
                                and g <= black_threshold
                                and b <= black_threshold
                            ):
                                pixels[x_pos, y_pos] = (255, 255, 255, a)  # White with same alpha
                            # Otherwise keep the color and alpha as is

                # Resize to final size (always resize since we rendered at 2x)
                icon = icon.resize(  # type: ignore[assignment]
                    (icon_size, icon_size),
                    Image.Resampling.LANCZOS,
                )

                logger.info(f"Successfully loaded refresh icon at size {icon_size}")
                self._icon_cache[cache_key] = icon
                return icon
            except ImportError:
                logger.debug("cairosvg not available, trying alternative methods")
                # Try using svglib as fallback
                try:
                    from reportlab.graphics import renderPM  # No type stubs
                    from svglib.svglib import svg2rlg  # Optional dependency

                    drawing = svg2rlg(str(icon_path))
                    if drawing:
                        # Render to PIL Image
                        img_data = renderPM.drawToString(drawing, fmt="PNG")
                        icon = Image.open(BytesIO(img_data))

                        # Keep in RGBA mode to preserve transparency
                        if icon.mode != "RGBA":
                            icon = icon.convert("RGBA")  # type: ignore[assignment]

                        # Convert black/dark pixels to white while preserving transparency
                        pixels = icon.load()
                        if pixels is not None:
                            black_threshold = 50
                            for y_pos in range(icon.height):
                                for x_pos in range(icon.width):
                                    pixel_val = pixels[x_pos, y_pos]
                                    if isinstance(pixel_val, tuple) and len(pixel_val) >= 4:
                                        r, g, b, a = (
                                            pixel_val[0],
                                            pixel_val[1],
                                            pixel_val[2],
                                            pixel_val[3],
                                        )
                                        # If pixel is black/dark and not transparent, make it white
                                        if (
                                            a > 0
                                            and r <= black_threshold
                                            and g <= black_threshold
                                            and b <= black_threshold
                                        ):
                                            pixels[x_pos, y_pos] = (
                                                255,
                                                255,
                                                255,
                                                a,
                                            )  # White with same alpha

                        # Resize to target size
                        if icon.size != (icon_size, icon_size):
                            icon = icon.resize(  # type: ignore[assignment]
                                (icon_size, icon_size),
                                Image.Resampling.LANCZOS,
                            )

                        self._icon_cache[cache_key] = icon
                        return icon
                    self._icon_cache[cache_key] = None
                    return None
                except ImportError:
                    logger.debug("svglib not available, no SVG conversion library found")
                    logger.error(
                        "Neither cairosvg nor svglib available for refresh icon conversion"
                    )
                    self._icon_cache[cache_key] = None
                    return None
        except Exception as e:
            logger.error(
                f"Could not load refresh icon from {icon_path}: {e}",
                exc_info=True,
            )
            self._icon_cache[cache_key] = None
            return None

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
                # Image.open() returns ImageFile which is compatible with Image.Image
                icon = Image.open(BytesIO(png_bytes))

                # Convert to RGB first (handle RGBA if needed)
                if icon.mode == "RGBA":
                    # Create a white background and composite the icon on it
                    bg = Image.new("RGB", icon.size, (255, 255, 255))
                    bg.paste(icon, mask=icon.split()[3])  # Use alpha channel as mask
                    icon = bg  # type: ignore[assignment]  # PIL: Image.new() returns Image which is compatible
                elif icon.mode != "RGB":
                    icon = icon.convert("RGB")  # type: ignore[assignment]  # PIL: convert() returns Image which is compatible

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
                icon = icon_rgb  # type: ignore[assignment]  # PIL: _convert_colored_icon_to_rgb_with_colors returns Image.Image which is compatible

                # Resize to final size (always resize since we rendered at 2x)
                # Use high-quality resampling for better icon rendering
                icon = icon.resize(  # type: ignore[assignment]  # PIL: resize() returns Image which is compatible
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
                    from reportlab.graphics import renderPM  # No type stubs
                    from svglib.svglib import svg2rlg  # Optional dependency

                    drawing = svg2rlg(str(icon_path))
                    if drawing:
                        # Render to PIL Image
                        img_data = renderPM.drawToString(drawing, fmt="PNG")
                        icon = Image.open(BytesIO(img_data))

                        # Convert to palette mode
                        if icon.mode != "P":
                            # Convert to grayscale first, then to palette with adaptive colors
                            icon_gray = icon.convert("L")
                            icon = icon_gray.quantize(colors=2, method=Image.Quantize.MEDIANCUT)  # type: ignore[assignment]  # PIL: quantize() returns Image which is compatible
                        if hasattr(self.display, "palette"):
                            icon.putpalette(self.display.palette)

                        # Resize to target size
                        if icon.size != (target_size, target_size):
                            icon = icon.resize(  # type: ignore[assignment]  # PIL: resize() returns Image which is compatible
                                (target_size, target_size),
                                Image.Resampling.LANCZOS,
                            )

                        self._icon_cache[cache_key] = icon
                        return icon
                    # If drawing is None/falsy, fall through to error handling
                    self._icon_cache[cache_key] = None
                    return None
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

    def _calculate_header_font_size(
        self, header_text: str, available_width: int, refresh_icon_size: int | None = None
    ) -> int:
        """Calculate optimal header font size to fit the longest header text.

        Args:
            header_text: The header text to fit (should be the longest header).
            available_width: Available width for header text (display width - 2 * padding).
            refresh_icon_size: Optional refresh icon size to display on the right.
                              If provided, ensures both header and icon fit without overlap.

        Returns:
            Optimal header font size.
        """
        if not header_text:
            return self.config.max_font_size

        # Try font sizes from max to min to find the largest that fits
        for font_size in range(
            self.config.max_font_size,
            self.config.min_font_size - 1,
            -self.config.font_size_step,
        ):
            header_font = self._get_font(font_size, bold=True)
            header_bbox = header_font.getbbox(header_text)
            header_width = header_bbox[2] - header_bbox[0]

            # If refresh icon size is provided, check that both fit with proper spacing
            if refresh_icon_size is not None:
                # Icon width is the same as icon size (square icon)
                icon_width = refresh_icon_size
                # Need space for: header_text + gap + icon + time_text
                # Gap between header and icon (minimum 10px for readability)
                gap = 10
                # Time text width (e.g., "14:30" - 5 characters)
                # Calculate time text width using the same font
                # Use local time for display (not UTC)
                time_text = datetime.now().strftime("%H:%M")  # noqa: DTZ005
                time_bbox = header_font.getbbox(time_text)
                time_width = time_bbox[2] - time_bbox[0]
                # Gap between icon and time
                icon_time_gap = 4
                total_width_needed = header_width + gap + icon_width + icon_time_gap + time_width

                if total_width_needed <= available_width:
                    logger.debug(
                        f"Header font size {font_size} fits with refresh icon: "
                        f"header_width={header_width}, icon_width={icon_width}, time_width={time_width}, "
                        f"total={total_width_needed} <= available={available_width}"
                    )
                    return font_size
            else:
                # No refresh icon, just check header text fits
                if header_width <= available_width:
                    logger.debug(
                        f"Header font size {font_size} fits: width={header_width} <= available={available_width}"
                    )
                    return font_size

        # If no font size fits, return minimum
        logger.warning(
            f"No header font size fits! Min font size {self.config.min_font_size} will be used. "
            f"Header text: '{header_text}', refresh_icon_size: {refresh_icon_size}, available width: {available_width}"
        )
        return self.config.min_font_size

    def _calculate_font_size_with_header(
        self,
        total_items: int,
        header_count: int,
        header_font_size: int,
        initial_font_size: int,
    ) -> int:
        """Calculate optimal body font size that fits vertically with given header font size.

        Args:
            total_items: Total number of departure rows (actual count from data).
            header_count: Number of header rows (actual count from data).
            header_font_size: Pre-calculated header font size (based on longest header text).
            initial_font_size: Initial body font size to try (typically 85% of header).

        Returns:
            Optimal body font size that fits vertically.
        """
        if total_items == 0:
            return initial_font_size

        # Always use full height for Inky displays (fill_vertical_space is always enabled)
        # No padding since we start at y=0
        available_height = self.config.height

        # Headers will use the same height as departure rows (line_height) for better vertical space distribution
        # We'll calculate the actual header_height based on line_height in the loop below
        # Header font will be recalculated in the render method based on final line_height
        # (header_font_size is used in the loop, but header_font itself is created in render method)

        # Always fill vertical space for Inky displays
        if True:  # fill_vertical_space is always True for Inky
            # Try font sizes from initial_font_size down to min to find the largest that fits
            # This maximizes font size usage and fills vertical space better
            best_font_size = None
            best_total_height = 0

            # Start from initial_font_size (which is already constrained to header_font_size or max_font_size)
            # and work down to find the largest that fits
            start_font_size = initial_font_size

            for font_size in range(
                start_font_size,
                self.config.min_font_size - 1,
                -self.config.font_size_step,
            ):
                font = self._get_font(font_size, bold=False)
                bbox = font.getbbox("Mg")
                font_height = bbox[3] - bbox[1]
                line_height = font_height + self.config.line_spacing

                # Headers use the same height as departure rows for better vertical space distribution
                header_height = line_height

                total_height = (
                    (header_height * header_count)  # Headers same height as rows
                    + (line_height * total_items)
                    - self.config.line_spacing
                )

                if total_height <= available_height and total_height > best_total_height:
                    best_font_size = font_size
                    best_total_height = int(total_height)
                    logger.debug(
                        f"Body font size {font_size} fits with header {header_font_size}: "
                        f"total_height={total_height} <= available_height={available_height}"
                    )

            if best_font_size is not None:
                # If we have unused space, try to distribute it by increasing line_height
                # This will be handled in the render method by adjusting line_height
                return best_font_size

            # If no font size fits, return minimum
            logger.warning(
                f"No body font size fits with header {header_font_size}! "
                f"Min font size {self.config.min_font_size} will be used. "
                f"Available height: {available_height}, total_items: {total_items}, header_count: {header_count}"
            )
            return self.config.min_font_size

        # When not filling, just find largest that fits
        for font_size in range(
            initial_font_size,
            self.config.min_font_size - 1,
            -self.config.font_size_step,
        ):
            font = self._get_font(font_size, bold=False)
            bbox = font.getbbox("Mg")
            font_height = bbox[3] - bbox[1]
            line_height = font_height + self.config.line_spacing

            total_height = (
                (header_height * header_count)
                + (line_height * total_items)
                - self.config.line_spacing
            )

            if total_height <= available_height:
                return font_size

        return self.config.min_font_size

    def _calculate_font_size(self, total_items: int, header_count: int) -> int:
        """Calculate optimal font size to fit all content and maximize when filling space.

        Finds the font size that makes total_height equal to available_height (or as close as possible).
        For Inky displays, fill_vertical_space is always enabled.

        Args:
            total_items: Total number of departure rows (actual count from data).
            header_count: Number of header rows (actual count from data).

        Returns:
            Optimal font size.
        """
        if total_items == 0:
            return self.config.max_font_size

        # Always use full height for Inky displays (fill_vertical_space is always enabled)
        # No padding since we start at y=0
        available_height = self.config.height

        # Always fill vertical space for Inky displays
        if True:  # fill_vertical_space is always True for Inky
            # Try all font sizes from max to min to find the one that maximizes space usage
            # Keep track of the best font size (largest total_height that still fits)
            best_font_size = None
            best_total_height = 0

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

                # Headers use the same height as departure rows for better vertical space distribution
                # Header font size will be calculated in render method based on final line_height
                # Headers use the same height as departure rows
                header_height = line_height

                # Calculate total height:
                # Each row takes line_height (font_height + spacing)
                # If we have N rows, we have N-1 gaps between them
                # But line_height already includes spacing for each row, so we're counting N spacings
                # The last row doesn't need spacing after it, so subtract one spacing
                total_height = (
                    (header_height * header_count)  # Headers same height as rows
                    + (line_height * total_items)
                    - self.config.line_spacing
                )

                # This font size fits - check if it uses more space than previous best
                if total_height <= available_height and total_height > best_total_height:
                    best_font_size = font_size
                    best_total_height = int(total_height)
                    logger.debug(
                        f"Font size {font_size} fits: total_height={total_height} <= available_height={available_height}"
                    )

            if best_font_size is not None:
                # Log if we're not using all available space
                height_diff = available_height - best_total_height
                if height_diff > 2:  # Only warn if more than 2px wasted
                    logger.debug(
                        f"Best font size {best_font_size} uses {best_total_height}px of {available_height}px "
                        f"({height_diff}px unused, likely due to font_size_step={self.config.font_size_step})"
                    )
                return best_font_size

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

            # Headers use the same height as departure rows for better vertical space distribution
            # Header font size will be calculated in render method based on final line_height
            # Headers use the same height as departure rows
            header_height = line_height

            # Calculate total height:
            # Each row takes line_height, but the last row doesn't need spacing after it
            # So subtract one spacing from total
            total_height = (
                (header_height * header_count)  # Headers same height as rows
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

        # Find the longest header text and first header to ensure they fit in the available width
        longest_header = ""
        first_header = ""
        for idx, group in enumerate(groups_with_departures):
            header = group.get("header", "")
            if idx == 0:
                first_header = header
            if len(header) > len(longest_header):
                longest_header = header

        # Calculate header font size based on fitting headers into available width
        # Available width for header = display width - 2 * padding (left and right)
        # For the first header, we also need to account for the refresh icon + time on the right
        available_header_width = self.config.width - (2 * self.config.padding)

        # Store current time for rendering
        # Use local time for display (not UTC)
        current_time = datetime.now().strftime("%H:%M")  # noqa: DTZ005
        self._update_time = current_time

        # Calculate font size: icon size will be proportional to font size (0.8x)
        # We need to find a font size where both first header (with icon) and longest header (without icon) fit
        # Use iterative approach: try different icon sizes and find the best font size

        # Calculate font size for first header with refresh icon
        # Start by assuming icon size is 0.8x of max font size, then iterate
        first_header_font_size_with_icon = self.config.max_font_size
        if first_header:
            # Try with icon size proportional to font size
            # We'll iterate: for each potential font size, calculate icon size and check if it fits
            for trial_font_size in range(
                self.config.max_font_size,
                self.config.min_font_size - 1,
                -self.config.font_size_step,
            ):
                trial_icon_size = max(int(trial_font_size * 0.6), 12)
                calculated_font_size = self._calculate_header_font_size(
                    first_header, available_header_width, refresh_icon_size=trial_icon_size
                )
                # If calculated size is >= trial, this size works
                if calculated_font_size >= trial_font_size:
                    first_header_font_size_with_icon = trial_font_size
                    break
                # Otherwise, the calculated size is the best we can do
                first_header_font_size_with_icon = calculated_font_size

        # Calculate font size for longest header without icon (if different from first)
        longest_header_font_size = self.config.max_font_size
        if longest_header and longest_header != first_header:
            longest_header_font_size = self._calculate_header_font_size(
                longest_header, available_header_width, refresh_icon_size=None
            )

        # Use the smaller font size to ensure both fit
        header_font_size = min(first_header_font_size_with_icon, longest_header_font_size)

        # Calculate icon size based on final font size (0.6x for proper sizing, minimum 12px)
        # Reduced from 0.8x to 0.6x to make refresh icon smaller and fit better in header
        refresh_icon_size = max(int(header_font_size * 0.6), 12)

        # Store icon size for rendering
        self._refresh_icon_size = refresh_icon_size

        # Pre-cache the refresh icon at the calculated size
        # This ensures it's ready when we need to render it
        if first_header:
            refresh_icon = self._load_refresh_icon(refresh_icon_size)
            if refresh_icon is None:
                logger.warning(f"Failed to pre-cache refresh icon at size {refresh_icon_size}")

        header_font = self._get_font(header_font_size, bold=True)

        # Calculate body font size - try to maximize it to fill vertical space
        # Start from max_font_size and work down, but ensure body doesn't exceed header by too much
        # This allows us to use larger fonts when there's vertical space available
        # Body font can be up to 110% of header size (slightly larger is OK if it fits better)
        # or max_font_size, whichever is smaller
        max_body_font_size = min(
            int(
                header_font_size * 1.1
            ),  # Allow body to be up to 10% larger than header if it fits better
            self.config.max_font_size,  # But also respect max_font_size
        )
        # Verify this font size fits vertically with the calculated header font size
        # Start from max_body_font_size and work down to find the largest that fits
        calculated_font_size = self._calculate_font_size_with_header(
            total_departures, header_count, header_font_size, max_body_font_size
        )

        # Apply font scaling factor (only affects body fonts, not headers)
        # This allows fine-tuning the body font size independently of header font size
        # fill_vertical_space is always enabled for Inky displays
        # The scaling factor is applied to make fonts larger (if > 1.0) or smaller (if < 1.0)
        # Since we're filling vertical space, we want to use the calculated size and scale it
        font_size = max(
            self.config.min_font_size,
            int(calculated_font_size * self.config.font_scaling_factor_when_filling),
        )
        logger.debug(
            f"Font size calculation: calculated={calculated_font_size}, "
            f"scaling_factor={self.config.font_scaling_factor_when_filling}, "
            f"final={font_size}"
        )
        font = self._get_font(font_size, bold=False)
        platform_font_size = max(int(font_size * 0.7), 10)
        self._platform_font = self._get_font(platform_font_size, bold=False)

        # Header height will be set to match line_height in the render method
        # We'll adjust header font size to fit within that height
        # For now, just store the header font (will be adjusted later)

        # Calculate route number column width dynamically to fit at least 4 characters
        # This prevents overlap when route numbers are longer
        # Measure width of 4 characters (e.g., "U123" or "N123") to ensure they fit
        # Use "U123" as representative of typical route numbers (U-Bahn, Bus, etc.)
        test_text = "U123"  # 4 characters: letter + 3 digits (typical route format)
        route_bbox = font.getbbox(test_text)
        route_number_width = max(
            route_bbox[2] - route_bbox[0] + self.config.padding,  # Width of 4 chars + padding
            self.config.route_number_width,  # But at least the configured minimum
        )
        self._route_number_width = int(route_number_width)

        # Calculate line height first (needed for icon size)
        # Note: line_height may be adjusted later to fill remaining vertical space
        font_bbox = font.getbbox("Mg")
        line_height = font_bbox[3] - font_bbox[1] + self.config.line_spacing

        # Icon size will be calculated after line_height is adjusted for remaining space

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

        # Headers should have the same height as departure rows for better vertical space distribution
        header_height = line_height  # Same as departure row height

        # Adjust header font size to fit within the header height
        # We want the font to fit within line_height, leaving some padding
        # Try to fit the header text within the available height
        max_header_font_size = int(line_height * 0.85)  # Use 85% of line height for font
        # Ensure header font is at least as large as body font, but not larger than max_header_font_size
        header_font_size = min(max(header_font_size, font_size), max_header_font_size)
        header_font = self._get_font(header_font_size, bold=True)

        # Calculate total height needed
        # Each row takes line_height, but the last row doesn't need spacing after it
        # So subtract one spacing from total
        total_height = (
            (header_height * header_count)
            + (line_height * total_departures)
            - self.config.line_spacing
        )

        # Always use full height for Inky displays (fill_vertical_space is always enabled)
        # Use full height - no padding, content should fill from top to bottom
        available_height = self.config.height

        # Calculate exact line_height needed to fill the available height
        # Since headers are now the same height as departure rows, we distribute among all rows
        total_rows = header_count + total_departures
        if total_rows > 0:
            # Formula: total_height = (line_height * total_rows) - line_spacing = available_height
            # Therefore: line_height = (available_height + line_spacing) / total_rows
            # This ensures we fill exactly to the bottom with no wasted space
            # Keep as float to avoid quantization - we'll distribute fractional pixels across rows
            line_height_float = (available_height + self.config.line_spacing) / total_rows
            header_height_float = line_height_float  # Headers same height as rows

            # Store the float value for precise calculation
            # We'll use integer positions when rendering, but accumulate fractional parts
            # to ensure we reach exactly available_height at the end
            self._line_height_float = line_height_float
            self._header_height_float = header_height_float

            # For rendering, we'll use integer positions but track fractional accumulation
            # Store the base integer height (floor)
            line_height_base = int(line_height_float)
            header_height_base = int(header_height_float)

            # Calculate how many extra pixels we need to distribute
            # Total height with base integer heights
            total_height_base = (
                (header_height_base * header_count)
                + (line_height_base * total_departures)
                - self.config.line_spacing
            )
            extra_pixels = available_height - total_height_base

            # Distribute extra pixels across rows (one pixel per row until we run out)
            # This ensures we fill exactly to available_height
            self._line_height_extra_pixels = [0] * total_rows
            for i in range(min(extra_pixels, total_rows)):
                self._line_height_extra_pixels[i] = 1

            # Calculate final line_height for rendering (base + extra if any)
            # Most rows will be line_height_base, some will be line_height_base + 1
            line_height = line_height_base
            header_height = header_height_base

            # Verify we'll fill exactly
            total_height = (
                (header_height_base * header_count)
                + (line_height_base * total_departures)
                + sum(self._line_height_extra_pixels)
                - self.config.line_spacing
            )

            logger.debug(
                f"Filled vertical space: line_height_base={line_height_base}, "
                f"extra_pixels={extra_pixels}, total_height={total_height}, "
                f"available_height={available_height}, total_rows={total_rows}"
            )

            if total_height != available_height:
                logger.warning(
                    f"Height mismatch: total_height={total_height}, "
                    f"available_height={available_height}, diff={available_height - total_height}px"
                )
        else:
            # No rows, use default
            line_height = font_height + self.config.line_spacing
            header_height = line_height
            self._line_height_float = float(line_height)
            self._header_height_float = float(header_height)
            self._line_height_extra_pixels = []

        # Store base line_height for use in _render_departure_row
        self._line_height = line_height
        self._header_height = header_height

        # Recalculate refresh icon size based on header height (same logic as transport icons)
        # Use header_height - 2 to ensure at least 1px padding on top and bottom (one dot whitespace)
        # This matches how transport icons are sized: line_height - 2
        if hasattr(self, "_refresh_icon_size"):
            # Recalculate based on actual header height instead of font size
            refresh_icon_size_from_height = header_height - 2  # Same as transport icons: row_height - 2
            # Keep minimum size for visibility
            refresh_icon_size_from_height = max(refresh_icon_size_from_height, 12)
            # Don't exceed maximum configured size
            refresh_icon_size_from_height = min(refresh_icon_size_from_height, self.config.route_icon_max_size)
            self._refresh_icon_size = int(refresh_icon_size_from_height)
            logger.debug(
                f"Recalculated refresh icon size based on header height: {self._refresh_icon_size} "
                f"(header_height={header_height}, transport icon logic: height - 2)"
            )

        # Calculate icon size based on font size (like web version: height: 1em)
        # Icon should scale with font size to save horizontal space when font is smaller
        # But also ensure it fits within the row with proper spacing
        # Use font_size * 1.2 as base (larger than 1em for better visibility)
        # Constrain to row height - 2 for spacing (leaves 1px top + 1px bottom = "one dot whitespace")
        # This adapts icon size to font size, saving horizontal space when needed
        icon_size_from_font = int(font_size * 1.2)  # 1.2em equivalent for larger icons
        icon_size_from_row = (
            line_height - 2
        )  # Maximum size to fit in row with 2px spacing (1px top + 1px bottom)

        # Use the smaller of the two to ensure it fits and scales with font
        calculated_icon_size = min(icon_size_from_font, icon_size_from_row)

        # Apply minimum (12px) for better visibility on e-ink displays
        # This allows icons to scale down with small fonts, but keeps them visible
        calculated_icon_size = max(calculated_icon_size, 12)

        # But also ensure it doesn't exceed the maximum configured size
        calculated_icon_size = min(calculated_icon_size, self.config.route_icon_max_size)

        self._calculated_icon_size = int(calculated_icon_size)
        logger.debug(
            f"Final icon size: {calculated_icon_size} "
            f"(font_size: {font_size}, line_height: {line_height}, "
            f"from_font: {icon_size_from_font}, from_row: {icon_size_from_row})"
        )

        logger.info(
            f"Rendering: Total height: {total_height}, "
            f"Available height: {available_height}, "
            f"Font size: {font_size}, Line height: {line_height}"
        )

        # Calculate starting Y position
        # First header should start at the very top (y=0), no padding
        start_y = 0

        # Track which row we're on (for distributing extra pixels)
        row_index = 0

        # Render each group with header
        y = start_y
        for group in groups_with_departures:
            header = group.get("header", "")
            departures = group.get("departures", [])

            # Determine header background color
            # Use DESATURATED_PALETTE from Inky display (as per Pimoroni example)
            # This gives us the exact RGB values that won't dither
            # DESATURATED_PALETTE order: [black, white, green, blue, red, yellow, orange]
            # Blue is at index 3
            if hasattr(self.display, "DESATURATED_PALETTE") and len(self.display.DESATURATED_PALETTE) > 3:
                # DESATURATED_PALETTE contains RGB tuples (0-255 range)
                header_bg_color_rgb = tuple(self.display.DESATURATED_PALETTE[3])
            else:
                # Fallback: get from palette RGB or use default
                palette_rgb = self._get_display_palette_rgb()
                if len(palette_rgb) > 3:
                    header_bg_color_rgb = palette_rgb[3]
                else:
                    # Final fallback: default Inky blue RGB(8, 123, 196) = #087BC4
                    header_bg_color_rgb = (8, 123, 196)

            # White text on colored background
            header_text_color_rgb = (255, 255, 255)

            # Get actual header height for this row (base + extra pixel if applicable)
            actual_header_height = int(self._header_height)
            if row_index < len(getattr(self, "_line_height_extra_pixels", [])):
                actual_header_height += int(self._line_height_extra_pixels[row_index])

            # First header starts at y=0, subsequent headers have spacing
            draw.rectangle(
                [0, y, self.config.width, y + actual_header_height],
                fill=header_bg_color_rgb,
            )

            # Draw header text (with padding from left edge)
            header_x = self.config.padding
            # Center text vertically in header by capital letters (cap height)
            # PIL's text() y coordinate is the baseline
            # Get cap height from a capital letter to center by capitals, not descenders
            cap_bbox = header_font.getbbox("A")
            # bbox[1] is top (negative = above baseline), bbox[3] is bottom (positive = below baseline)
            # Capital center from baseline = (cap_bbox[1] + cap_bbox[3]) / 2
            capital_center_from_baseline = (cap_bbox[1] + cap_bbox[3]) / 2
            # Header center = y + actual_header_height / 2
            # To center capitals: baseline = header_center - capital_center_from_baseline
            header_center = y + actual_header_height / 2
            header_text_y = int(header_center - capital_center_from_baseline)
            draw.text((header_x, header_text_y), header, header_text_color_rgb, font=header_font)

            # Add refresh icon + time text right-aligned for the first header
            if row_index == 0:
                cached_refresh_icon_size: int | None = getattr(self, "_refresh_icon_size", None)
                update_time = getattr(self, "_update_time", "")

                if cached_refresh_icon_size is not None and update_time:
                    # Load refresh icon (should be cached from pre-loading during font size calculation)
                    refresh_icon = self._load_refresh_icon(cached_refresh_icon_size)

                    # Calculate time text width
                    time_bbox = header_font.getbbox(update_time)
                    time_width = time_bbox[2] - time_bbox[0]

                    # Position elements from right edge with proper padding
                    # Ensure at least 1 pixel padding from right edge (one dot whitespace)
                    # right_x is where content should end (width - padding)
                    right_x = self.config.width - self.config.padding

                    # Time text position (right-aligned, ends at right_x)
                    time_x = right_x - time_width

                    # Gap between icon and time (at least 4px for readability)
                    icon_time_gap = 4

                    # Icon position (to the left of time text)
                    # Ensure icon has at least 1px padding from right edge
                    # Icon's right edge should be at: time_x - icon_time_gap
                    # But we want at least 1px from the right edge, so verify:
                    # icon_right_edge = icon_x + cached_refresh_icon_size
                    # We want: icon_right_edge <= right_x - 1 (at least 1px padding)
                    # So: icon_x + cached_refresh_icon_size <= right_x - 1
                    # Therefore: icon_x <= right_x - 1 - cached_refresh_icon_size
                    icon_x_max = right_x - 1 - cached_refresh_icon_size
                    icon_x_from_time = time_x - icon_time_gap - cached_refresh_icon_size
                    # Use the more restrictive (leftmost) position to ensure padding
                    icon_x = min(icon_x_from_time, icon_x_max)

                    # Verify icon doesn't go beyond left padding (safety check)
                    if icon_x < self.config.padding:
                        logger.warning(
                            f"Icon would overlap left padding: icon_x={icon_x}, padding={self.config.padding}. "
                            f"Adjusting icon size or position may be needed."
                        )
                        # Adjust: move icon to the right if needed
                        icon_x = max(icon_x, self.config.padding)

                    # Center icon vertically in header, but ensure at least 1px padding from top and bottom
                    # Header starts at y, ends at y + actual_header_height
                    icon_y_centered = int(header_center - cached_refresh_icon_size / 2)
                    icon_y_min = int(y + 1)  # At least 1px from top
                    icon_y_max = int(y + actual_header_height - cached_refresh_icon_size - 1)  # At least 1px from bottom
                    icon_y = max(icon_y_min, min(icon_y_centered, icon_y_max))  # Clamp between min and max

                    # Draw time text
                    draw.text(
                        (time_x, header_text_y),
                        update_time,
                        header_text_color_rgb,
                        font=header_font,
                    )

                    # Draw refresh icon
                    if refresh_icon:
                        # Access internal _image attribute for pasting icons
                        refresh_img: Image.Image | None = getattr(draw, "_image", None)
                        if refresh_img is not None:
                            # Convert icon to RGB if needed
                            icon_x_int = int(icon_x)
                            icon_y_int = int(icon_y)
                            if refresh_icon.mode == "RGBA":
                                refresh_img.paste(
                                    refresh_icon, (icon_x_int, icon_y_int), refresh_icon
                                )
                            else:
                                refresh_img.paste(refresh_icon, (icon_x_int, icon_y_int))
                            logger.debug(
                                f"Pasted refresh icon at ({icon_x}, {icon_y}), size={cached_refresh_icon_size}"
                            )
                        else:
                            logger.error("Could not access ImageDraw._image for refresh icon")
                    else:
                        logger.warning("Refresh icon not loaded, skipping icon rendering")

            y += actual_header_height
            row_index += 1

            # Render departures in this group
            for dep_data in departures:
                # Get actual line height for this row (base + extra pixel if applicable)
                actual_line_height = int(self._line_height)
                if row_index < len(getattr(self, "_line_height_extra_pixels", [])):
                    actual_line_height += int(self._line_height_extra_pixels[row_index])

                self._render_departure_row(draw, dep_data, font, int(y), actual_line_height)
                y = int(y + actual_line_height)
                row_index += 1

        # Store RGB image before dithering for change detection
        # (dithering is deterministic, but comparing RGB is more stable)
        self._last_rgb_image = img.copy()

        # Apply dithering to convert RGB image to 7-color palette (if enabled)
        # This is the key step for proper color rendering on e-ink displays
        if self.config.dithering_enabled:
            return self._dither_image_to_palette(img)

        # Dithering disabled: convert RGB to palette mode using nearest color matching
        # This is faster but colors may be less accurate (no dithering)
        # We still need to use the 7-color palette for the display
        palette_rgb = self._get_display_palette_rgb()

        # Create a palette image with the 7 colors
        palette_img = Image.new("P", (1, 1))
        palette_data = []
        for r, g, b in palette_rgb:
            palette_data.extend([r, g, b])
        # Fill remaining palette slots with white
        while len(palette_data) < 768:  # 256 colors * 3 RGB values
            palette_data.extend([255, 255, 255])
        palette_img.putpalette(palette_data)

        # Quantize the RGB image to the palette (nearest color, no dithering)
        return img.quantize(palette=palette_img, dither=Image.Dither.NONE)

    def _render_departure_row(
        self,
        draw: ImageDraw.ImageDraw,
        dep_data: dict[str, Any],
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        y: int,
        line_height: int | None = None,
    ) -> None:
        """Render a single departure row.

        Args:
            draw: PIL ImageDraw instance.
            dep_data: Formatted departure data (from DepartureGroupingCalculator).
            font: Font to use.
            y: Y position for this row (top of the row).
            line_height: Optional line height for this row. If None, uses stored _line_height.
        """
        # Calculate bottom alignment for all text in this row
        # Find the maximum bottom offset (bbox[3]) among all text elements
        route_text = dep_data.get("line", "")
        destination_text = dep_data.get("destination", "")
        platform_text = dep_data.get("platform", "") or ""

        # Get bounding boxes for route and platform (destination and time use route_baseline)
        route_bbox = font.getbbox(route_text) if route_text else (0, 0, 0, 0)
        platform_bbox = (
            self._platform_font.getbbox(platform_text) if platform_text else (0, 0, 0, 0)
        )

        # Get time text based on time_mode
        # Time is always shown, but the format depends on the mode
        if self.config.time_mode == "relative":
            time_text = dep_data.get("time_str_relative", "")
        else:  # absolute (default)
            time_text = dep_data.get("time_str_absolute", "")

        time_bbox = font.getbbox(time_text) if time_text else (0, 0, 0, 0)

        # Calculate baseline for each text element so all are centered vertically in the row
        # y is the top of the row, row extends from y to y + line_height
        # Row center = y + line_height / 2
        # For each text element, calculate its center from baseline and align with row center
        # Use provided line_height if available, otherwise fall back to stored value
        if line_height is None:
            stored_line_height = getattr(self, "_line_height", None)
            if stored_line_height is not None:
                line_height = int(stored_line_height)
            else:
                line_height = int(
                    self.config.line_spacing + font.getbbox("Mg")[3] - font.getbbox("Mg")[1]
                )
        else:
            line_height = int(line_height)
        # line_height is now guaranteed to be int
        row_center = y + line_height / 2

        # Calculate text center from baseline for route and platform
        # bbox[1] is top (negative = above baseline), bbox[3] is bottom (positive = below baseline)
        # Text center from baseline = (bbox[1] + bbox[3]) / 2
        # We use route_baseline for route, destination, and time to align them horizontally
        route_center_from_baseline = (route_bbox[1] + route_bbox[3]) / 2 if route_text else 0
        platform_center_from_baseline = (
            (platform_bbox[1] + platform_bbox[3]) / 2 if platform_text else 0
        )

        # Position each text element so its center aligns with row center
        # baseline = row_center - text_center_from_baseline
        # We use route_baseline for route, destination, and time to align them horizontally
        route_baseline = int(row_center - route_center_from_baseline) if route_text else 0
        platform_baseline = int(row_center - platform_center_from_baseline) if platform_text else 0

        x = self.config.padding

        # Add at least 1 pixel gap before icon (spacing between icons if multiple)
        icon_gap_before = 1
        x += icon_gap_before

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

            # Calculate icon position - center icon perfectly in the row
            # y is the top of the row, row extends from y to y + line_height
            # Row center = y + line_height / 2
            # Icon should be centered at row center: icon_y + icon_size / 2 = row_center
            # Therefore: icon_y = row_center - icon_size / 2 = y + line_height / 2 - icon_size / 2
            # line_height is already set above from the function parameter or stored value
            # Ensure line_height is an int (it should be set above, but handle None case)
            if line_height is None:
                stored_line_height = getattr(self, "_line_height", None)
                if stored_line_height is not None:
                    line_height = int(stored_line_height)
                else:
                    line_height = int(
                        self.config.line_spacing + font.getbbox("Mg")[3] - font.getbbox("Mg")[1]
                    )
            else:
                line_height = int(line_height)
            # line_height is now guaranteed to be int
            row_center = y + line_height / 2
            icon_y = int(row_center - icon_size / 2)

            # Paste icon onto main image (both are RGB now)
            if icon.mode == "RGBA":
                # Create a temporary image with alpha channel
                img.paste(icon, (x, icon_y), icon)
            else:
                # For RGB or other modes, paste directly
                img.paste(icon, (x, icon_y))

            logger.debug(
                f"Pasting icon for {transport_type} at ({x}, {icon_y}), "
                f"size={icon_size}, mode={icon.mode}"
            )
        else:
            logger.warning(f"No icon loaded for transport type: {transport_type}")

        # Add proper spacing after icon (icon size + spacing between icon and route number)
        # Add at least 1 pixel gap between icon and route number
        icon_gap = max(1, self.config.route_icon_spacing)
        x += icon_size + icon_gap

        # Draw route number (center-aligned)
        if route_text:
            draw.text((x, route_baseline), route_text, (0, 0, 0), font=font)  # Black RGB
        # Use dynamically calculated route number width
        route_number_width = getattr(self, "_route_number_width", self.config.route_number_width)
        x += route_number_width + self.config.padding

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

        # Truncate destination if needed to avoid overlap
        if available_destination_width > 0:
            destination_text = self._truncate_text(
                destination_text, font, available_destination_width
            )
        else:
            destination_text = ""  # No space for destination

        # Draw destination (same baseline as route number for horizontal alignment)
        if destination_text:
            # Use route_baseline to ensure destination starts at same level as route number
            draw.text((x, route_baseline), destination_text, (0, 0, 0), font=font)  # Black RGB

        # Draw platform and time together on the right (center-aligned with all text)
        right_x = self.config.width - self.config.padding

        if time_text:
            # Check if this is a realtime departure (green time in web version)
            # Use green RGB color for realtime (will be dithered to green palette index)
            # Green from web version: #047857 = RGB(4, 120, 87)
            is_realtime = dep_data.get("is_realtime", False)
            time_color_rgb = (4, 120, 87) if is_realtime else (0, 0, 0)

            # Calculate actual time width for this specific time text
            time_width = time_bbox[2] - time_bbox[0]

            if platform_text:
                # Platform position: fixed column width, left-aligned within column (center-aligned)
                platform_x = (
                    right_x - effective_time_width - effective_gap - self._platform_column_width
                )
                draw.text(
                    (platform_x, platform_baseline),
                    platform_text,
                    (0, 0, 0),
                    font=self._platform_font,
                )  # Black RGB

                # Time position: right-aligned (same baseline as route number for horizontal alignment)
                time_x = right_x - time_width
                draw.text((time_x, route_baseline), time_text, time_color_rgb, font=font)
            else:
                # Just time, right-aligned (same baseline as route number for horizontal alignment)
                time_x = right_x - time_width
                draw.text((time_x, route_baseline), time_text, time_color_rgb, font=font)
        elif platform_text:
            # Only platform, right-aligned in fixed column (center-aligned)
            platform_x = right_x - self._platform_column_width
            draw.text(
                (platform_x, platform_baseline), platform_text, (0, 0, 0), font=self._platform_font
            )  # Black RGB

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
