"""Tests for color rendering in Inky renderer.

This test verifies that:
1. Headers are rendered in blue color
2. Realtime departure times are rendered in green color
3. Colors are properly dithered to the 7-color palette
4. The dithered image uses the correct palette indices
"""

import sys
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
from mvg_departures.domain.models.direction_group_with_metadata import (
    DirectionGroupWithMetadata,
)
from mvg_departures.domain.models.departure import Departure

from mvg_departures_inky.config import InkyDisplayConfig
from mvg_departures_inky.mock_display import create_mock_display
from mvg_departures_inky.renderer import InkyRenderer


class TestColorRendering:
    """Tests for color rendering functionality."""

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
            stop_configs=[],  # Empty for color tests
            config=app_config,
        )
        calculator = DepartureGroupingCalculator(
            calculator_config,
            formatter,
            HeaderDisplaySettings(),  # Use defaults
        )
        return InkyRenderer(config, mock_display, calculator)

    def test_when_header_rendered_then_uses_blue_color(
        self, renderer: InkyRenderer
    ) -> None:
        """Given departures with headers, when rendered, then headers use blue color."""
        # Create test data with a header
        from datetime import UTC, datetime, timedelta

        now = datetime.now(UTC)
        departure = Departure(
            station_id="de:09162:70",
            line="U2",
            destination="Messestadt Ost",
            time=now + timedelta(minutes=5),
            platform="1",
            transport_type="U-Bahn",
            is_realtime=True,
        )

        direction_group = DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Giesing",
            direction_name="Messestadt Ost",
            departures=[departure],
            random_header_colors=False,
            header_background_brightness=0.7,
            random_color_salt=0,
        )

        # Render the departures
        img = renderer.render([direction_group])

        # Verify image is in palette mode (dithered)
        assert img.mode == "P", f"Image should be in palette mode after dithering, got {img.mode}"

        # Get the palette
        palette = img.getpalette()
        assert palette is not None, "Image should have a palette"

        # Find header area (top of image, full width)
        # Headers are typically around 30-40 pixels high
        header_height = 40
        pixels = img.load()
        if pixels is None:
            pytest.fail("Failed to load pixels from rendered image")

        # Count blue pixels in header area (palette index 3 = blue)
        blue_pixels = 0
        total_header_pixels = 0

        for y in range(min(header_height, img.height)):
            for x in range(img.width):
                idx = pixels[x, y]
                if isinstance(idx, int):
                    total_header_pixels += 1
                    if idx == 3:  # Blue palette index
                        blue_pixels += 1

        blue_percentage = (blue_pixels / total_header_pixels) * 100 if total_header_pixels > 0 else 0

        # Header should have significant blue pixels (at least 10% due to dithering)
        assert (
            blue_pixels > 0
        ), f"Header should have blue pixels, found {blue_pixels} out of {total_header_pixels}"
        assert (
            blue_percentage > 10.0
        ), f"Header should have at least 10% blue pixels (dithered), got {blue_percentage:.2f}%"

    def test_when_realtime_departure_rendered_then_time_is_green(
        self, renderer: InkyRenderer
    ) -> None:
        """Given realtime departure, when rendered, then time is green."""
        # Create test data with realtime departure
        from datetime import UTC, datetime, timedelta

        now = datetime.now(UTC)
        departure = Departure(
            station_id="de:09162:70",
            line="U2",
            destination="Messestadt Ost",
            time=now + timedelta(minutes=5),
            platform="1",
            transport_type="U-Bahn",
            is_realtime=True,  # Realtime!
        )

        direction_group = DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Giesing",
            direction_name="Messestadt Ost",
            departures=[departure],
            random_header_colors=False,
            header_background_brightness=0.7,
            random_color_salt=0,
        )

        # Render the departures
        img = renderer.render([direction_group])

        # Verify image is in palette mode (dithered)
        assert img.mode == "P", f"Image should be in palette mode after dithering, got {img.mode}"

        # Get the palette
        palette = img.getpalette()
        assert palette is not None, "Image should have a palette"

        # Find time area (right side of image, after header)
        # Time is typically on the right side, in the last 100 pixels
        pixels = img.load()
        if pixels is None:
            pytest.fail("Failed to load pixels from rendered image")

        # Skip header (first 40 pixels)
        header_height = 40
        time_area_x_start = img.width - 100
        time_area_y_start = header_height
        time_area_y_end = min(header_height + 50, img.height)  # Check first departure row

        # Count green pixels in time area (palette index 2 = green)
        green_pixels = 0
        total_time_pixels = 0

        for y in range(time_area_y_start, time_area_y_end):
            for x in range(time_area_x_start, img.width):
                idx = pixels[x, y]
                if isinstance(idx, int):
                    total_time_pixels += 1
                    if idx == 2:  # Green palette index
                        green_pixels += 1

        green_percentage = (green_pixels / total_time_pixels) * 100 if total_time_pixels > 0 else 0

        # Time should have some green pixels (due to dithering, might not be 100%)
        # But for realtime departures, we should see green
        assert (
            green_pixels > 0
        ), f"Realtime time should have green pixels, found {green_pixels} out of {total_time_pixels}"

    def test_when_image_dithered_then_uses_correct_palette_indices(
        self, renderer: InkyRenderer
    ) -> None:
        """Given RGB image, when dithered, then uses only 7-color palette indices."""
        # Create a simple RGB image with colors
        rgb_img = Image.new("RGB", (100, 100), (255, 255, 255))
        from PIL import ImageDraw

        draw = ImageDraw.Draw(rgb_img)
        # Draw blue rectangle (header color)
        draw.rectangle([0, 0, 50, 50], fill=(8, 123, 196))  # Blue
        # Draw green rectangle (realtime color)
        draw.rectangle([50, 0, 100, 50], fill=(4, 120, 87))  # Green
        # Draw black text
        draw.rectangle([0, 50, 100, 100], fill=(0, 0, 0))  # Black

        # Dither the image
        dithered = renderer._dither_image_to_palette(rgb_img)

        # Verify it's in palette mode
        assert dithered.mode == "P", f"Dithered image should be in palette mode, got {dithered.mode}"

        # Get palette
        palette = dithered.getpalette()
        assert palette is not None, "Dithered image should have a palette"

        # Check that only valid palette indices (0-6) are used
        pixels = dithered.load()
        if pixels is None:
            pytest.fail("Failed to load pixels from dithered image")

        used_indices: set[int] = set()
        for y in range(dithered.height):
            for x in range(dithered.width):
                idx = pixels[x, y]
                if isinstance(idx, int):
                    used_indices.add(idx)

        # Should only use indices 0-6 (7 colors)
        invalid_indices = {idx for idx in used_indices if idx < 0 or idx > 6}
        assert (
            len(invalid_indices) == 0
        ), f"Dithered image should only use palette indices 0-6, found: {invalid_indices}"

        # Should use at least some colors (not just white/black)
        color_indices = {idx for idx in used_indices if idx > 1}  # Exclude black (0) and white (1)
        assert (
            len(color_indices) > 0
        ), f"Dithered image should use some color indices (2-6), only found: {used_indices}"

    def test_when_rendered_to_mock_display_then_colors_visible(
        self, renderer: InkyRenderer
    ) -> None:
        """Given rendered image with colors, when saved to mock display, then colors are visible."""
        # Create test data
        from datetime import UTC, datetime, timedelta

        now = datetime.now(UTC)
        departure = Departure(
            station_id="de:09162:70",
            line="U2",
            destination="Messestadt Ost",
            time=now + timedelta(minutes=5),
            platform="1",
            transport_type="U-Bahn",
            is_realtime=True,
        )

        direction_group = DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Giesing",
            direction_name="Messestadt Ost",
            departures=[departure],
            random_header_colors=False,
            header_background_brightness=0.7,
            random_color_salt=0,
        )

        # Render
        img = renderer.render([direction_group])

        # Create mock display and save
        with TemporaryDirectory() as tmpdir:
            mock_display = create_mock_display(width=480, height=800, output_dir=tmpdir)
            mock_display.set_image(img)
            output_file = Path(tmpdir) / "test_color_output.png"
            mock_display.show(str(output_file.name))

            # Verify output file exists
            assert output_file.exists(), f"Output file should exist: {output_file}"

            # Load the saved image and verify colors
            saved_image = Image.open(output_file)
            assert saved_image.mode == "RGB", f"Saved image should be RGB, got {saved_image.mode}"

            # Check for blue in header area
            pixels = saved_image.load()
            if pixels is None:
                pytest.fail("Failed to load pixels from saved image")

            # Check header area for blue pixels
            blue_found = False
            for y in range(min(40, saved_image.height)):
                for x in range(saved_image.width):
                    pixel = pixels[x, y]
                    if isinstance(pixel, tuple) and len(pixel) >= 3:
                        r, g, b = pixel[0], pixel[1], pixel[2]
                        # Check for blue-ish color (blue channel should be highest)
                        if b > r and b > g and b > 100:
                            blue_found = True
                            break
                if blue_found:
                    break

            assert blue_found, "Header should contain blue pixels in saved image"
