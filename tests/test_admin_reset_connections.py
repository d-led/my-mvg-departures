"""Tests for admin maintenance helpers such as connection reset."""

from unittest.mock import MagicMock

from mvg_departures.adapters.config import AppConfig
from mvg_departures.adapters.web.pyview_app import PyViewWebAdapter
from mvg_departures.domain.models import RouteConfiguration, StopConfiguration
from mvg_departures.domain.ports import DepartureGroupingService, DepartureRepository


def _make_adapter() -> PyViewWebAdapter:
    """Create a minimal PyViewWebAdapter for testing admin helpers."""
    grouping_service = MagicMock(spec=DepartureGroupingService)
    departure_repo = MagicMock(spec=DepartureRepository)
    route_config = RouteConfiguration(
        path="/",
        stop_configs=[
            StopConfiguration(
                station_id="de:09162:70",
                station_name="Universität",
                direction_mappings={},
            )
        ],
    )
    config = AppConfig(config_file=None, _env_file=None, admin_command_token="test-token")
    return PyViewWebAdapter(
        grouping_service=grouping_service,
        route_configs=[route_config],
        config=config,
        departure_repository=departure_repo,
    )


def test_route_states_initially_empty() -> None:
    """Given a fresh adapter, then no sockets are registered in route state."""
    adapter = _make_adapter()

    assert list(adapter.route_states.keys()) == ["/"]
    state = adapter.route_states["/"]
    assert len(state.connected_sockets) == 0
