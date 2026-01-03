"""Tests for ApiPoller behavior."""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from mvg_departures.adapters.config import AppConfig
from mvg_departures.adapters.web.broadcasters import StateBroadcaster
from mvg_departures.adapters.web.pollers import (
    ApiPoller,
    ApiPollerConfiguration,
    ApiPollerServices,
    ApiPollerSettings,
)
from mvg_departures.adapters.web.state import DeparturesState
from mvg_departures.adapters.web.updaters import StateUpdater
from mvg_departures.application.services import DepartureGroupingService
from mvg_departures.domain.models import (
    Departure,
    DirectionGroupWithMetadata,
    StopConfiguration,
)
from tests.test_services import MockDepartureRepository


@pytest.fixture
def sample_departures() -> list[Departure]:
    """Create sample departures for testing."""
    now = datetime.now(UTC)
    return [
        Departure(
            time=now + timedelta(minutes=5),
            planned_time=now + timedelta(minutes=5),
            delay_seconds=0,
            platform=1,
            is_realtime=True,
            line="139",
            destination="Klinikum Harlaching",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        ),
    ]


@pytest.fixture
def stop_config() -> StopConfiguration:
    """Create a sample stop configuration."""
    return StopConfiguration(
        station_id="de:09162:1110",
        station_name="Chiemgaustr.",
        direction_mappings={"->Klinikum": ["139 Klinikum Harlaching"]},
    )


@pytest.fixture
def mock_state_updater() -> StateUpdater:
    """Create a mock state updater."""
    departures_state = DeparturesState()
    return StateUpdater(departures_state)


@pytest.fixture
def mock_state_broadcaster() -> StateBroadcaster:
    """Create a mock state broadcaster."""
    return StateBroadcaster()


@pytest.mark.asyncio
async def test_when_cache_empty_then_fetches_fresh_from_api(
    sample_departures: list[Departure],
    stop_config: StopConfiguration,
    mock_state_updater: StateUpdater,
    mock_state_broadcaster: StateBroadcaster,
) -> None:
    """Given empty cache, when processing, then fetches fresh data from API instead of using stale cached groups."""
    with patch.dict(os.environ, {}, clear=True):
        # Create a grouping service that will return fresh departures
        repo = MockDepartureRepository(sample_departures)
        grouping_service = DepartureGroupingService(repo)

        # Create ApiPoller with empty shared cache
        empty_cache: dict[str, list[Departure]] = {}
        config = AppConfig.for_testing(config_file=None)
        services = ApiPollerServices(
            grouping_service=grouping_service,
            state_updater=mock_state_updater,
            state_broadcaster=mock_state_broadcaster,
        )
        configuration = ApiPollerConfiguration(
            stop_configs=[stop_config],
            config=config,
            refresh_interval_seconds=None,
        )
        settings = ApiPollerSettings(
            broadcast_topic="test",
            shared_cache=empty_cache,
        )
        poller = ApiPoller(services=services, configuration=configuration, settings=settings)

        # Mock the broadcaster to avoid actual pubsub calls
        mock_state_broadcaster.broadcast_update = AsyncMock()

        # Process and broadcast
        await poller._process_and_broadcast()

        # Verify that fresh data was fetched (not cached groups)
        # The state should have the fresh departure from the API
        assert len(mock_state_updater.departures_state.direction_groups) == 1
        group = mock_state_updater.departures_state.direction_groups[0]
        assert isinstance(group, DirectionGroupWithMetadata)
        assert group.stop_name == "Chiemgaustr."
        assert group.direction_name == "->Klinikum"
        assert len(group.departures) == 1
        assert group.departures[0].line == "139"
        assert group.departures[0].destination == "Klinikum Harlaching"

        # Verify that the fresh data was cached for future use
        assert stop_config.station_name in poller.cached_departures


