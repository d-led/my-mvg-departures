"""Behavior-focused tests for PyViewWebAdapterConfig dataclass."""

from unittest.mock import MagicMock

import pytest

from mvg_departures.adapters.config import AppConfig
from mvg_departures.adapters.web.pyview_app import PyViewWebAdapterConfig
from mvg_departures.domain.models import RouteConfiguration, StopConfiguration
from mvg_departures.domain.ports import DepartureGroupingService, DepartureRepository


def test_when_created_then_holds_all_configuration_values() -> None:
    """Given all required parameters, when creating config, then all values are stored."""
    grouping_service = MagicMock(spec=DepartureGroupingService)
    route_configs = [
        RouteConfiguration(
            path="/test",
            stop_configs=[
                StopConfiguration(
                    station_id="de:09162:70",
                    station_name="Test",
                    direction_mappings={},
                )
            ],
        )
    ]
    config = AppConfig.for_testing()
    departure_repo = MagicMock(spec=DepartureRepository)

    adapter_config = PyViewWebAdapterConfig(
        grouping_service=grouping_service,
        route_configs=route_configs,
        config=config,
        departure_repository=departure_repo,
    )

    assert adapter_config.grouping_service is grouping_service
    assert adapter_config.route_configs == route_configs
    assert adapter_config.config is config
    assert adapter_config.departure_repository is departure_repo
    assert adapter_config.session is None


def test_when_created_with_session_then_stores_session() -> None:
    """Given session parameter, when creating config, then session is stored."""
    grouping_service = MagicMock(spec=DepartureGroupingService)
    route_configs = []
    config = AppConfig.for_testing()
    departure_repo = MagicMock(spec=DepartureRepository)
    session = MagicMock()

    adapter_config = PyViewWebAdapterConfig(
        grouping_service=grouping_service,
        route_configs=route_configs,
        config=config,
        departure_repository=departure_repo,
        session=session,
    )

    assert adapter_config.session is session


def test_when_created_then_is_immutable() -> None:
    """Given config instance, when trying to modify, then raises FrozenInstanceError."""
    from dataclasses import FrozenInstanceError

    grouping_service = MagicMock(spec=DepartureGroupingService)
    route_configs = []
    config = AppConfig.for_testing()
    departure_repo = MagicMock(spec=DepartureRepository)

    adapter_config = PyViewWebAdapterConfig(
        grouping_service=grouping_service,
        route_configs=route_configs,
        config=config,
        departure_repository=departure_repo,
    )

    with pytest.raises(FrozenInstanceError):
        adapter_config.grouping_service = MagicMock()


def test_when_creating_adapter_with_config_then_initializes_correctly() -> None:
    """Given PyViewWebAdapterConfig, when creating adapter, then adapter has all values."""
    from mvg_departures.adapters.web.pyview_app import PyViewWebAdapter

    grouping_service = MagicMock(spec=DepartureGroupingService)
    route_config = RouteConfiguration(
        path="/test",
        stop_configs=[
            StopConfiguration(
                station_id="de:09162:70",
                station_name="Test",
                direction_mappings={},
            )
        ],
    )
    config = AppConfig.for_testing()
    departure_repo = MagicMock(spec=DepartureRepository)

    adapter_config = PyViewWebAdapterConfig(
        grouping_service=grouping_service,
        route_configs=[route_config],
        config=config,
        departure_repository=departure_repo,
    )

    adapter = PyViewWebAdapter(adapter_config)

    assert adapter.grouping_service is grouping_service
    assert adapter.route_configs == [route_config]
    assert adapter.config is config
    assert adapter.departure_repository is departure_repo
    assert adapter.session is None
    assert "/test" in adapter.route_states
