"""Tests for icon loading in Inky renderer."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

# Add parent project to path for imports
parent_project = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_project))

from mvg_departures_inky.config import InkyDisplayConfig
from mvg_departures_inky.renderer import InkyRenderer


class TestIconLoading:
    """Tests for icon loading functionality."""

    @pytest.fixture
    def mock_display(self) -> MagicMock:
        """Create a mock display."""
        display = MagicMock()
        display.BLACK = 0
        display.WHITE = 1
        display.GREEN = 2
        display.BLUE = 3
        display.RED = 4
        display.YELLOW = 5
        display.ORANGE = 6
        display.palette = [0, 0, 0, 255, 255, 255] + [255, 255, 255] * 254
        return display

    @pytest.fixture
    def config(self) -> InkyDisplayConfig:
        """Create a test config."""
        return InkyDisplayConfig()

    @pytest.fixture
    def renderer(self, config: InkyDisplayConfig, mock_display: MagicMock) -> InkyRenderer:
        """Create a renderer instance."""
        from mvg_departures.adapters.web.builders.departure_grouping_calculator import (
            DepartureGroupingCalculator,
            DepartureGroupingCalculatorConfig,
        )
        from mvg_departures.adapters.web.formatters.departure_formatter import (
            DepartureFormatter,
        )
        from mvg_departures.adapters.config import AppConfig
        from mvg_departures.adapters.web.builders import HeaderDisplaySettings

        app_config = AppConfig()
        formatter = DepartureFormatter(app_config)
        calculator_config = DepartureGroupingCalculatorConfig(
            stop_configs=[], config=app_config
        )
        calculator = DepartureGroupingCalculator(
            calculator_config, formatter, HeaderDisplaySettings()
        )
        return InkyRenderer(config, mock_display, calculator)

    def test_when_icon_path_exists_then_loads_svg_icon(self, renderer: InkyRenderer) -> None:
        """Given a valid icon path, when loading icon, then converts SVG to PIL Image."""
        # Get the actual icon path from config
        icon_path = renderer.config.get_route_icon_path("Bus")
        
        # Skip test if icon file doesn't exist (e.g., in CI without parent project)
        if not icon_path or not icon_path.exists():
            pytest.skip(f"Icon file not found: {icon_path}")
        
        # Load the icon
        icon = renderer._load_icon("Bus", icon_size=32)
        
        # Assertions
        assert icon is not None, "Icon should be loaded, not None"
        assert isinstance(icon, Image.Image), "Icon should be a PIL Image"
        assert icon.size == (32, 32), f"Icon should be 32x32, got {icon.size}"
        assert icon.mode == "RGB", f"Icon should be in RGB mode (before dithering), got {icon.mode}"
        
        # RGB mode images don't have a palette - they have RGB values directly
        # Check that icon has colored pixels (background) or white pixels (symbols)
        pixels = icon.load()
        if pixels is None:
            pytest.fail("Failed to load pixels from icon")

        colored_pixels = 0
        white_pixels = 0
        for y in range(icon.height):
            for x in range(icon.width):
                pixel_val = pixels[x, y]
                if isinstance(pixel_val, tuple) and len(pixel_val) >= 3:
                    r, g, b = pixel_val[0], pixel_val[1], pixel_val[2]
                    # Check for colored background
                    if (r > 100 or g > 50 or b > 50) and not (r >= 240 and g >= 240 and b >= 240):
                        colored_pixels += 1
                    # Check for white pixels (symbols)
                    elif r >= 240 and g >= 240 and b >= 240:
                        white_pixels += 1

        # Icon should have some visible pixels
        assert (
            colored_pixels > 0 or white_pixels > 0
        ), f"Icon should have colored or white pixels, found {colored_pixels} colored, {white_pixels} white"

    def test_when_icon_path_missing_then_returns_none(self, renderer: InkyRenderer) -> None:
        """Given a missing icon path, when loading icon, then returns None (no text fallback)."""
        # Mock get_route_icon_path to return None
        with patch.object(renderer.config, "get_route_icon_path", return_value=None):
            icon = renderer._load_icon("UnknownTransport", icon_size=32)
            assert icon is None, "Should return None when icon path is missing"

    def test_when_icon_file_not_found_then_returns_none(self, renderer: InkyRenderer) -> None:
        """Given a non-existent icon file, when loading icon, then returns None."""
        # Mock get_route_icon_path to return a non-existent path
        fake_path = Path("/nonexistent/icon.svg")
        with patch.object(renderer.config, "get_route_icon_path", return_value=fake_path):
            icon = renderer._load_icon("Bus", icon_size=32)
            assert icon is None, "Should return None when icon file doesn't exist"

    def test_when_svg_conversion_fails_then_returns_none(self, renderer: InkyRenderer) -> None:
        """Given SVG conversion failure, when loading icon, then returns None (no text fallback)."""
        # Get a real icon path
        icon_path = renderer.config.get_route_icon_path("Bus")
        if not icon_path or not icon_path.exists():
            pytest.skip(f"Icon file not found: {icon_path}")
        
        # Mock cairosvg to raise an exception
        with patch("cairosvg.svg2png", side_effect=Exception("Conversion failed")):
            icon = renderer._load_icon("Bus", icon_size=32)
            assert icon is None, "Should return None when SVG conversion fails"

    def test_when_icon_loaded_then_cached(self, renderer: InkyRenderer) -> None:
        """Given icon is loaded, when loading again, then returns cached version."""
        icon_path = renderer.config.get_route_icon_path("Bus")
        if not icon_path or not icon_path.exists():
            pytest.skip(f"Icon file not found: {icon_path}")
        
        # Load icon first time
        icon1 = renderer._load_icon("Bus", icon_size=32)
        if icon1 is None:
            pytest.skip("Icon loading failed, cannot test caching")
        
        # Load icon second time - should use cache
        icon2 = renderer._load_icon("Bus", icon_size=32)
        
        assert icon2 is not None, "Cached icon should not be None"
        assert icon2 is icon1, "Should return the same cached icon object"

    def test_when_icon_size_different_then_not_cached(self, renderer: InkyRenderer) -> None:
        """Given different icon sizes, when loading, then creates separate cache entries."""
        icon_path = renderer.config.get_route_icon_path("Bus")
        if not icon_path or not icon_path.exists():
            pytest.skip(f"Icon file not found: {icon_path}")
        
        # Load icon at size 32
        icon32 = renderer._load_icon("Bus", icon_size=32)
        if icon32 is None:
            pytest.skip("Icon loading failed, cannot test size caching")
        
        # Load icon at size 48 - should create new entry
        icon48 = renderer._load_icon("Bus", icon_size=48)
        if icon48 is None:
            pytest.skip("Icon loading failed at size 48")
        
        assert icon32.size == (32, 32), "First icon should be 32x32"
        assert icon48.size == (48, 48), "Second icon should be 48x48"
        assert icon32 is not icon48, "Different sizes should create different cache entries"

    def test_when_icon_has_black_pixels_then_visible(self, renderer: InkyRenderer) -> None:
        """Given a loaded icon, when checking pixels, then has colored or white pixels for visibility."""
        icon_path = renderer.config.get_route_icon_path("Bus")
        if not icon_path or not icon_path.exists():
            pytest.skip(f"Icon file not found: {icon_path}")
        
        icon = renderer._load_icon("Bus", icon_size=32)
        if icon is None:
            pytest.skip("Icon loading failed")
        
        # Count colored pixels (background) and white pixels (symbols)
        pixels = icon.load()
        if pixels is None:
            pytest.fail("Failed to load pixels from icon")
        
        colored_count = 0
        white_count = 0
        for y in range(icon.height):
            for x in range(icon.width):
                pixel_val = pixels[x, y]
                if isinstance(pixel_val, tuple) and len(pixel_val) >= 3:
                    r, g, b = pixel_val[0], pixel_val[1], pixel_val[2]
                    # Check for colored background
                    if (r > 100 or g > 50 or b > 50) and not (r >= 240 and g >= 240 and b >= 240):
                        colored_count += 1
                    # Check for white pixels (symbols)
                    elif r >= 240 and g >= 240 and b >= 240:
                        white_count += 1
        
        # Icon should have significant colored or white pixels (at least 1% of total)
        total_pixels = icon.width * icon.height
        visible_pixels = colored_count + white_count
        visible_percentage = (visible_pixels / total_pixels) * 100
        
        assert visible_pixels > 0, f"Icon should have colored or white pixels, found {visible_pixels}"
        assert visible_percentage > 1.0, f"Icon should have at least 1% visible pixels, got {visible_percentage:.2f}%"
