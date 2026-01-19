"""Configuration for Inky display adapter."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]  # Fallback for older Python (optional)

logger = logging.getLogger(__name__)

# Inky Impression 7.5" resolution (portrait mode)
INKY_7_5_WIDTH = 480
INKY_7_5_HEIGHT = 800

# Layout constants (optimized for portrait mode)
PADDING = 8
ROUTE_ICON_SIZE = 32  # Base size, will be calculated dynamically
ROUTE_ICON_MIN_SIZE = 24  # Minimum icon size
ROUTE_ICON_MAX_SIZE = 48  # Maximum icon size
ROUTE_ICON_SPACING = 6  # Spacing between icon and route number
ROUTE_NUMBER_WIDTH = 50
PLATFORM_WIDTH = 60
MIN_FONT_SIZE = 6  # Minimum font size for very small displays or many departures
MAX_FONT_SIZE = 36
FONT_SIZE_STEP = 1  # Smaller step for finer font size control
LINE_SPACING = 4

# Colors for Inky Impression Spectra (7 colors)
# Order: black, white, green, blue, red, yellow, orange
BLACK = 0
WHITE = 1
GREEN = 2
BLUE = 3
RED = 4
YELLOW = 5
ORANGE = 6

# Time display settings
TIME_MODE_RELATIVE = "relative"  # Always show relative time (e.g., "5m")
TIME_MODE_ABSOLUTE = "absolute"  # Always show absolute time (e.g., "14:30")

# Fonts are hardcoded:
# - Headers: HK Grotesk Bold
# - Routes: Fredoka One

# Font scaling when filling vertical space
FONT_SCALING_FACTOR_WHEN_FILLING = (
    0.8  # Scale body fonts by this factor (fill_vertical_space is always enabled for Inky)
)

# Default refresh interval for Inky displays (in seconds)
# E-ink displays update slower than web displays, so a longer interval is often preferred
DEFAULT_REFRESH_INTERVAL_SECONDS = 60  # 1 minute default for e-ink displays


@dataclass
class InkyDisplayConfig:
    """Configuration for Inky display rendering."""

    width: int = INKY_7_5_WIDTH
    height: int = INKY_7_5_HEIGHT
    padding: int = PADDING
    route_icon_size: int = ROUTE_ICON_SIZE  # Base size, will be calculated dynamically
    route_icon_min_size: int = ROUTE_ICON_MIN_SIZE
    route_icon_max_size: int = ROUTE_ICON_MAX_SIZE
    route_icon_spacing: int = ROUTE_ICON_SPACING
    route_number_width: int = ROUTE_NUMBER_WIDTH
    platform_width: int = PLATFORM_WIDTH
    min_font_size: int = MIN_FONT_SIZE
    max_font_size: int = MAX_FONT_SIZE
    font_size_step: int = FONT_SIZE_STEP
    line_spacing: int = LINE_SPACING
    time_mode: str = TIME_MODE_ABSOLUTE  # "relative" or "absolute"
    # Note: fill_vertical_space is always True for Inky displays (not configurable)
    # E-ink displays don't have pagination/scrolling, so we always fill the available space
    # Fonts are hardcoded: HK Grotesk Bold for headers, Fredoka One for routes
    font_scaling_factor_when_filling: float = (
        FONT_SCALING_FACTOR_WHEN_FILLING  # Scale body fonts by this factor (only affects route fonts, not headers)
    )
    # Dithering settings
    dithering_enabled: bool = (
        True  # Enable dithering for better color representation (disable for faster rendering)
    )
    # Refresh interval (in seconds) - separate from web version
    # E-ink displays update slower, so a longer interval is often preferred
    refresh_interval_seconds: int = DEFAULT_REFRESH_INTERVAL_SECONDS
    # Landscape mode: if True, render in landscape orientation (width > height)
    # If False (default), render in portrait orientation (height > width)
    # The rendered image will be rotated if needed to match hardware orientation
    landscape_mode: bool = False

    @property
    def route_section_width(self) -> int:
        """Width of route icon + number section."""
        return self.padding + self.route_icon_size + self.padding + self.route_number_width

    def destination_section_x(self, icon_size: int | None = None) -> int:
        """X position where destination text starts.

        Args:
            icon_size: Icon size to use (if None, uses config.route_icon_size).
        """
        # Use provided icon_size or fall back to config
        effective_icon_size = icon_size if icon_size is not None else self.route_icon_size
        return (
            self.padding
            + effective_icon_size
            + self.route_icon_spacing
            + self.route_number_width
            + self.padding
        )

    def destination_section_width(self, icon_size: int | None = None) -> int:
        """Available width for destination text.

        Args:
            icon_size: Icon size to use (if None, uses config.route_icon_size).
        """
        return (
            self.width
            - self.destination_section_x(icon_size)
            - self.platform_width
            - self.padding
            - self.padding
        )

    @property
    def platform_section_x(self) -> int:
        """X position where platform text starts."""
        return self.width - self.padding - self.platform_width

    @property
    def usable_height(self) -> int:
        """Usable vertical space (excluding padding)."""
        return self.height - 2 * self.padding

    def get_fonts_directory(self) -> Path:
        """Get path to fonts directory.

        Returns:
            Path to fonts directory (inky/fonts).
        """
        # Path structure: inky/src/mvg_departures_inky/config.py
        # Need to go up 3 levels: config.py -> mvg_departures_inky -> src -> inky
        inky_root = Path(__file__).parent.parent.parent
        return inky_root / "fonts"

    def get_hk_grotesk_font_path(self, bold: bool = False) -> Path | None:
        """Get path to HK Grotesk font file.

        Args:
            bold: Whether to get Bold variant (True) or Regular variant (False).

        Returns:
            Path to font file, or None if not found.
        """
        fonts_dir = self.get_fonts_directory()
        font_name = "HKGrotesk-Bold.ttf" if bold else "HKGrotesk-Regular.ttf"
        font_path = fonts_dir / font_name
        if font_path.exists():
            return font_path
        return None

    @classmethod
    def from_toml(
        cls,
        config_file: str | None = None,
        route_path: str | None = None,
    ) -> "InkyDisplayConfig":
        """Create InkyDisplayConfig from TOML configuration.

        Args:
            config_file: Path to TOML config file. If None, uses defaults.
            route_path: Optional route path to read route-specific inky settings.

        Returns:
            InkyDisplayConfig instance with values from TOML or defaults.
        """
        # Start with defaults
        inky_settings: dict[str, Any] = {}

        # Load from [inky] section in TOML if config_file is provided
        if config_file:
            try:
                config_path = Path(config_file)
                if config_path.exists():
                    with open(config_path, "rb") as f:
                        toml_data = tomllib.load(f)
                        # Load global [inky] section
                        if "inky" in toml_data and isinstance(toml_data["inky"], dict):
                            inky_settings = toml_data["inky"].copy()
                            # Convert legacy show_time to time_mode if present
                            if "show_time" in inky_settings and "time_mode" not in inky_settings:
                                if inky_settings["show_time"]:
                                    inky_settings["time_mode"] = TIME_MODE_RELATIVE
                                else:
                                    inky_settings["time_mode"] = TIME_MODE_ABSOLUTE
                                # Remove show_time to avoid confusion
                                del inky_settings["show_time"]
                            logger.debug(
                                f"Loaded inky settings from [inky] section: {inky_settings}"
                            )

                        # Load route-specific inky settings from [[routes.display]] section
                        if route_path and "routes" in toml_data:
                            routes = toml_data["routes"]
                            if isinstance(routes, list):
                                for route in routes:
                                    if isinstance(route, dict) and route.get("path") == route_path:
                                        display = route.get("display")
                                        if isinstance(display, dict):
                                            # Route-specific inky settings override global [inky] section
                                            if "time_mode" in display:
                                                inky_settings["time_mode"] = display["time_mode"]
                                            elif "show_time" in display:
                                                # Legacy support: convert show_time bool to time_mode
                                                if display["show_time"]:
                                                    inky_settings["time_mode"] = TIME_MODE_RELATIVE
                                                else:
                                                    inky_settings["time_mode"] = TIME_MODE_ABSOLUTE
                                            if "font_scaling_factor_when_filling" in display:
                                                inky_settings[
                                                    "font_scaling_factor_when_filling"
                                                ] = display["font_scaling_factor_when_filling"]
                                            if "refresh_interval_seconds" in display:
                                                inky_settings["refresh_interval_seconds"] = int(
                                                    display["refresh_interval_seconds"]
                                                )
                                            if "landscape_mode" in display:
                                                inky_settings["landscape_mode"] = bool(
                                                    display["landscape_mode"]
                                                )
                                            logger.debug(
                                                f"Loaded route-specific inky settings for '{route_path}': {inky_settings}"
                                            )
                                        break
            except Exception as e:
                logger.warning(f"Failed to load inky settings from TOML: {e}, using defaults")

        # Note: fill_vertical_space is always True for Inky displays (not configurable)
        # E-ink displays don't have pagination/scrolling, so we always fill the available space

        # Create config with TOML values or defaults
        # Fonts are hardcoded: HK Grotesk Bold for headers, Fredoka One for routes
        return cls(
            time_mode=inky_settings.get("time_mode", TIME_MODE_ABSOLUTE),
            font_scaling_factor_when_filling=inky_settings.get(
                "font_scaling_factor_when_filling", FONT_SCALING_FACTOR_WHEN_FILLING
            ),
            dithering_enabled=inky_settings.get("dithering_enabled", True),
            refresh_interval_seconds=int(
                inky_settings.get("refresh_interval_seconds", DEFAULT_REFRESH_INTERVAL_SECONDS)
            ),
            landscape_mode=inky_settings.get("landscape_mode", False),
        )

    def get_route_icon_path(self, transport_type: str) -> Path | None:
        """Get path to route icon SVG file."""
        icon_map = {
            "U-Bahn": "ico-subway.svg",
            "S-Bahn": "ico-metropolitan-railway.svg",
            "Tram": "ico-tram.svg",
            "Bus": "ico-bus.svg",
            "Regionalbus": "ico-bus.svg",  # Map Regionalbus to bus icon
        }
        icon_name = icon_map.get(transport_type)
        if not icon_name:
            logger.debug(
                f"Transport type '{transport_type}' not in icon_map. Available keys: {list(icon_map.keys())}"
            )
            return None

        # Look for icons in parent project's static/assets directory
        # Path structure: inky/src/mvg_departures_inky/config.py
        # Need to go up 4 levels: config.py -> mvg_departures_inky -> src -> inky -> project root
        parent_project = Path(__file__).parent.parent.parent.parent
        icon_path = parent_project / "static" / "assets" / icon_name
        logger.debug(f"Looking for icon: {icon_path} (exists: {icon_path.exists()})")
        if icon_path.exists():
            return icon_path
        logger.warning(f"Icon file not found: {icon_path}")
        return None
