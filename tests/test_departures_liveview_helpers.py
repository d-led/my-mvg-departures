"""Tests for DeparturesLiveView helper methods."""

import os
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from mvg_departures.adapters.config import AppConfig
from mvg_departures.adapters.web.presence import PresenceTracker
from mvg_departures.adapters.web.state import DeparturesState, State
from mvg_departures.adapters.web.views.departures.departures import DeparturesLiveView
from mvg_departures.application.services import DepartureGroupingService
from mvg_departures.domain.models import StopConfiguration


def _create_test_view() -> DeparturesLiveView:
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
        config = AppConfig(config_file=None, _env_file=None)
        presence_tracker = PresenceTracker()
        return DeparturesLiveView(
            state_manager, grouping_service, stop_configs, config, presence_tracker
        )


def test_update_presence_from_event_dashboard_topic() -> None:
    """Given a dashboard presence topic, when updating, then updates both local and total."""
    view = _create_test_view()
    mock_socket = MagicMock()
    mock_socket.context = DeparturesState()
    presence_data = {"local_count": 5, "total_count": 10}

    view._update_presence_from_event("presence:test", presence_data, mock_socket)

    assert mock_socket.context.presence_local == 5
    assert mock_socket.context.presence_total == 10


def test_update_presence_from_event_global_topic() -> None:
    """Given a global presence topic, when updating, then updates only total."""
    view = _create_test_view()
    mock_socket = MagicMock()
    mock_socket.context = DeparturesState()
    presence_data = {"total_count": 10}

    view._update_presence_from_event("presence:global", presence_data, mock_socket)

    assert mock_socket.context.presence_total == 10
    # Local should not be updated for global topic
    assert mock_socket.context.presence_local == 0  # Default value


def test_update_context_from_state() -> None:
    """Given state manager with departures, when updating context, then updates all fields."""
    view = _create_test_view()
    mock_socket = MagicMock()
    mock_socket.context = DeparturesState()

    # Set up state manager with some data
    now = datetime.now(UTC)
    view.state_manager.departures_state.direction_groups = [("Stop", "->Dir", [])]
    view.state_manager.departures_state.last_update = now
    view.state_manager.departures_state.api_status = "success"
    view.state_manager.departures_state.presence_local = 5
    view.state_manager.departures_state.presence_total = 10

    view._update_context_from_state(mock_socket)

    assert mock_socket.context.direction_groups == [("Stop", "->Dir", [])]
    assert mock_socket.context.last_update == now
    assert mock_socket.context.api_status == "success"
    assert mock_socket.context.presence_local == 5
    assert mock_socket.context.presence_total == 10


def test_build_template_assigns_includes_all_config() -> None:
    """Given state and template data, when building assigns, then includes all config values."""
    view = _create_test_view()
    now = datetime.now(UTC)
    state = DeparturesState(
        direction_groups=[],
        last_update=now,
        api_status="success",
        presence_local=5,
        presence_total=10,
    )
    template_data = {
        "groups_with_departures": [],
        "stops_without_departures": [],
        "has_departures": False,
        "font_size_no_departures": "12px",
    }

    result = view._build_template_assigns(state, template_data)

    # Check template data is included
    assert result["has_departures"] is False
    # Check config values are included
    assert "theme" in result
    assert "banner_color" in result
    assert "font_size_route_number" in result
    assert "pagination_enabled" in result
    # Check state values are included
    assert result["api_status"] == "success"
    assert result["presence_local"] == 5
    assert result["presence_total"] == 10
    assert "update_time" in result


def test_build_template_assigns_normalizes_theme() -> None:
    """Given invalid theme, when building assigns, then defaults to auto."""
    view = _create_test_view()
    state = DeparturesState()
    template_data = {"has_departures": False}

    # Mock invalid theme
    view.config.theme = "invalid"

    result = view._build_template_assigns(state, template_data)
    assert result["theme"] == "auto"


def test_build_template_assigns_handles_none_last_update() -> None:
    """Given state with None last_update, when building assigns, then uses zero timestamp."""
    view = _create_test_view()
    state = DeparturesState(last_update=None)
    template_data = {"has_departures": False}

    result = view._build_template_assigns(state, template_data)
    assert result["last_update_timestamp"] == "0"