@pytest.mark.asyncio
async def test_when_api_fails_then_falls_back_to_cached_groups(
    sample_departures: list[Departure],
    stop_config: StopConfiguration,
    mock_state_updater: StateUpdater,
    mock_state_broadcaster: StateBroadcaster,
) -> None:
    """Given API failure, when processing, then falls back to cached processed groups."""
    with patch.dict(os.environ, {}, clear=True):
        # Create a grouping service that will raise an exception
        repo = MockDepartureRepository(sample_departures)

        async def failing_get_departures(*args, **kwargs):  # noqa: ARG001
            raise Exception("API call failed: 502 Bad Gateway")

        repo.get_departures = failing_get_departures
        grouping_service = DepartureGroupingService(repo)

        # Create ApiPoller with empty shared cache
        empty_cache: dict[str, list[Departure]] = {}
        config = AppConfig.for_testing(config_file=None)
        services = ApiPollerServices(
            grouping_service=grouping_service,
            state_updater=mock_state_updater,
            state_broadcaster=mock_state_broadcaster,
        )
        configuration = ApiPollerConfiguration(
            stop_configs=[stop_config],
            config=config,
            refresh_interval_seconds=None,
        )
        settings = ApiPollerSettings(
            broadcast_topic="test",
            shared_cache=empty_cache,
        )
        poller = ApiPoller(services=services, configuration=configuration, settings=settings)

        # Pre-populate cached groups (simulating a previous successful fetch)
        cached_departure = Departure(
            time=datetime.now(UTC) + timedelta(minutes=10),
            planned_time=datetime.now(UTC) + timedelta(minutes=10),
            delay_seconds=0,
            platform=1,
            is_realtime=True,
            line="139",
            destination="Klinikum Harlaching",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        )
        from mvg_departures.domain.models import GroupedDepartures

        poller.cached_departures[stop_config.station_name] = [
            GroupedDepartures(direction_name="->Klinikum", departures=[cached_departure])
        ]

        # Mock the broadcaster to avoid actual pubsub calls
        mock_state_broadcaster.broadcast_update = AsyncMock()

        # Process and broadcast (should catch exception and use cached groups)
        await poller._process_and_broadcast()

        # Verify that cached groups were used (marked as stale/non-realtime)
        assert len(mock_state_updater.departures_state.direction_groups) == 1
        group = mock_state_updater.departures_state.direction_groups[0]
        assert isinstance(group, DirectionGroupWithMetadata)
        assert group.stop_name == "Chiemgaustr."
        assert group.direction_name == "->Klinikum"
        assert len(group.departures) == 1
        # Departures should be marked as non-realtime (stale) when using cached fallback
        assert group.departures[0].is_realtime is False
        assert group.departures[0].line == "139"


@pytest.mark.asyncio
async def test_when_cache_has_data_then_uses_cache(
    sample_departures: list[Departure],
    stop_config: StopConfiguration,
    mock_state_updater: StateUpdater,
    mock_state_broadcaster: StateBroadcaster,
) -> None:
    """Given cache has data, when processing, then uses cached data instead of fetching from API."""
    with patch.dict(os.environ, {}, clear=True):
        # Create a grouping service
        repo = MockDepartureRepository([])  # Empty repo - should not be called
        grouping_service = DepartureGroupingService(repo)

        # Create ApiPoller with populated shared cache
        cache_with_data: dict[str, list[Departure]] = {stop_config.station_id: sample_departures}
        config = AppConfig.for_testing(config_file=None)
        services = ApiPollerServices(
            grouping_service=grouping_service,
            state_updater=mock_state_updater,
            state_broadcaster=mock_state_broadcaster,
        )
        configuration = ApiPollerConfiguration(
            stop_configs=[stop_config],
            config=config,
            refresh_interval_seconds=None,
        )
        settings = ApiPollerSettings(
            broadcast_topic="test",
            shared_cache=cache_with_data,
        )
        poller = ApiPoller(services=services, configuration=configuration, settings=settings)

        # Mock the broadcaster to avoid actual pubsub calls
        mock_state_broadcaster.broadcast_update = AsyncMock()

        # Process and broadcast
        await poller._process_and_broadcast()

        # Verify that cached data was used
        assert len(mock_state_updater.departures_state.direction_groups) == 1
        group = mock_state_updater.departures_state.direction_groups[0]
        assert isinstance(group, DirectionGroupWithMetadata)
        assert group.stop_name == "Chiemgaustr."
        assert group.direction_name == "->Klinikum"
        assert len(group.departures) == 1
        assert group.departures[0].line == "139"
        assert group.departures[0].destination == "Klinikum Harlaching"
