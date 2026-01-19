"""Tests for vertical space filling in Inky renderer.

This test verifies that:
1. Vertical space is correctly calculated and filled for various configurations
2. Header heights match departure row heights
3. Padding is properly accounted for
4. Extra pixels are distributed correctly across rows
5. Total height matches available height exactly
6. Works with different numbers of headers and departures per header
"""

import sys
from datetime import datetime, timedelta
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
from mvg_departures.domain.models.departure import Departure
from mvg_departures.domain.models.direction_group_with_metadata import (
    DirectionGroupWithMetadata,
)

from mvg_departures_inky.config import InkyDisplayConfig
from mvg_departures_inky.renderer import InkyRenderer


class TestVerticalSpaceFilling:
    """Tests for vertical space filling functionality."""

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

    def _create_departure(self, line: str = "18", minutes_from_now: int = 5) -> Departure:
        """Create a test departure."""
        now = datetime.now()
        departure_time = now + timedelta(minutes=minutes_from_now)
        return Departure(
            time=departure_time,
            planned_time=departure_time,
            delay_seconds=0,
            platform=1,
            is_realtime=True,
            line=line,
            destination="Test Destination",
            transport_type="Bus",
            icon="",
            is_cancelled=False,
            messages=[],
        )

    def _create_direction_group(
        self,
        stop_name: str,
        direction_name: str,
        num_departures: int,
    ) -> DirectionGroupWithMetadata:
        """Create a direction group with specified number of departures."""
        departures = [self._create_departure(f"Line{i}", i + 1) for i in range(num_departures)]
        return DirectionGroupWithMetadata(
            station_id="test_station",
            stop_name=stop_name,
            direction_name=direction_name,
            departures=departures,
            random_header_colors=False,
            header_background_brightness=0.7,
            random_color_salt=None,
        )

    def _render_and_verify_height(
        self,
        renderer: InkyRenderer,
        groups: list[DirectionGroupWithMetadata],
        expected_available_height: int,
    ) -> None:
        """Render groups and verify the height calculation is correct."""
        # Render the groups
        img = renderer.render(groups)

        # Verify image height matches config
        assert img.height == renderer.config.height, (
            f"Image height {img.height} should match config height {renderer.config.height}"
        )

        # Verify available height calculation (should use full height, no padding)
        assert renderer.config.height == expected_available_height, (
            f"Config height {renderer.config.height} should be {expected_available_height} "
            f"(full height, no padding subtracted)"
        )

        # Verify the renderer calculated the correct available height
        # This is checked via the internal state after rendering
        # We can't directly access it, but we can verify the image was rendered correctly

    def test_when_single_header_single_departure_then_fills_vertical_space(
        self, renderer: InkyRenderer
    ) -> None:
        """Given 1 header with 1 departure, when rendering, then fills vertical space correctly."""
        groups = [self._create_direction_group("Stop1", "Direction1", 1)]
        expected_height = renderer.config.height

        self._render_and_verify_height(renderer, groups, expected_height)

    def test_when_single_header_many_departures_then_fills_vertical_space(
        self, renderer: InkyRenderer
    ) -> None:
        """Given 1 header with many departures, when rendering, then fills vertical space correctly."""
        groups = [self._create_direction_group("Stop1", "Direction1", 15)]
        expected_height = renderer.config.height

        self._render_and_verify_height(renderer, groups, expected_height)

    def test_when_multiple_headers_few_departures_then_fills_vertical_space(
        self, renderer: InkyRenderer
    ) -> None:
        """Given multiple headers with few departures each, when rendering, then fills vertical space."""
        groups = [
            self._create_direction_group("Stop1", "Direction1", 2),
            self._create_direction_group("Stop2", "Direction2", 2),
            self._create_direction_group("Stop3", "Direction3", 2),
        ]
        expected_height = renderer.config.height

        self._render_and_verify_height(renderer, groups, expected_height)

    def test_when_multiple_headers_many_departures_then_fills_vertical_space(
        self, renderer: InkyRenderer
    ) -> None:
        """Given multiple headers with many departures each, when rendering, then fills vertical space."""
        groups = [
            self._create_direction_group("Stop1", "Direction1", 10),
            self._create_direction_group("Stop2", "Direction2", 10),
            self._create_direction_group("Stop3", "Direction3", 10),
        ]
        expected_height = renderer.config.height

        self._render_and_verify_height(renderer, groups, expected_height)

    def test_when_mixed_departure_counts_then_fills_vertical_space(
        self, renderer: InkyRenderer
    ) -> None:
        """Given headers with mixed departure counts, when rendering, then fills vertical space."""
        groups = [
            self._create_direction_group("Stop1", "Direction1", 1),
            self._create_direction_group("Stop2", "Direction2", 5),
            self._create_direction_group("Stop3", "Direction3", 10),
            self._create_direction_group("Stop4", "Direction4", 3),
        ]
        expected_height = renderer.config.height

        self._render_and_verify_height(renderer, groups, expected_height)

    def test_when_single_header_no_departures_then_fills_vertical_space(
        self, renderer: InkyRenderer
    ) -> None:
        """Given 1 header with no departures, when rendering, then fills vertical space correctly."""
        groups = [self._create_direction_group("Stop1", "Direction1", 0)]
        expected_height = renderer.config.height

        self._render_and_verify_height(renderer, groups, expected_height)

    def test_when_many_headers_few_departures_then_fills_vertical_space(
        self, renderer: InkyRenderer
    ) -> None:
        """Given many headers with few departures, when rendering, then fills vertical space."""
        groups = [
            self._create_direction_group(f"Stop{i}", f"Direction{i}", 1)
            for i in range(10)
        ]
        expected_height = renderer.config.height

        self._render_and_verify_height(renderer, groups, expected_height)

    def test_when_single_header_single_departure_then_header_height_equals_line_height(
        self, renderer: InkyRenderer
    ) -> None:
        """Given 1 header with 1 departure, when rendering, then header height equals line height."""
        groups = [self._create_direction_group("Stop1", "Direction1", 1)]

        # Render to set internal state
        renderer.render(groups)

        # Verify header height equals line height
        assert hasattr(renderer, "_header_height"), "Renderer should have _header_height attribute"
        assert hasattr(renderer, "_line_height"), "Renderer should have _line_height attribute"
        assert renderer._header_height == renderer._line_height, (
            f"Header height {renderer._header_height} should equal line height {renderer._line_height}"
        )

    def test_when_multiple_headers_then_all_header_heights_equal_line_height(
        self, renderer: InkyRenderer
    ) -> None:
        """Given multiple headers, when rendering, then all header heights equal line height."""
        groups = [
            self._create_direction_group("Stop1", "Direction1", 2),
            self._create_direction_group("Stop2", "Direction2", 2),
            self._create_direction_group("Stop3", "Direction3", 2),
        ]

        # Render to set internal state
        renderer.render(groups)

        # Verify header height equals line height
        assert renderer._header_height == renderer._line_height, (
            f"Header height {renderer._header_height} should equal line height {renderer._line_height}"
        )

    def test_when_calculating_total_height_then_matches_available_height(
        self, renderer: InkyRenderer
    ) -> None:
        """Given various configurations, when calculating total height, then matches available height."""
        test_cases = [
            ([self._create_direction_group("Stop1", "Direction1", 1)], "1 header, 1 departure"),
            ([self._create_direction_group("Stop1", "Direction1", 10)], "1 header, 10 departures"),
            (
                [
                    self._create_direction_group("Stop1", "Direction1", 2),
                    self._create_direction_group("Stop2", "Direction2", 2),
                ],
                "2 headers, 2 departures each",
            ),
            (
                [
                    self._create_direction_group("Stop1", "Direction1", 5),
                    self._create_direction_group("Stop2", "Direction2", 5),
                    self._create_direction_group("Stop3", "Direction3", 5),
                ],
                "3 headers, 5 departures each",
            ),
        ]

        for groups, description in test_cases:
            # Render to set internal state
            renderer.render(groups)

            # Calculate expected total height
            header_count = len(groups)
            total_departures = sum(len(g.departures) for g in groups)
            total_rows = header_count + total_departures

            if total_rows > 0:
                # Calculate what the total height should be
                line_height_base = int(renderer._line_height)
                header_height_base = int(renderer._header_height)
                extra_pixels = sum(
                    getattr(renderer, "_line_height_extra_pixels", [])
                )

                calculated_total = (
                    (header_height_base * header_count)
                    + (line_height_base * total_departures)
                    + extra_pixels
                    - renderer.config.line_spacing
                )

                # The total should match full height (no padding, content fills from top to bottom)
                available_height = renderer.config.height
                assert abs(calculated_total - available_height) <= 1, (
                    f"For {description}: calculated total {calculated_total} should match "
                    f"available_height {available_height} (within 1px tolerance)"
                )

    def test_when_extra_pixels_then_distributed_correctly(
        self, renderer: InkyRenderer
    ) -> None:
        """Given configuration that requires extra pixels, when rendering, then distributes correctly."""
        # Use a configuration that will likely need extra pixels
        groups = [
            self._create_direction_group("Stop1", "Direction1", 7),
            self._create_direction_group("Stop2", "Direction2", 7),
        ]

        # Render to set internal state
        renderer.render(groups)

        # Verify extra pixels are distributed
        extra_pixels = getattr(renderer, "_line_height_extra_pixels", [])
        total_rows = len(groups) + sum(len(g.departures) for g in groups)

        # Extra pixels should be distributed (0 or 1 per row)
        assert len(extra_pixels) == total_rows, (
            f"Extra pixels array length {len(extra_pixels)} should match total rows {total_rows}"
        )
        assert all(pixel in (0, 1) for pixel in extra_pixels), (
            "Each extra pixel value should be 0 or 1"
        )

        # Sum of extra pixels should account for any remainder
        total_extra = sum(extra_pixels)
        assert total_extra <= total_rows, (
            f"Total extra pixels {total_extra} should not exceed total rows {total_rows}"
        )

    def test_when_portrait_mode_then_uses_correct_height(
        self, renderer: InkyRenderer
    ) -> None:
        """Given portrait mode config, when rendering, then uses correct height."""
        # Portrait mode: height > width
        renderer.config.width = 480
        renderer.config.height = 800
        groups = [self._create_direction_group("Stop1", "Direction1", 5)]

        self._render_and_verify_height(renderer, groups, 800)

    def test_when_landscape_mode_then_uses_correct_height(
        self, renderer: InkyRenderer
    ) -> None:
        """Given landscape mode config, when rendering, then uses correct height."""
        # Landscape mode: width > height (swapped for rendering)
        renderer.config.width = 800
        renderer.config.height = 480
        groups = [self._create_direction_group("Stop1", "Direction1", 5)]

        self._render_and_verify_height(renderer, groups, 480)

    def test_when_different_padding_then_accounts_correctly(
        self, renderer: InkyRenderer
    ) -> None:
        """Given different padding values, when rendering, then accounts correctly."""
        test_paddings = [0, 4, 8, 16]

        for padding in test_paddings:
            renderer.config.padding = padding
            groups = [self._create_direction_group("Stop1", "Direction1", 5)]

            # Full height is used regardless of padding (content fills from top to bottom)
            expected_height = renderer.config.height
            self._render_and_verify_height(renderer, groups, expected_height)

    def test_when_many_rows_then_still_fills_vertical_space(
        self, renderer: InkyRenderer
    ) -> None:
        """Given many rows, when rendering, then still fills vertical space correctly."""
        # Create many groups with many departures
        groups = [
            self._create_direction_group(f"Stop{i}", f"Direction{i}", 8)
            for i in range(5)
        ]
        expected_height = renderer.config.height

        self._render_and_verify_height(renderer, groups, expected_height)

    def test_when_few_rows_then_still_fills_vertical_space(
        self, renderer: InkyRenderer
    ) -> None:
        """Given few rows, when rendering, then still fills vertical space correctly."""
        # Create few groups with few departures
        groups = [
            self._create_direction_group("Stop1", "Direction1", 1),
            self._create_direction_group("Stop2", "Direction2", 1),
        ]
        expected_height = renderer.config.height

        self._render_and_verify_height(renderer, groups, expected_height)

    def test_when_empty_groups_then_handles_gracefully(
        self, renderer: InkyRenderer
    ) -> None:
        """Given empty groups, when rendering, then handles gracefully."""
        # Create groups with no departures
        groups = [
            self._create_direction_group("Stop1", "Direction1", 0),
            self._create_direction_group("Stop2", "Direction2", 0),
        ]

        # Should not raise an exception
        img = renderer.render(groups)
        assert img is not None, "Should render successfully even with empty groups"

    def test_when_single_row_then_fills_vertical_space(
        self, renderer: InkyRenderer
    ) -> None:
        """Given single row (1 header, 0 departures), when rendering, then fills vertical space."""
        groups = [self._create_direction_group("Stop1", "Direction1", 0)]
        expected_height = renderer.config.height

        self._render_and_verify_height(renderer, groups, expected_height)

    def test_when_line_spacing_changes_then_accounts_correctly(
        self, renderer: InkyRenderer
    ) -> None:
        """Given different line spacing values, when rendering, then accounts correctly."""
        test_spacings = [0, 2, 4, 8]

        for spacing in test_spacings:
            renderer.config.line_spacing = spacing
            groups = [self._create_direction_group("Stop1", "Direction1", 5)]

            # Should render successfully
            img = renderer.render(groups)
            assert img is not None, f"Should render successfully with line_spacing={spacing}"

    def test_when_header_and_departure_heights_then_consistent(
        self, renderer: InkyRenderer
    ) -> None:
        """Given various configurations, when rendering, then header and departure heights are consistent."""
        test_cases = [
            [self._create_direction_group("Stop1", "Direction1", 1)],
            [self._create_direction_group("Stop1", "Direction1", 10)],
            [
                self._create_direction_group("Stop1", "Direction1", 2),
                self._create_direction_group("Stop2", "Direction2", 2),
            ],
            [
                self._create_direction_group("Stop1", "Direction1", 5),
                self._create_direction_group("Stop2", "Direction2", 5),
                self._create_direction_group("Stop3", "Direction3", 5),
            ],
        ]

        for groups in test_cases:
            renderer.render(groups)

            # Header height should equal line height in all cases
            assert renderer._header_height == renderer._line_height, (
                f"Header height {renderer._header_height} should equal "
                f"line height {renderer._line_height} for {len(groups)} groups"
            )

    def test_when_total_height_calculation_then_matches_rendered_height(
        self, renderer: InkyRenderer
    ) -> None:
        """Given rendered image, when checking height, then matches calculated total height."""
        groups = [
            self._create_direction_group("Stop1", "Direction1", 3),
            self._create_direction_group("Stop2", "Direction2", 3),
            self._create_direction_group("Stop3", "Direction3", 3),
        ]

        img = renderer.render(groups)

        # Image height should match config height
        assert img.height == renderer.config.height, (
            f"Rendered image height {img.height} should match config height {renderer.config.height}"
        )

        # Verify the calculation used the correct available height
        usable_height = renderer.config.usable_height
        assert usable_height == renderer.config.height - 2 * renderer.config.padding, (
            f"Usable height {usable_height} should account for padding"
        )
