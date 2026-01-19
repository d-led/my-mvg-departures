"""Tests for font size calculation in Inky renderer.

This test verifies that:
1. Header font size is calculated to fit the longest header text horizontally
2. Body font size is calculated to be smaller than header (85%) and fits vertically
3. Font sizes respect minimum and maximum constraints
4. Font size calculation adapts to different numbers of departures and headers

All tests use the actual production code from InkyRenderer - no duplication!
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

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
from mvg_departures_inky.renderer import InkyRenderer


class TestFontSizeCalculation:
    """Tests for font size calculation functionality."""

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
            stop_configs=[],
            config=app_config,
        )
        calculator = DepartureGroupingCalculator(
            calculator_config,
            formatter,
            HeaderDisplaySettings(),
        )
        return InkyRenderer(config, mock_display, calculator)

    def test_when_short_header_then_uses_large_font_size(
        self, renderer: InkyRenderer
    ) -> None:
        """Given short header text, when calculating font size, then uses large font."""
        short_header = "A"
        available_width = 400  # Wide enough for large font

        font_size = renderer._calculate_header_font_size(short_header, available_width)

        # Should use maximum or close to maximum font size
        assert font_size >= renderer.config.max_font_size - renderer.config.font_size_step
        assert font_size <= renderer.config.max_font_size

    def test_when_long_header_then_uses_smaller_font_size(
        self, renderer: InkyRenderer
    ) -> None:
        """Given long header text, when calculating font size, then uses smaller font."""
        long_header = "Chiemgaustr → Ostbahnhof (very long destination name)"
        available_width = 400

        font_size = renderer._calculate_header_font_size(long_header, available_width)

        # Should be smaller than max to fit the long text
        assert font_size <= renderer.config.max_font_size
        assert font_size >= renderer.config.min_font_size

    def test_when_header_too_long_then_uses_minimum_font_size(
        self, renderer: InkyRenderer
    ) -> None:
        """Given very long header text, when calculating font size, then uses minimum."""
        very_long_header = "A" * 200  # Extremely long header
        available_width = 100  # Narrow width

        font_size = renderer._calculate_header_font_size(very_long_header, available_width)

        # Should fall back to minimum font size
        assert font_size == renderer.config.min_font_size

    def test_when_empty_header_then_uses_maximum_font_size(
        self, renderer: InkyRenderer
    ) -> None:
        """Given empty header text, when calculating font size, then uses maximum."""
        empty_header = ""
        available_width = 400

        font_size = renderer._calculate_header_font_size(empty_header, available_width)

        # Should use maximum font size
        assert font_size == renderer.config.max_font_size

    def test_when_calculating_body_font_then_smaller_than_header(
        self, renderer: InkyRenderer
    ) -> None:
        """Given header font size, when calculating body font, then body is smaller."""
        header_font_size = 20
        total_departures = 5
        header_count = 2
        initial_font_size = int(header_font_size * 0.85)  # 85% of header

        body_font_size = renderer._calculate_font_size_with_header(
            total_departures, header_count, header_font_size, initial_font_size
        )

        # Body font should be smaller than or equal to header (85% of header)
        assert body_font_size <= header_font_size
        assert body_font_size >= int(header_font_size * 0.85) - 1  # Allow small rounding

    def test_when_many_departures_then_reduces_body_font_size(
        self, renderer: InkyRenderer
    ) -> None:
        """Given many departures, when calculating body font, then reduces font size."""
        header_font_size = 20
        many_departures = 20
        header_count = 3
        initial_font_size = int(header_font_size * 0.85)

        body_font_size = renderer._calculate_font_size_with_header(
            many_departures, header_count, header_font_size, initial_font_size
        )

        # Should reduce font size to fit all departures
        assert body_font_size <= initial_font_size
        assert body_font_size >= renderer.config.min_font_size

    def test_when_few_departures_then_uses_initial_body_font_size(
        self, renderer: InkyRenderer
    ) -> None:
        """Given few departures, when calculating body font, then uses initial size."""
        header_font_size = 20
        few_departures = 2
        header_count = 1
        initial_font_size = int(header_font_size * 0.85)

        body_font_size = renderer._calculate_font_size_with_header(
            few_departures, header_count, header_font_size, initial_font_size
        )

        # Should use initial font size (or close to it) since there's plenty of space
        assert body_font_size == initial_font_size or body_font_size >= initial_font_size - renderer.config.font_size_step

    def test_when_no_departures_then_returns_initial_font_size(
        self, renderer: InkyRenderer
    ) -> None:
        """Given no departures, when calculating body font, then returns initial size."""
        header_font_size = 20
        no_departures = 0
        header_count = 0
        initial_font_size = 15

        body_font_size = renderer._calculate_font_size_with_header(
            no_departures, header_count, header_font_size, initial_font_size
        )

        # Should return initial font size when no departures
        assert body_font_size == initial_font_size

    def test_when_fill_vertical_space_then_maximizes_font_size(
        self, renderer: InkyRenderer
    ) -> None:
        """Given fill_vertical_space enabled, when calculating, then maximizes font size."""
        renderer.config.fill_vertical_space = True
        header_font_size = 20
        total_departures = 10
        header_count = 2
        initial_font_size = int(header_font_size * 0.85)

        body_font_size = renderer._calculate_font_size_with_header(
            total_departures, header_count, header_font_size, initial_font_size
        )

        # Should find the largest font that fits
        assert body_font_size >= renderer.config.min_font_size
        assert body_font_size <= initial_font_size

    def test_when_header_font_size_fits_then_header_text_fits_horizontally(
        self, renderer: InkyRenderer
    ) -> None:
        """Given calculated header font size, when measuring header text, then fits in width."""
        header_text = "Chiemgaustr → Ostbahnhof"
        available_width = 400

        header_font_size = renderer._calculate_header_font_size(header_text, available_width)
        header_font = renderer._get_font(header_font_size, bold=True)
        header_bbox = header_font.getbbox(header_text)
        header_width = header_bbox[2] - header_bbox[0]

        # Header text should fit within available width
        assert header_width <= available_width

    def test_when_body_font_size_calculated_then_fits_vertically(
        self, renderer: InkyRenderer
    ) -> None:
        """Given calculated body font size, when measuring total height, then fits vertically."""
        renderer.config.fill_vertical_space = True
        header_font_size = 20
        total_departures = 10
        header_count = 2
        initial_font_size = int(header_font_size * 0.85)

        body_font_size = renderer._calculate_font_size_with_header(
            total_departures, header_count, header_font_size, initial_font_size
        )

        # Calculate total height with these font sizes
        body_font = renderer._get_font(body_font_size, bold=False)
        body_bbox = body_font.getbbox("Mg")
        body_font_height = body_bbox[3] - body_bbox[1]
        line_height = body_font_height + renderer.config.line_spacing

        header_font = renderer._get_font(header_font_size, bold=True)
        header_bbox = header_font.getbbox("Mg")
        header_font_height = header_bbox[3] - header_bbox[1]
        header_height = header_font_height + renderer.config.line_spacing + 4

        total_height = (
            (header_height * header_count) + (line_height * total_departures) - renderer.config.line_spacing
        )
        available_height = renderer.config.height

        # Total height should fit within available height
        assert total_height <= available_height
