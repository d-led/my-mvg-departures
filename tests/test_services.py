"""Tests for application services."""

from datetime import datetime, timedelta

import pytest

from mvg_departures.application.services import DepartureGroupingService
from mvg_departures.domain.models import Departure, StopConfiguration


class MockDepartureRepository:
    """Mock departure repository for testing."""

    def __init__(self, departures: list[Departure]) -> None:
        """Initialize with a list of departures to return."""
        self.departures = departures

    async def get_departures(
        self,
        station_id: str,
        limit: int = 10,
        offset_minutes: int = 0,
        transport_types: list[str] | None = None,
    ) -> list[Departure]:
        """Return the configured departures."""
        return self.departures


@pytest.fixture
def sample_departures() -> list[Departure]:
    """Create sample departures for testing."""
    now = datetime.now()
    return [
        Departure(
            time=now + timedelta(minutes=5),
            planned_time=now + timedelta(minutes=5),
            delay_seconds=0,
            platform=1,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(minutes=10),
            planned_time=now + timedelta(minutes=10),
            delay_seconds=0,
            platform=1,
            is_realtime=True,
            line="U3",
            destination="Fürstenried West",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(minutes=15),
            planned_time=now + timedelta(minutes=15),
            delay_seconds=0,
            platform=2,
            is_realtime=True,
            line="U6",
            destination="Klinikum Großhadern",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
    ]


@pytest.fixture
def stop_config() -> StopConfiguration:
    """Create a sample stop configuration."""
    return StopConfiguration(
        station_id="de:09162:70",
        station_name="Universität",
        direction_mappings={
            "->Giesing": ["Giesing", "Fürstenried"],
            "->West": ["Klinikum"],
        },
    )


@pytest.mark.asyncio
async def test_group_departures_by_direction(
    sample_departures: list[Departure], stop_config: StopConfiguration
) -> None:
    """Given departures with different destinations, when grouped, then they are organized by direction."""
    repo = MockDepartureRepository(sample_departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    assert len(groups) == 2
    direction_names = [name for name, _ in groups]
    assert "->Giesing" in direction_names
    assert "->West" in direction_names


@pytest.mark.asyncio
async def test_group_departures_sorts_by_time(
    sample_departures: list[Departure], stop_config: StopConfiguration
) -> None:
    """Given departures, when grouped, then departures within each group are sorted by time."""
    repo = MockDepartureRepository(sample_departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    for direction_name, departures in groups:
        times = [d.time for d in departures]
        assert times == sorted(times), f"Departures in {direction_name} should be sorted by time"


@pytest.mark.asyncio
async def test_group_departures_matches_exact_destination(
    stop_config: StopConfiguration,
) -> None:
    """Given a departure with exact destination match, when grouped, then it matches the direction."""
    now = datetime.now()
    departure = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=0,
        platform=1,
        is_realtime=True,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    repo = MockDepartureRepository([departure])
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    giesing_groups = [g for g in groups if g[0] == "->Giesing"]
    assert len(giesing_groups) == 1
    assert len(giesing_groups[0][1]) == 1
    assert giesing_groups[0][1][0].destination == "Giesing"


@pytest.mark.asyncio
async def test_group_departures_handles_ungrouped(
    stop_config: StopConfiguration,
) -> None:
    """Given a departure that doesn't match any direction, when grouped, then it appears in 'Other' group."""
    now = datetime.now()
    departure = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=0,
        platform=1,
        is_realtime=True,
        line="U3",
        destination="Unknown Destination",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    repo = MockDepartureRepository([departure])
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    other_groups = [g for g in groups if g[0] == "Other"]
    assert len(other_groups) == 1
    assert len(other_groups[0][1]) == 1
    assert other_groups[0][1][0].destination == "Unknown Destination"


@pytest.mark.asyncio
async def test_group_departures_matches_pattern(
    stop_config: StopConfiguration,
) -> None:
    """Given a departure matching a pattern, when grouped, then it matches the direction."""
    now = datetime.now()
    departure = Departure(
        time=now + timedelta(minutes=5),
        planned_time=now + timedelta(minutes=5),
        delay_seconds=0,
        platform=1,
        is_realtime=True,
        line="U3",
        destination="Klinikum Großhadern",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=[],
    )

    repo = MockDepartureRepository([departure])
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    west_groups = [g for g in groups if g[0] == "->West"]
    assert len(west_groups) == 1
    assert len(west_groups[0][1]) == 1


