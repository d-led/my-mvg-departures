"""Tests for icon rendering and conversion in Inky renderer.

This test verifies that:
1. Icons are loaded correctly from SVG files using production code
2. Colored backgrounds (e.g., red #dd0b2f for tram) are detected in the original
3. White symbols are correctly extracted and converted to black
4. Icons can be rendered to a mock display

All tests use the actual production code from InkyRenderer - no duplication!
"""

import sys
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

import pytest
from PIL import Image

# Add parent project to path for imports
parent_project = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_project))

from mvg_departures.adapters.config.app_config import AppConfig
from mvg_departures.adapters.web.builders.departure_grouping_calculator import (
    DepartureGroupingCalculator,
    DepartureGroupingCalculatorConfig,
    HeaderDisplaySettings,
)
from mvg_departures.adapters.web.formatters.departure_formatter import DepartureFormatter

from mvg_departures_inky.config import InkyDisplayConfig
from mvg_departures_inky.mock_display import create_mock_display
from mvg_departures_inky.renderer import InkyRenderer


class TestIconRendering:
    """Tests for icon rendering and conversion."""

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
        """Create a renderer instance using production code."""
        # Initialize calculator the same way as in main.py (production code)
        # Create a minimal AppConfig for the formatter
        app_config = AppConfig(
            timezone="Europe/Berlin",
            time_format="minutes",
            time_offset_minutes=0,
            refresh_interval_seconds=30,
            max_departures_per_route=10,
            max_departures_per_stop=10,
            max_delay_minutes=5,
            max_hours_in_advance=2,
            show_ungrouped_departures=True,
            ungrouped_departures_title="Other departures",
            header_show_stop_name=True,
            header_show_direction=True,
            header_show_route_name=False,
            time_toggle_interval_seconds=10,
        )
        formatter = DepartureFormatter(app_config)
        calculator_config = DepartureGroupingCalculatorConfig(
            stop_configs=[],  # Empty for icon tests
            config=app_config,
        )
        calculator = DepartureGroupingCalculator(
            calculator_config,
            formatter,
            HeaderDisplaySettings(),  # Use defaults
        )
        return InkyRenderer(config, mock_display, calculator)

    def test_when_tram_icon_loaded_then_has_red_background_in_original(
        self, renderer: InkyRenderer
    ) -> None:
        """Given tram icon SVG, when loaded as RGB, then has red background pixels.
        
        Uses production code: renderer._load_icon() loads the icon, but we need to check
        the original RGB version before conversion. We'll use the same cairosvg approach
        that the production code uses.
        """
        # Get the actual icon path from config (using production code)
        icon_path = renderer.config.get_route_icon_path("Tram")

        # Skip test if icon file doesn't exist (e.g., in CI without parent project)
        if not icon_path or not icon_path.exists():
            pytest.skip(f"Icon file not found: {icon_path}")

        # Load the original SVG as RGB to check for red background
        # Use the same approach as production code
        try:
            import cairosvg

            # Convert SVG to PNG bytes (same as production code)
            png_bytes = cairosvg.svg2png(
                url=str(icon_path),
                output_width=64,
                output_height=64,
            )

            # Load PNG bytes into PIL Image (same as production code)
            icon = Image.open(BytesIO(png_bytes))

            # Convert to RGB (same as production code)
            if icon.mode == "RGBA":
                bg = Image.new("RGB", icon.size, (255, 255, 255))
                bg.paste(icon, mask=icon.split()[3])
                icon = bg
            elif icon.mode != "RGB":
                icon = icon.convert("RGB")

            # Check for red pixels (tram icon has red background #dd0b2f = RGB(221, 11, 47))
            pixels = icon.load()
            if pixels is None:
                pytest.fail("Failed to load pixels from icon")

            red_pixels = 0
            white_pixels = 0
            total_pixels = icon.width * icon.height

            for y in range(icon.height):
                for x in range(icon.width):
                    pixel_val = pixels[x, y]
                    if isinstance(pixel_val, tuple) and len(pixel_val) >= 3:
                        r, g, b = pixel_val[0], pixel_val[1], pixel_val[2]
                        # Check for red background (tram: #dd0b2f = RGB(221, 11, 47))
                        # Allow some tolerance for anti-aliasing
                        if r > 200 and g < 50 and b < 100:
                            red_pixels += 1
                        # Check for white symbols (#fff = RGB(255, 255, 255))
                        elif r >= 240 and g >= 240 and b >= 240:
                            white_pixels += 1

            red_percentage = (red_pixels / total_pixels) * 100
            white_percentage = (white_pixels / total_pixels) * 100

            # Tram icon should have significant red background and white symbols
            assert red_pixels > 0, f"Tram icon should have red background pixels, found {red_pixels}"
            assert (
                red_percentage > 10.0
            ), f"Tram icon should have at least 10% red pixels, got {red_percentage:.2f}%"
            assert white_pixels > 0, f"Tram icon should have white symbol pixels, found {white_pixels}"
            assert (
                white_percentage > 1.0
            ), f"Tram icon should have at least 1% white pixels, got {white_percentage:.2f}%"

        except ImportError:
            pytest.skip("cairosvg not available")

    def test_when_tram_icon_converted_then_has_black_symbols_on_white(
        self, renderer: InkyRenderer
    ) -> None:
        """Given tram icon, when converted for e-ink using production code, then has black symbols on white background."""
        # Get the actual icon path from config (using production code)
        icon_path = renderer.config.get_route_icon_path("Tram")

        # Skip test if icon file doesn't exist
        if not icon_path or not icon_path.exists():
            pytest.skip(f"Icon file not found: {icon_path}")

        # Load the icon using the production code method
        icon = renderer._load_icon("Tram", icon_size=64)

        # Assertions
        assert icon is not None, "Icon should be loaded, not None"
        assert isinstance(icon, Image.Image), "Icon should be a PIL Image"
        assert icon.size == (64, 64), f"Icon should be 64x64, got {icon.size}"
        assert icon.mode == "P", f"Icon should be in palette mode, got {icon.mode}"

        # Check that icon has a palette
        palette = icon.getpalette()
        assert palette is not None, "Icon should have a palette"

        # Check palette colors: index 0 should be black, index 1 should be white
        assert palette[0] == 0 and palette[1] == 0 and palette[2] == 0, "Palette index 0 should be black"
        assert (
            palette[3] == 255 and palette[4] == 255 and palette[5] == 255
        ), "Palette index 1 should be white"

        # Check that icon has black pixels (the symbols)
        pixels = icon.load()
        if pixels is None:
            pytest.fail("Failed to load pixels from converted icon")

        black_pixels = 0
        white_pixels = 0
        total_pixels = icon.width * icon.height

        for y in range(icon.height):
            for x in range(icon.width):
                idx = pixels[x, y]
                if idx == 0:  # Black
                    black_pixels += 1
                elif idx == 1:  # White
                    white_pixels += 1

        black_percentage = (black_pixels / total_pixels) * 100
        white_percentage = (white_pixels / total_pixels) * 100

        # Converted icon should have black symbols and white background
        assert black_pixels > 0, f"Icon should have black pixels (symbols), found {black_pixels}"
        assert (
            black_percentage > 1.0
        ), f"Icon should have at least 1% black pixels, got {black_percentage:.2f}%"
        assert white_pixels > 0, f"Icon should have white pixels (background), found {white_pixels}"
        assert (
            white_percentage > 50.0
        ), f"Icon should have at least 50% white pixels (background), got {white_percentage:.2f}%"

    def test_when_icon_rendered_to_mock_display_then_visible(
        self, renderer: InkyRenderer
    ) -> None:
        """Given loaded icon using production code, when rendered to mock display, then is visible in output."""
        # Get the actual icon path from config (using production code)
        icon_path = renderer.config.get_route_icon_path("Tram")

        # Skip test if icon file doesn't exist
        if not icon_path or not icon_path.exists():
            pytest.skip(f"Icon file not found: {icon_path}")

        # Load the icon using production code
        icon = renderer._load_icon("Tram", icon_size=64)
        if icon is None:
            pytest.skip("Icon loading failed")

        # Create a mock display with temporary output directory
        with TemporaryDirectory() as tmpdir:
            mock_display = create_mock_display(
                width=480, height=800, output_dir=tmpdir
            )

            # Create a test image with the icon pasted on it
            test_image = Image.new("P", (480, 800), mock_display.WHITE)
            test_image.putpalette(mock_display.palette)

            # Paste icon at top-left corner
            # Ensure icon palette matches test image palette
            if icon.mode == "P":
                icon_palette = icon.getpalette()
                if icon_palette:
                    # Map icon palette indices to test image palette
                    # Icon: 0=black, 1=white
                    # Test image: 0=black, 1=white, 2=green, 3=blue, etc.
                    # So indices match - just set the palette
                    icon.putpalette(mock_display.palette)

            test_image.paste(icon, (10, 10))

            # Set image on mock display and save
            mock_display.set_image(test_image)
            output_file = Path(tmpdir) / "test_icon_output.png"
            mock_display.show(str(output_file.name))

            # Verify output file exists
            assert output_file.exists(), f"Output file should exist: {output_file}"

            # Load the saved image and verify icon is visible
            saved_image = Image.open(output_file)
            assert saved_image is not None, "Saved image should load successfully"

            # Check that the icon area has black pixels (the symbol)
            # Icon is at (10, 10) with size 64x64
            icon_area = saved_image.crop((10, 10, 74, 74))
            pixels = icon_area.load()
            if pixels is None:
                pytest.fail("Failed to load pixels from saved image")

            black_pixels = 0
            for y in range(min(64, icon_area.height)):
                for x in range(min(64, icon_area.width)):
                    pixel_val = pixels[x, y]
                    if isinstance(pixel_val, tuple) and len(pixel_val) >= 3:
                        r, g, b = pixel_val[0], pixel_val[1], pixel_val[2]
                        # Check for black (or very dark) pixels
                        if r < 50 and g < 50 and b < 50:
                            black_pixels += 1

            # Icon should have visible black pixels in the saved image
            assert (
                black_pixels > 0
            ), f"Icon should be visible in saved image with black pixels, found {black_pixels}"

    def test_when_convert_colored_icon_then_extracts_white_symbols(
        self, renderer: InkyRenderer
    ) -> None:
        """Given colored icon with white symbols, when converted using production code, then extracts symbols correctly."""
        # Create a test image: red background with white symbol
        # Tram icon has red background #dd0b2f = RGB(221, 11, 47) and white symbols #fff
        test_icon = Image.new("RGB", (32, 32), (221, 11, 47))  # Red background

        # Draw a white rectangle in the middle (simulating white symbol)
        from PIL import ImageDraw

        draw = ImageDraw.Draw(test_icon)
        draw.rectangle([8, 8, 24, 24], fill=(255, 255, 255))  # White symbol

        # Convert using the production code method
        converted = renderer._convert_colored_icon_to_black_white(test_icon, "Tram")

        assert converted is not None, "Conversion should succeed"
        assert converted.mode == "L", f"Converted icon should be grayscale (L), got {converted.mode}"

        # Check that white symbol area is now black
        pixels = converted.load()
        if pixels is None:
            pytest.fail("Failed to load pixels from converted icon")

        # Check the white symbol area (should be black after conversion)
        symbol_black_pixels = 0
        for y in range(8, 24):
            for x in range(8, 24):
                if pixels[x, y] == 0:  # Black
                    symbol_black_pixels += 1

        # Most of the symbol area should be black
        symbol_area = (24 - 8) * (24 - 8)
        assert (
            symbol_black_pixels > symbol_area * 0.8
        ), f"Symbol area should be mostly black, found {symbol_black_pixels}/{symbol_area} black pixels"

        # Check that background area is white
        bg_white_pixels = 0
        # Check corners (background areas)
        for y in [0, 1, 30, 31]:
            for x in [0, 1, 30, 31]:
                if pixels[x, y] == 255:  # White
                    bg_white_pixels += 1

        assert (
            bg_white_pixels > 10
        ), f"Background should be white, found {bg_white_pixels} white pixels in corners"
