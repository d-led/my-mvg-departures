"""Unit tests for template parsing - catch template errors before server startup."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from pyview.vendor import ibis
from pyview.vendor.ibis.loaders import FileReloader

from mvg_departures.adapters.config import AppConfig
from mvg_departures.adapters.web.presence import PresenceTracker
from mvg_departures.adapters.web.state import DeparturesState, State
from mvg_departures.adapters.web.views.departures.departures import (
    DeparturesLiveView,
    DisplayConfiguration,
    LiveViewDependencies,
)
from mvg_departures.application.services import DepartureGroupingService
from mvg_departures.domain.models import (
    Departure,
    DirectionGroupWithMetadata,
    StopConfiguration,
)


class TestTemplateParsing:
    """Test that the departures.html template can be parsed and rendered."""

    def _load_template(self) -> ibis.Template:
        """Load the departures.html template using the same method as DeparturesLiveView.

        Returns the underlying ibis.Template directly for testing.
        """
        current_file_path = Path(__file__).resolve()
        views_dir = (
            current_file_path.parent.parent
            / "src"
            / "mvg_departures"
            / "adapters"
            / "web"
            / "views"
        )

        if not hasattr(ibis, "loader") or not isinstance(ibis.loader, FileReloader):
            ibis.loader = FileReloader(str(views_dir))

        template_path = "departures/departures.html"
        template_file = views_dir / template_path
        template_content = template_file.read_text(encoding="utf-8")

        return ibis.Template(template_content)

    def _create_test_live_view(self) -> DeparturesLiveView:
        """Create a test DeparturesLiveView instance."""
        with patch.dict(os.environ, {}, clear=True):
            state_manager = State()
            grouping_service = MagicMock(spec=DepartureGroupingService)
            stop_configs = [
                StopConfiguration(
                    station_id="de:09162:70",
                    station_name="Universität",
                    direction_mappings={},
                )
            ]
            config = AppConfig.for_testing(config_file=None)
            presence_tracker = PresenceTracker()
            dependencies = LiveViewDependencies(
                state_manager=state_manager,
                grouping_service=grouping_service,
                stop_configs=stop_configs,
                config=config,
                presence_tracker=presence_tracker,
            )
            return DeparturesLiveView(dependencies)

    def _create_minimal_template_assigns(self) -> dict:
        """Create minimal template assigns for testing."""
        view = self._create_test_live_view()
        state = DeparturesState(
            direction_groups=[],
            last_update=datetime.now(UTC),
            api_status="online",
            presence_local=None,
            presence_total=None,
        )

        template_data = {
            "groups_with_departures": [],
            "stops_without_departures": [],
            "has_departures": False,
        }

        return view._build_template_assigns(state, template_data)

    def test_template_can_be_loaded(self) -> None:
        """Test that the template file can be loaded without errors."""
        template = self._load_template()
        assert template is not None

    def test_template_can_be_rendered_with_minimal_data(self) -> None:
        """Test that the template can be rendered with minimal data."""
        template = self._load_template()
        assigns = self._create_minimal_template_assigns()

        # Render the template - this will raise an exception if there are syntax errors
        result = template.render(**assigns)

        # Verify we got some HTML output
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

        # Verify key elements are present
        assert "<head>" in result.lower() or "html" in result.lower()

    def test_template_renders_with_empty_departures(self) -> None:
        """Test that the template renders correctly with no departures."""
        template = self._load_template()
        assigns = self._create_minimal_template_assigns()

        # Ensure empty state
        assigns["groups_with_departures"] = []
        assigns["stops_without_departures"] = []
        assigns["has_departures"] = False

        # Should render without errors
        result = template.render(**assigns)
        assert result is not None
        assert isinstance(result, str)

    def test_template_renders_with_single_departure(self) -> None:
        """Test that the template renders correctly with a single departure."""
        template = self._load_template()
        assigns = self._create_minimal_template_assigns()
        view = self._create_test_live_view()

        now = datetime.now(UTC)
        departure = Departure(
            time=now,
            planned_time=now,
            delay_seconds=None,
            platform=None,
            is_realtime=False,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        )

        direction_group = DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )

        # Get formatted template data
        template_data = view.departure_grouping_calculator.calculate_display_data([direction_group])
        state = DeparturesState(
            direction_groups=[direction_group],
            last_update=now,
            api_status="online",
            presence_local=None,
            presence_total=None,
        )
        assigns = view._build_template_assigns(state, template_data)

        # Should render without errors
        result = template.render(**assigns)
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_template_renders_with_multiple_departures(self) -> None:
        """Test that the template renders correctly with multiple departures."""
        template = self._load_template()
        view = self._create_test_live_view()

        now = datetime.now(UTC)
        departures = [
            Departure(
                time=now,
                planned_time=now,
                delay_seconds=None,
                platform=None,
                is_realtime=False,
                line=f"U{i}",
                destination=f"Destination {i}",
                transport_type="U-Bahn",
                icon="mdi:subway",
                is_cancelled=False,
                messages=[],
            )
            for i in range(3)
        ]

        direction_group = DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="Multiple Departures",
            departures=departures,
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )

        # Get formatted template data
        template_data = view.departure_grouping_calculator.calculate_display_data([direction_group])
        state = DeparturesState(
            direction_groups=[direction_group],
            last_update=now,
            api_status="online",
            presence_local=None,
            presence_total=None,
        )
        assigns = view._build_template_assigns(state, template_data)

        # Should render without errors
        result = template.render(**assigns)
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_template_renders_with_cancelled_departure(self) -> None:
        """Test that the template renders correctly with cancelled departures."""
        template = self._load_template()
        view = self._create_test_live_view()

        now = datetime.now(UTC)
        departure = Departure(
            time=now,
            planned_time=now,
            delay_seconds=None,
            platform=None,
            is_realtime=False,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=True,
            messages=["Service cancelled"],
        )

        direction_group = DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )

        # Get formatted template data
        template_data = view.departure_grouping_calculator.calculate_display_data([direction_group])
        state = DeparturesState(
            direction_groups=[direction_group],
            last_update=now,
            api_status="online",
            presence_local=None,
            presence_total=None,
        )
        assigns = view._build_template_assigns(state, template_data)

        # Should render without errors
        result = template.render(**assigns)
        assert result is not None
        assert isinstance(result, str)

    def test_template_handles_missing_optional_fields(self) -> None:
        """Test that the template handles missing optional fields gracefully."""
        template = self._load_template()
        assigns = self._create_minimal_template_assigns()

        # Remove optional fields
        assigns.pop("route_title", None)
        assigns.pop("route_theme", None)
        assigns.pop("max_train_steps", None)
        assigns.pop("environment_name", None)

        # Should still render without errors
        result = template.render(**assigns)
        assert result is not None
        assert isinstance(result, str)

    def test_template_with_all_config_options(self) -> None:
        """Test that the template renders with various configuration options."""
        view = self._create_test_live_view()
        state = DeparturesState(
            direction_groups=[],
            last_update=datetime.now(UTC),
            api_status="online",
            presence_local=5,
            presence_total=42,
        )

        template_data = {
            "groups_with_departures": [],
            "stops_without_departures": [],
            "has_departures": False,
        }

        assigns = view._build_template_assigns(state, template_data)

        # Verify key assigns are present
        assert "title" in assigns
        assert "theme" in assigns
        assert "banner_color" in assigns
        assert "font_size_route_number" in assigns
        assert "pagination_enabled" in assigns
        assert "departures_per_page" in assigns
        assert "refresh_interval_seconds" in assigns
        assert "api_status" in assigns
        assert "presence_local" in assigns
        assert "presence_total" in assigns

        # Render should work
        template = self._load_template()
        result = template.render(**assigns)
        assert result is not None
        assert isinstance(result, str)

    def test_template_with_special_characters_in_destination(self) -> None:
        """Test that the template handles special characters in destination names."""
        template = self._load_template()
        view = self._create_test_live_view()

        now = datetime.now(UTC)
        departure = Departure(
            time=now,
            planned_time=now,
            delay_seconds=None,
            platform=None,
            is_realtime=False,
            line="U3",
            destination="Straße & Platz <Main>",  # Special characters
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        )

        direction_group = DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Destination",
            departures=[departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )

        # Get formatted template data
        template_data = view.departure_grouping_calculator.calculate_display_data([direction_group])
        state = DeparturesState(
            direction_groups=[direction_group],
            last_update=now,
            api_status="online",
            presence_local=None,
            presence_total=None,
        )
        assigns = view._build_template_assigns(state, template_data)

        # Should render without errors
        result = template.render(**assigns)
        assert result is not None
        assert isinstance(result, str)

    def test_template_with_delay_in_departure(self) -> None:
        """Test that the template correctly displays departures with delays."""
        template = self._load_template()
        view = self._create_test_live_view()

        now = datetime.now(UTC)
        departure = Departure(
            time=now,
            planned_time=now,
            delay_seconds=300,  # 5 minute delay
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=["Delay due to signal failure"],
        )

        direction_group = DirectionGroupWithMetadata(
            station_id="de:09162:70",
            stop_name="Universität",
            direction_name="->Giesing",
            departures=[departure],
            random_header_colors=None,
            header_background_brightness=None,
            random_color_salt=None,
        )

        # Get formatted template data
        template_data = view.departure_grouping_calculator.calculate_display_data([direction_group])
        state = DeparturesState(
            direction_groups=[direction_group],
            last_update=now,
            api_status="online",
            presence_local=None,
            presence_total=None,
        )
        assigns = view._build_template_assigns(state, template_data)

        # Should render without errors
        result = template.render(**assigns)
        assert result is not None
        assert isinstance(result, str)

    def test_build_template_assigns_includes_required_keys(self) -> None:
        """Test that _build_template_assigns includes all required keys."""
        view = self._create_test_live_view()
        state = DeparturesState(
            direction_groups=[],
            last_update=datetime.now(UTC),
            api_status="online",
            presence_local=None,
            presence_total=None,
        )
        template_data = {
            "groups_with_departures": [],
            "stops_without_departures": [],
            "has_departures": False,
        }

        assigns = view._build_template_assigns(state, template_data)

        # Verify all required keys are present
        required_keys = [
            "title",
            "theme",
            "banner_color",
            "font_size_route_number",
            "font_size_destination",
            "font_size_platform",
            "font_size_time",
            "font_size_direction_header",
            "pagination_enabled",
            "departures_per_page",
            "refresh_interval_seconds",
            "api_status",
            "static_version",
            "groups_with_departures",
            "stops_without_departures",
            "has_departures",
        ]

        for key in required_keys:
            assert key in assigns, f"Missing required key: {key}"

    def test_build_template_assigns_with_presence_tracking(self) -> None:
        """Test that _build_template_assigns correctly includes presence tracking data."""
        view = self._create_test_live_view()
        state = DeparturesState(
            direction_groups=[],
            last_update=datetime.now(UTC),
            api_status="online",
            presence_local=3,
            presence_total=15,
        )
        template_data = {
            "groups_with_departures": [],
            "stops_without_departures": [],
            "has_departures": False,
        }

        assigns = view._build_template_assigns(state, template_data)

        assert assigns["presence_local"] == "3"
        assert assigns["presence_total"] == "15"

    def test_validate_template_data_ensures_required_keys(self) -> None:
        """Test that _validate_template_data adds missing required keys."""
        view = self._create_test_live_view()

        # Empty template data
        empty_data = {}
        validated = view._validate_template_data(empty_data)

        assert "groups_with_departures" in validated
        assert "stops_without_departures" in validated
        assert "has_departures" in validated

    def test_template_with_display_configuration(self) -> None:
        """Test that the template renders with custom display configuration."""
        with patch.dict(os.environ, {}, clear=True):
            state_manager = State()
            grouping_service = MagicMock(spec=DepartureGroupingService)
            stop_configs = [
                StopConfiguration(
                    station_id="de:09162:70",
                    station_name="Universität",
                    direction_mappings={},
                )
            ]
            config = AppConfig.for_testing(config_file=None)
            presence_tracker = PresenceTracker()
            dependencies = LiveViewDependencies(
                state_manager=state_manager,
                grouping_service=grouping_service,
                stop_configs=stop_configs,
                config=config,
                presence_tracker=presence_tracker,
            )

            display_config = DisplayConfiguration(
                fill_vertical_space=True,
                font_scaling_factor_when_filling=1.2,
                random_header_colors=True,
                header_background_brightness=0.8,
            )

            view = DeparturesLiveView(
                dependencies,
                display_config=display_config,
            )

            state = DeparturesState(
                direction_groups=[],
                last_update=datetime.now(UTC),
                api_status="online",
                presence_local=None,
                presence_total=None,
            )
            template_data = {
                "groups_with_departures": [],
                "stops_without_departures": [],
                "has_departures": False,
            }

            assigns = view._build_template_assigns(state, template_data)

            assert assigns["fill_vertical_space"] == "true"
            assert assigns["font_scaling_factor_when_filling"] == "1.2"

            # Should render without errors
            template = self._load_template()
            result = template.render(**assigns)
            assert result is not None
