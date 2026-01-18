"""Configuration for Inky display adapter."""

from dataclasses import dataclass
from pathlib import Path

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
MIN_FONT_SIZE = 14
MAX_FONT_SIZE = 36
FONT_SIZE_STEP = 2
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
TIME_TOGGLE_INTERVAL_SECONDS = 10  # Toggle between absolute/relative every 10 seconds


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
    time_toggle_interval: int = TIME_TOGGLE_INTERVAL_SECONDS
    show_time: bool = False  # Don't show time for now
    fill_vertical_space: bool = True

    @property
    def route_section_width(self) -> int:
        """Width of route icon + number section."""
        return self.padding + self.route_icon_size + self.padding + self.route_number_width

    def destination_section_x(self, icon_size: int | None = None) -> int:
        """X position where destination text starts.
        
        Args:
            icon_size: Icon size to use (if None, uses config.route_icon_size).
        """
        return self.route_section_width(icon_size) + self.padding

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

    def get_route_icon_path(self, transport_type: str) -> Path | None:
        """Get path to route icon SVG file."""
        icon_map = {
            "U-Bahn": "ico-subway.svg",
            "S-Bahn": "ico-metropolitan-railway.svg",
            "Tram": "ico-tram.svg",
            "Bus": "ico-bus.svg",
        }
        icon_name = icon_map.get(transport_type)
        if not icon_name:
            return None

        # Look for icons in parent project's static/assets directory
        parent_project = Path(__file__).parent.parent.parent.parent.parent
        icon_path = parent_project / "static" / "assets" / icon_name
        if icon_path.exists():
            return icon_path
        return None
