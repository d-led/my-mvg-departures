"""Tests for application services."""

from datetime import UTC, datetime, timedelta

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
        station_id: str,  # noqa: ARG002
        limit: int = 10,  # noqa: ARG002
        offset_minutes: int = 0,  # noqa: ARG002
        transport_types: list[str] | None = None,  # noqa: ARG002
    ) -> list[Departure]:
        """Return the configured departures."""
        return self.departures


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
    now = datetime.now(UTC)
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
    now = datetime.now(UTC)
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
    now = datetime.now(UTC)
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


@pytest.mark.asyncio
async def test_max_departures_per_route_filters_by_route() -> None:
    """Given multiple departures of the same route, when grouped, then only max_departures_per_route are shown."""
    now = datetime.now(UTC)
    # Create 5 departures of the same route "18" going to the same destination
    departures = [
        Departure(
            time=now + timedelta(minutes=i),
            planned_time=now + timedelta(minutes=i),
            delay_seconds=0,
            platform=1,
            is_realtime=True,
            line="18",
            destination="Gondrellplatz",
            transport_type="Tram",
            icon="mdi:tram",
            is_cancelled=False,
            messages=[],
        )
        for i in range(1, 6)  # 5 departures
    ]

    stop_config = StopConfiguration(
        station_id="de:09162:1110",
        station_name="Giesing",
        direction_mappings={"->Stadt": ["18 Gondrellplatz"]},
        max_departures_per_stop=10,  # High enough to not limit
        max_departures_per_route=2,  # Only 2 per route
        show_ungrouped=False,
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    assert len(groups) == 1
    assert groups[0][0] == "->Stadt"
    # Should only have 2 departures (max_departures_per_route), not 5
    assert len(groups[0][1]) == 2
    # Should be the first 2 (sorted by time)
    assert groups[0][1][0].time == now + timedelta(minutes=1)
    assert groups[0][1][1].time == now + timedelta(minutes=2)


@pytest.mark.asyncio
async def test_max_departures_per_route_applies_to_multiple_routes() -> None:
    """Given multiple routes in the same direction, when grouped, then each route is limited separately."""
    now = datetime.now(UTC)
    # Create departures: 3 of route "18" and 3 of route "139"
    departures = []
    for i in range(1, 4):
        departures.append(
            Departure(
                time=now + timedelta(minutes=i),
                planned_time=now + timedelta(minutes=i),
                delay_seconds=0,
                platform=1,
                is_realtime=True,
                line="18",
                destination="Gondrellplatz",
                transport_type="Tram",
                icon="mdi:tram",
                is_cancelled=False,
                messages=[],
            )
        )
    for i in range(4, 7):
        departures.append(
            Departure(
                time=now + timedelta(minutes=i),
                planned_time=now + timedelta(minutes=i),
                delay_seconds=0,
                platform=1,
                is_realtime=True,
                line="139",
                destination="Messestadt West",
                transport_type="Bus",
                icon="mdi:bus",
                is_cancelled=False,
                messages=[],
            )
        )

    stop_config = StopConfiguration(
        station_id="de:09162:1110",
        station_name="Giesing",
        direction_mappings={"->East": ["18 Gondrellplatz", "139 Messestadt West"]},
        max_departures_per_stop=10,  # High enough
        max_departures_per_route=2,  # 2 per route
        show_ungrouped=False,
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    assert len(groups) == 1
    assert groups[0][0] == "->East"
    # Should have 2 from route 18 + 2 from route 139 = 4 total
    assert len(groups[0][1]) == 4
    # Check that we have exactly 2 of each route
    route_18_count = sum(1 for d in groups[0][1] if d.line == "18")
    route_139_count = sum(1 for d in groups[0][1] if d.line == "139")
    assert route_18_count == 2
    assert route_139_count == 2


@pytest.mark.asyncio
async def test_max_departures_per_stop_limits_direction() -> None:
    """Given many departures in a direction, when grouped, then only max_departures_per_stop are shown."""
    now = datetime.now(UTC)
    # Create 10 departures of different routes
    departures = [
        Departure(
            time=now + timedelta(minutes=i),
            planned_time=now + timedelta(minutes=i),
            delay_seconds=0,
            platform=1,
            is_realtime=True,
            line=str(i),  # Different route for each
            destination="Messestadt",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        )
        for i in range(1, 11)  # 10 departures
    ]

    stop_config = StopConfiguration(
        station_id="de:09162:1110",
        station_name="Giesing",
        direction_mappings={"->East": ["Messestadt"]},  # All match
        max_departures_per_stop=4,  # Only 4 total
        max_departures_per_route=2,  # 2 per route (but we have 10 different routes)
        show_ungrouped=False,
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    assert len(groups) == 1
    assert groups[0][0] == "->East"
    # Should be limited to 4 (max_departures_per_stop)
    assert len(groups[0][1]) == 4


@pytest.mark.asyncio
async def test_max_departures_per_route_then_per_stop() -> None:
    """Given many departures, when grouped, then route filtering happens before direction limiting."""
    now = datetime.now(UTC)
    # Create 5 departures of route "18" and 5 of route "139"
    departures = []
    for route, base_min in [("18", 1), ("139", 6)]:
        for i in range(5):
            departures.append(
                Departure(
                    time=now + timedelta(minutes=base_min + i),
                    planned_time=now + timedelta(minutes=base_min + i),
                    delay_seconds=0,
                    platform=1,
                    is_realtime=True,
                    line=route,
                    destination="Messestadt",
                    transport_type="Bus",
                    icon="mdi:bus",
                    is_cancelled=False,
                    messages=[],
                )
            )

    stop_config = StopConfiguration(
        station_id="de:09162:1110",
        station_name="Giesing",
        direction_mappings={"->East": ["Messestadt"]},
        max_departures_per_stop=3,  # Only 3 total in direction
        max_departures_per_route=2,  # 2 per route
        show_ungrouped=False,
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    assert len(groups) == 1
    assert groups[0][0] == "->East"
    # After route filtering: 2 from route 18 + 2 from route 139 = 4
    # After direction limiting: 3 (max_departures_per_stop)
    assert len(groups[0][1]) == 3


@pytest.mark.asyncio
async def test_pattern_matching_route_and_destination() -> None:
    """Given a pattern like 'U2 Messestadt', when matching, then it matches only that route to that destination."""
    now = datetime.now(UTC)
    departures = [
        Departure(
            time=now + timedelta(minutes=5),
            planned_time=now + timedelta(minutes=5),
            delay_seconds=0,
            platform=1,
            is_realtime=True,
            line="U2",
            destination="Messestadt Ost",
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
            line="U2",
            destination="Feldmoching",  # Different destination
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(minutes=15),
            planned_time=now + timedelta(minutes=15),
            delay_seconds=0,
            platform=1,
            is_realtime=True,
            line="U3",  # Different route
            destination="Messestadt Ost",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
    ]

    stop_config = StopConfiguration(
        station_id="de:09162:1110",
        station_name="Giesing",
        direction_mappings={"->East": ["U2 Messestadt"]},  # Specific route + destination
        max_departures_per_stop=10,
        max_departures_per_route=2,
        show_ungrouped=False,
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    assert len(groups) == 1
    assert groups[0][0] == "->East"
    # Should only match U2 to Messestadt Ost, not U2 to Feldmoching or U3 to Messestadt
    assert len(groups[0][1]) == 1
    assert groups[0][1][0].line == "U2"
    assert "Messestadt" in groups[0][1][0].destination


@pytest.mark.asyncio
async def test_pattern_matching_route_only() -> None:
    """Given a pattern like 'U2', when matching, then it matches any destination for that route."""
    now = datetime.now(UTC)
    departures = [
        Departure(
            time=now + timedelta(minutes=5),
            planned_time=now + timedelta(minutes=5),
            delay_seconds=0,
            platform=1,
            is_realtime=True,
            line="U2",
            destination="Messestadt Ost",
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
            line="U2",
            destination="Feldmoching",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(minutes=15),
            planned_time=now + timedelta(minutes=15),
            delay_seconds=0,
            platform=1,
            is_realtime=True,
            line="U3",
            destination="Messestadt Ost",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
    ]

    stop_config = StopConfiguration(
        station_id="de:09162:1110",
        station_name="Giesing",
        direction_mappings={"->East": ["U2"]},  # Route only
        max_departures_per_stop=10,
        max_departures_per_route=2,
        show_ungrouped=False,
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    assert len(groups) == 1
    assert groups[0][0] == "->East"
    # Should match both U2 departures, but not U3
    assert len(groups[0][1]) == 2
    assert all(d.line == "U2" for d in groups[0][1])


@pytest.mark.asyncio
async def test_pattern_matching_destination_only() -> None:
    """Given a pattern like 'Messestadt', when matching, then it matches any route to that destination."""
    now = datetime.now(UTC)
    departures = [
        Departure(
            time=now + timedelta(minutes=5),
            planned_time=now + timedelta(minutes=5),
            delay_seconds=0,
            platform=1,
            is_realtime=True,
            line="U2",
            destination="Messestadt Ost",
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
            destination="Messestadt Ost",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(minutes=15),
            planned_time=now + timedelta(minutes=15),
            delay_seconds=0,
            platform=1,
            is_realtime=True,
            line="U2",
            destination="Feldmoching",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
    ]

    stop_config = StopConfiguration(
        station_id="de:09162:1110",
        station_name="Giesing",
        direction_mappings={"->East": ["Messestadt"]},  # Destination only
        max_departures_per_stop=10,
        max_departures_per_route=2,
        show_ungrouped=False,
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    assert len(groups) == 1
    assert groups[0][0] == "->East"
    # Should match both Messestadt departures (U2 and U3), but not U2 to Feldmoching
    assert len(groups[0][1]) == 2
    assert all("Messestadt" in d.destination for d in groups[0][1])


@pytest.mark.asyncio
async def test_pattern_matching_bus_with_transport_type() -> None:
    """Given a pattern like 'Bus 59 Giesing', when matching, then it matches correctly."""
    now = datetime.now(UTC)
    departures = [
        Departure(
            time=now + timedelta(minutes=5),
            planned_time=now + timedelta(minutes=5),
            delay_seconds=0,
            platform=1,
            is_realtime=True,
            line="59",
            destination="Giesing Bahnhof",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(minutes=10),
            planned_time=now + timedelta(minutes=10),
            delay_seconds=0,
            platform=1,
            is_realtime=True,
            line="59",
            destination="Other Destination",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        ),
    ]

    stop_config = StopConfiguration(
        station_id="de:09162:1110",
        station_name="Giesing",
        direction_mappings={"->Giesing": ["Bus 59 Giesing"]},
        max_departures_per_stop=10,
        max_departures_per_route=2,
        show_ungrouped=False,
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    assert len(groups) == 1
    assert groups[0][0] == "->Giesing"
    # Should only match Bus 59 to Giesing, not Bus 59 to Other
    assert len(groups[0][1]) == 1
    assert "Giesing" in groups[0][1][0].destination


@pytest.mark.asyncio
async def test_direction_order_preserved() -> None:
    """Given multiple directions, when grouped, then directions appear in config order."""
    now = datetime.now(UTC)
    departures = [
        Departure(
            time=now + timedelta(minutes=5),
            planned_time=now + timedelta(minutes=5),
            delay_seconds=0,
            platform=1,
            is_realtime=True,
            line="U2",
            destination="Messestadt",
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
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
    ]

    # Note: order in dict matters in Python 3.7+
    stop_config = StopConfiguration(
        station_id="de:09162:1110",
        station_name="Giesing",
        direction_mappings={
            "->First": ["Messestadt"],
            "->Second": ["Giesing"],
        },
        max_departures_per_stop=10,
        max_departures_per_route=2,
        show_ungrouped=False,
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    # Should preserve order from direction_mappings
    assert len(groups) == 2
    assert groups[0][0] == "->First"
    assert groups[1][0] == "->Second"


@pytest.mark.asyncio
async def test_show_ungrouped_false_hides_other() -> None:
    """Given show_ungrouped=False, when grouped, then unmatched departures are not shown."""
    now = datetime.now(UTC)
    departures = [
        Departure(
            time=now + timedelta(minutes=5),
            planned_time=now + timedelta(minutes=5),
            delay_seconds=0,
            platform=1,
            is_realtime=True,
            line="U2",
            destination="Messestadt",
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
            destination="Unknown",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
    ]

    stop_config = StopConfiguration(
        station_id="de:09162:1110",
        station_name="Giesing",
        direction_mappings={"->East": ["Messestadt"]},
        max_departures_per_stop=10,
        max_departures_per_route=2,
        show_ungrouped=False,  # Don't show unmatched
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    # Should only have ->East, not "Other"
    assert len(groups) == 1
    assert groups[0][0] == "->East"
    assert len(groups[0][1]) == 1


@pytest.mark.asyncio
async def test_show_ungrouped_true_shows_other() -> None:
    """Given show_ungrouped=True, when grouped, then unmatched departures appear in 'Other'."""
    now = datetime.now(UTC)
    departures = [
        Departure(
            time=now + timedelta(minutes=5),
            planned_time=now + timedelta(minutes=5),
            delay_seconds=0,
            platform=1,
            is_realtime=True,
            line="U2",
            destination="Messestadt",
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
            destination="Unknown",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
    ]

    stop_config = StopConfiguration(
        station_id="de:09162:1110",
        station_name="Giesing",
        direction_mappings={"->East": ["Messestadt"]},
        max_departures_per_stop=10,
        max_departures_per_route=2,
        show_ungrouped=True,  # Show unmatched
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    # Should have ->East and Other
    assert len(groups) == 2
    assert groups[0][0] == "->East"
    assert groups[1][0] == "Other"
    assert len(groups[1][1]) == 1
    assert groups[1][1][0].destination == "Unknown"


@pytest.mark.asyncio
async def test_ungrouped_also_filtered_by_route() -> None:
    """Given ungrouped departures, when filtered, then max_departures_per_route applies."""
    now = datetime.now(UTC)
    # Create 5 ungrouped departures of the same route
    departures = [
        Departure(
            time=now + timedelta(minutes=i),
            planned_time=now + timedelta(minutes=i),
            delay_seconds=0,
            platform=1,
            is_realtime=True,
            line="N43",
            destination="Unknown",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        )
        for i in range(1, 6)  # 5 departures
    ]

    stop_config = StopConfiguration(
        station_id="de:09162:1110",
        station_name="Giesing",
        direction_mappings={"->East": ["Messestadt"]},  # None match
        max_departures_per_stop=10,
        max_departures_per_route=2,  # Only 2 per route
        show_ungrouped=True,
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    assert len(groups) == 1
    assert groups[0][0] == "Other"
    # Should only have 2 (max_departures_per_route), not 5
    assert len(groups[0][1]) == 2


@pytest.mark.asyncio
async def test_empty_direction_mappings_shows_all_as_ungrouped() -> None:
    """Given empty direction_mappings, when grouped, then all departures appear in Other."""
    now = datetime.now(UTC)
    departures = [
        Departure(
            time=now + timedelta(minutes=5),
            planned_time=now + timedelta(minutes=5),
            delay_seconds=0,
            platform=1,
            is_realtime=True,
            line="U2",
            destination="Messestadt",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
    ]

    stop_config = StopConfiguration(
        station_id="de:09162:1110",
        station_name="Giesing",
        direction_mappings={},  # Empty
        max_departures_per_stop=10,
        max_departures_per_route=2,
        show_ungrouped=True,
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    # Should have Other group if show_ungrouped is True
    assert len(groups) == 1
    assert groups[0][0] == "Other"
    assert len(groups[0][1]) == 1
