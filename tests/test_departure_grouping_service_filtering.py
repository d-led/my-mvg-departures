"""Tests for DepartureGroupingService filtering and limiting logic."""

from datetime import UTC, datetime, timedelta

import pytest

from mvg_departures.application.services import DepartureGroupingService
from mvg_departures.domain.models import Departure, StopConfiguration
from tests.test_services import MockDepartureRepository


def test_filter_and_limit_departures_applies_leeway_filter() -> None:
    """Given departures with leeway configured, when filtering, then excludes departures too soon."""
    service = DepartureGroupingService(MockDepartureRepository([]))
    now = datetime.now(UTC)

    stop_config = StopConfiguration(
        station_id="de:09162:70",
        station_name="Test Station",
        direction_mappings={},
        departure_leeway_minutes=5,
    )

    departures = [
        Departure(
            time=now + timedelta(minutes=3),  # Too soon
            planned_time=now + timedelta(minutes=3),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(minutes=10),  # OK
            planned_time=now + timedelta(minutes=10),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
    ]

    result = service._filter_and_limit_departures(departures, stop_config)

    assert len(result) == 1
    assert result[0].time == now + timedelta(minutes=10)


def test_filter_and_limit_departures_applies_route_limit() -> None:
    """Given departures from same route, when filtering, then limits per route."""
    service = DepartureGroupingService(MockDepartureRepository([]))
    now = datetime.now(UTC)

    stop_config = StopConfiguration(
        station_id="de:09162:70",
        station_name="Test Station",
        direction_mappings={},
        max_departures_per_route=2,
    )

    departures = [
        Departure(
            time=now + timedelta(minutes=i),
            planned_time=now + timedelta(minutes=i),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        )
        for i in range(5)  # 5 departures from U3
    ]

    result = service._filter_and_limit_departures(departures, stop_config)

    assert len(result) == 2
    assert all(dep.line == "U3" for dep in result)


def test_filter_and_limit_departures_applies_direction_limit() -> None:
    """Given many departures, when filtering, then limits to max_departures_per_stop."""
    service = DepartureGroupingService(MockDepartureRepository([]))
    now = datetime.now(UTC)

    stop_config = StopConfiguration(
        station_id="de:09162:70",
        station_name="Test Station",
        direction_mappings={},
        max_departures_per_stop=3,
    )

    departures = [
        Departure(
            time=now + timedelta(minutes=i),
            planned_time=now + timedelta(minutes=i),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line=f"U{i % 3}",  # Mix of routes
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        )
        for i in range(10)  # 10 departures
    ]

    result = service._filter_and_limit_departures(departures, stop_config)

    assert len(result) == 3


def test_filter_and_limit_departures_applies_all_filters_together() -> None:
    """Given departures, when filtering, then applies leeway, route limit, and direction limit."""
    service = DepartureGroupingService(MockDepartureRepository([]))
    now = datetime.now(UTC)

    stop_config = StopConfiguration(
        station_id="de:09162:70",
        station_name="Test Station",
        direction_mappings={},
        departure_leeway_minutes=5,
        max_departures_per_route=1,
        max_departures_per_stop=2,
    )

    departures = [
        # Too soon - should be filtered out
        Departure(
            time=now + timedelta(minutes=3),
            planned_time=now + timedelta(minutes=3),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
        # OK - U3 #1
        Departure(
            time=now + timedelta(minutes=10),
            planned_time=now + timedelta(minutes=10),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
        # OK but second U3 - should be filtered by route limit
        Departure(
            time=now + timedelta(minutes=11),
            planned_time=now + timedelta(minutes=11),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
        # OK - U6 #1
        Departure(
            time=now + timedelta(minutes=12),
            planned_time=now + timedelta(minutes=12),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U6",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
        # OK but third overall - should be filtered by direction limit
        Departure(
            time=now + timedelta(minutes=13),
            planned_time=now + timedelta(minutes=13),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U6",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
    ]

    result = service._filter_and_limit_departures(departures, stop_config)

    assert len(result) == 2
    assert result[0].line == "U3"
    assert result[1].line == "U6"


def test_filter_and_limit_departures_with_no_leeway() -> None:
    """Given no leeway configured, when filtering, then includes all future departures."""
    service = DepartureGroupingService(MockDepartureRepository([]))
    now = datetime.now(UTC)

    stop_config = StopConfiguration(
        station_id="de:09162:70",
        station_name="Test Station",
        direction_mappings={},
        departure_leeway_minutes=0,
    )

    departures = [
        Departure(
            time=now + timedelta(minutes=1),  # Very soon, but no leeway filter
            planned_time=now + timedelta(minutes=1),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
    ]

    result = service._filter_and_limit_departures(departures, stop_config)

    assert len(result) == 1


def test_group_departures_excludes_blacklisted_route() -> None:
    """Given departures with blacklisted route, when grouping, then excludes blacklisted departures."""
    service = DepartureGroupingService(MockDepartureRepository([]))
    now = datetime.now(UTC)

    stop_config = StopConfiguration(
        station_id="de:09162:70",
        station_name="Test Station",
        direction_mappings={"->City": ["U3"]},
        exclude_destinations=["54"],  # Blacklist route 54
        show_ungrouped=True,
    )

    departures = [
        Departure(
            time=now + timedelta(minutes=10),
            planned_time=now + timedelta(minutes=10),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(minutes=11),
            planned_time=now + timedelta(minutes=11),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="54",
            destination="Münchner Freiheit",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(minutes=12),
            planned_time=now + timedelta(minutes=12),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U6",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
    ]

    result = service.group_departures(departures, stop_config)

    # Should have U3 in ->City group and U6 in ungrouped, but not route 54
    assert len(result) == 2
    direction_names = [group.direction_name for group in result]
    assert "->City" in direction_names
    assert "Other" in direction_names

    # Check that route 54 is not in any group
    all_departures = [dep for group in result for dep in group.departures]
    assert not any(dep.line == "54" for dep in all_departures)
    assert any(dep.line == "U3" for dep in all_departures)
    assert any(dep.line == "U6" for dep in all_departures)


def test_group_departures_excludes_blacklisted_destination() -> None:
    """Given departures with blacklisted destination, when grouping, then excludes blacklisted departures."""
    service = DepartureGroupingService(MockDepartureRepository([]))
    now = datetime.now(UTC)

    stop_config = StopConfiguration(
        station_id="de:09162:70",
        station_name="Test Station",
        direction_mappings={"->City": ["U3"]},
        exclude_destinations=["Messestadt"],  # Blacklist destination
        show_ungrouped=True,
    )

    departures = [
        Departure(
            time=now + timedelta(minutes=10),
            planned_time=now + timedelta(minutes=10),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(minutes=11),
            planned_time=now + timedelta(minutes=11),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U2",
            destination="Messestadt Ost",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(minutes=12),
            planned_time=now + timedelta(minutes=12),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U6",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
    ]

    result = service.group_departures(departures, stop_config)

    # Should have U3 in ->City group and U6 in ungrouped, but not U2 to Messestadt
    all_departures = [dep for group in result for dep in group.departures]
    assert not any(dep.destination == "Messestadt Ost" for dep in all_departures)
    assert any(dep.line == "U3" for dep in all_departures)
    assert any(dep.line == "U6" for dep in all_departures)


def test_group_departures_excludes_blacklisted_route_and_destination() -> None:
    """Given departures with blacklisted route+destination, when grouping, then excludes only matching combination."""
    service = DepartureGroupingService(MockDepartureRepository([]))
    now = datetime.now(UTC)

    stop_config = StopConfiguration(
        station_id="de:09162:70",
        station_name="Test Station",
        direction_mappings={"->City": ["U3"]},
        exclude_destinations=["54 Münchner Freiheit"],  # Blacklist specific route+destination
        show_ungrouped=True,
    )

    departures = [
        Departure(
            time=now + timedelta(minutes=10),
            planned_time=now + timedelta(minutes=10),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="54",
            destination="Münchner Freiheit",  # Should be excluded
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(minutes=11),
            planned_time=now + timedelta(minutes=11),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="54",
            destination="Lorettoplatz",  # Should NOT be excluded (different destination)
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(minutes=12),
            planned_time=now + timedelta(minutes=12),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
    ]

    result = service.group_departures(departures, stop_config)

    # Should have U3 in ->City group and route 54 to Lorettoplatz in ungrouped, but not route 54 to Münchner Freiheit
    all_departures = [dep for group in result for dep in group.departures]
    assert not any(
        dep.line == "54" and dep.destination == "Münchner Freiheit" for dep in all_departures
    )
    assert any(dep.line == "54" and dep.destination == "Lorettoplatz" for dep in all_departures)
    assert any(dep.line == "U3" for dep in all_departures)


def test_filter_and_limit_departures_applies_max_hours_in_advance_filter() -> None:
    """Given departures with max_hours_in_advance configured, when filtering, then excludes departures too far in the future."""
    service = DepartureGroupingService(MockDepartureRepository([]))
    now = datetime.now(UTC)

    stop_config = StopConfiguration(
        station_id="de:09162:70",
        station_name="Test Station",
        direction_mappings={},
        max_hours_in_advance=3.0,
    )

    departures = [
        Departure(
            time=now + timedelta(hours=2),  # OK - within 3 hours
            planned_time=now + timedelta(hours=2),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="54",
            destination="Lorettoplatz",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(hours=4),  # Too far - beyond 3 hours
            planned_time=now + timedelta(hours=4),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="N43",
            destination="Ostbahnhof",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        ),
    ]

    result = service._filter_and_limit_departures(departures, stop_config)

    assert len(result) == 1
    assert result[0].line == "54"
    assert result[0].time == now + timedelta(hours=2)


def test_filter_and_limit_departures_with_max_hours_in_advance_unset() -> None:
    """Given departures with max_hours_in_advance unset, when filtering, then shows all departures regardless of time."""
    service = DepartureGroupingService(MockDepartureRepository([]))
    now = datetime.now(UTC)

    stop_config = StopConfiguration(
        station_id="de:09162:70",
        station_name="Test Station",
        direction_mappings={},
        max_hours_in_advance=None,
    )

    departures = [
        Departure(
            time=now + timedelta(hours=2),
            planned_time=now + timedelta(hours=2),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="54",
            destination="Lorettoplatz",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(hours=10),  # Should still be shown
            planned_time=now + timedelta(hours=10),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="N43",
            destination="Ostbahnhof",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        ),
    ]

    result = service._filter_and_limit_departures(departures, stop_config)

    assert len(result) == 2


def test_filter_and_limit_departures_with_max_hours_in_advance_less_than_one() -> None:
    """Given departures with max_hours_in_advance < 1, when filtering, then shows all departures (treated as unset)."""
    service = DepartureGroupingService(MockDepartureRepository([]))
    now = datetime.now(UTC)

    stop_config = StopConfiguration(
        station_id="de:09162:70",
        station_name="Test Station",
        direction_mappings={},
        max_hours_in_advance=0.5,  # < 1, should be treated as None
    )

    departures = [
        Departure(
            time=now + timedelta(hours=2),
            planned_time=now + timedelta(hours=2),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="54",
            destination="Lorettoplatz",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(hours=10),  # Should still be shown
            planned_time=now + timedelta(hours=10),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="N43",
            destination="Ostbahnhof",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        ),
    ]

    result = service._filter_and_limit_departures(departures, stop_config)

    assert len(result) == 2


def test_filter_and_limit_departures_applies_max_hours_in_advance_with_leeway() -> None:
    """Given departures with both leeway and max_hours_in_advance, when filtering, then applies both filters correctly."""
    service = DepartureGroupingService(MockDepartureRepository([]))
    now = datetime.now(UTC)

    stop_config = StopConfiguration(
        station_id="de:09162:70",
        station_name="Test Station",
        direction_mappings={},
        departure_leeway_minutes=5,
        max_hours_in_advance=3.0,
    )

    departures = [
        Departure(
            time=now + timedelta(minutes=3),  # Too soon - filtered by leeway
            planned_time=now + timedelta(minutes=3),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="54",
            destination="Lorettoplatz",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(hours=2),  # OK - within both limits
            planned_time=now + timedelta(hours=2),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="54",
            destination="Lorettoplatz",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(hours=4),  # Too far - filtered by max_hours_in_advance
            planned_time=now + timedelta(hours=4),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="N43",
            destination="Ostbahnhof",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        ),
    ]

    result = service._filter_and_limit_departures(departures, stop_config)

    assert len(result) == 1
    assert result[0].time == now + timedelta(hours=2)
    assert result[0].line == "54"


def test_group_departures_with_empty_blacklist() -> None:
    """Given departures with empty blacklist, when grouping, then includes all departures."""
    service = DepartureGroupingService(MockDepartureRepository([]))
    now = datetime.now(UTC)

    stop_config = StopConfiguration(
        station_id="de:09162:70",
        station_name="Test Station",
        direction_mappings={"->City": ["U3"]},
        exclude_destinations=[],  # Empty blacklist
        show_ungrouped=True,
    )

    departures = [
        Departure(
            time=now + timedelta(minutes=10),
            planned_time=now + timedelta(minutes=10),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(minutes=11),
            planned_time=now + timedelta(minutes=11),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="54",
            destination="Münchner Freiheit",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        ),
    ]

    result = service.group_departures(departures, stop_config)

    # Should have all departures
    all_departures = [dep for group in result for dep in group.departures]
    assert len(all_departures) == 2
    assert any(dep.line == "U3" for dep in all_departures)
    assert any(dep.line == "54" for dep in all_departures)


@pytest.mark.asyncio
async def test_group_departures_returns_empty_when_stop_point_has_no_departures() -> None:
    """Given a stop point that doesn't exist, when grouping, then returns empty list."""
    now = datetime.now(UTC)

    # Departures from different stop points
    departures = [
        Departure(
            time=now + timedelta(minutes=10),
            planned_time=now + timedelta(minutes=10),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
            stop_point_global_id="de:09162:1108:1:1",  # Different stop point
        ),
        Departure(
            time=now + timedelta(minutes=15),
            planned_time=now + timedelta(minutes=15),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
            stop_point_global_id="de:09162:1108:2:2",  # Different stop point
        ),
    ]

    # Stop config for a stop point that doesn't exist in departures
    stop_config = StopConfiguration(
        station_id="de:09162:1108:4:4",  # This stop point doesn't exist
        station_name="Test Station",
        direction_mappings={},
        show_ungrouped=True,
        ungrouped_title="Test",
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    # Should return empty list when no departures match the stop point
    assert len(groups) == 0


@pytest.mark.asyncio
async def test_group_departures_returns_empty_when_all_departures_filtered_out() -> None:
    """Given departures that are all filtered out, when grouping, then returns empty list."""
    now = datetime.now(UTC)

    departures = [
        Departure(
            time=now + timedelta(minutes=10),
            planned_time=now + timedelta(minutes=10),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
    ]

    # Stop config with direction mappings but departures don't match
    stop_config = StopConfiguration(
        station_id="de:09162:70",
        station_name="Test Station",
        direction_mappings={"->City": ["U2"]},  # U3 doesn't match
        show_ungrouped=False,  # Don't show ungrouped
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    # Should return empty list when all departures are filtered out and show_ungrouped is False
    assert len(groups) == 0


@pytest.mark.asyncio
async def test_group_departures_returns_empty_when_ungrouped_filtered_out() -> None:
    """Given show_ungrouped is true but all departures are filtered out, when grouping, then returns empty list."""
    now = datetime.now(UTC)

    departures = [
        Departure(
            time=now + timedelta(minutes=10),
            planned_time=now + timedelta(minutes=10),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
    ]

    # Stop config with show_ungrouped=True but all departures filtered by leeway
    stop_config = StopConfiguration(
        station_id="de:09162:70",
        station_name="Test Station",
        direction_mappings={},
        show_ungrouped=True,
        ungrouped_title="Test",
        departure_leeway_minutes=15,  # Filter out departures within 15 minutes
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    # Should return empty list when all departures are filtered out by leeway
    assert len(groups) == 0


def test_build_result_list_excludes_empty_direction_groups() -> None:
    """Given direction groups with empty departures, when building result list, then excludes empty groups."""
    service = DepartureGroupingService(MockDepartureRepository([]))
    now = datetime.now(UTC)

    stop_config = StopConfiguration(
        station_id="de:09162:70",
        station_name="Test Station",
        direction_mappings={"->City": ["U3"], "->West": ["U6"]},
        show_ungrouped=True,
    )

    # Direction groups with one empty
    direction_groups = {
        "->City": [
            Departure(
                time=now + timedelta(minutes=10),
                planned_time=now + timedelta(minutes=10),
                delay_seconds=None,
                platform=None,
                is_realtime=True,
                line="U3",
                destination="Giesing",
                transport_type="U-Bahn",
                icon="mdi:subway",
                is_cancelled=False,
                messages=[],
            ),
        ],
        "->West": [],  # Empty group
    }
    ungrouped: list[Departure] = []

    result = service._build_result_list(direction_groups, ungrouped, stop_config)

    # Should only include the non-empty group
    assert len(result) == 1
    assert result[0].direction_name == "->City"
    assert len(result[0].departures) == 1


def test_build_result_list_excludes_empty_ungrouped() -> None:
    """Given show_ungrouped is true but ungrouped is empty, when building result list, then excludes ungrouped."""
    service = DepartureGroupingService(MockDepartureRepository([]))

    stop_config = StopConfiguration(
        station_id="de:09162:70",
        station_name="Test Station",
        direction_mappings={},
        show_ungrouped=True,
        ungrouped_title="Test",
    )

    direction_groups: dict[str, list[Departure]] = {}
    ungrouped: list[Departure] = []  # Empty

    result = service._build_result_list(direction_groups, ungrouped, stop_config)

    # Should return empty list when ungrouped is empty
    assert len(result) == 0


@pytest.mark.asyncio
async def test_group_departures_with_direction_mappings_and_ungrouped() -> None:
    """Given direction mappings and show_ungrouped=true, when grouping, then shows both mapped and ungrouped."""
    now = datetime.now(UTC)
    departures = [
        Departure(
            time=now + timedelta(minutes=10),
            planned_time=now + timedelta(minutes=10),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(minutes=15),
            planned_time=now + timedelta(minutes=15),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="54",
            destination="Münchner Freiheit",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        ),
    ]

    stop_config = StopConfiguration(
        station_id="de:09162:70",
        station_name="Test Station",
        direction_mappings={"->Giesing": ["U3"]},
        show_ungrouped=True,
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    # Should have both ->Giesing group and Other group
    assert len(groups) == 2
    direction_names = {g.direction_name for g in groups}
    assert "->Giesing" in direction_names
    assert "Other" in direction_names


@pytest.mark.asyncio
async def test_group_departures_with_direction_mappings_and_blacklist() -> None:
    """Given direction mappings and blacklist, when grouping, then excludes blacklisted from both groups."""
    now = datetime.now(UTC)
    departures = [
        Departure(
            time=now + timedelta(minutes=10),
            planned_time=now + timedelta(minutes=10),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(minutes=11),
            planned_time=now + timedelta(minutes=11),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="54",
            destination="Münchner Freiheit",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(minutes=12),
            planned_time=now + timedelta(minutes=12),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U6",
            destination="Klinikum",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
    ]

    stop_config = StopConfiguration(
        station_id="de:09162:70",
        station_name="Test Station",
        direction_mappings={"->Giesing": ["U3"]},
        exclude_destinations=["54"],  # Blacklist route 54
        show_ungrouped=True,
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    # Should have ->Giesing with U3, and Other with U6, but not route 54
    all_departures = [dep for group in groups for dep in group.departures]
    assert len(all_departures) == 2
    assert any(dep.line == "U3" for dep in all_departures)
    assert any(dep.line == "U6" for dep in all_departures)
    assert not any(dep.line == "54" for dep in all_departures)


@pytest.mark.asyncio
async def test_group_departures_with_direction_mappings_and_leeway() -> None:
    """Given direction mappings and leeway, when grouping, then applies leeway to all groups."""
    now = datetime.now(UTC)
    departures = [
        Departure(
            time=now + timedelta(minutes=3),  # Too soon
            planned_time=now + timedelta(minutes=3),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(minutes=10),  # OK
            planned_time=now + timedelta(minutes=10),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(minutes=4),  # Too soon
            planned_time=now + timedelta(minutes=4),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="54",
            destination="Münchner Freiheit",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(minutes=12),  # OK
            planned_time=now + timedelta(minutes=12),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="54",
            destination="Münchner Freiheit",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        ),
    ]

    stop_config = StopConfiguration(
        station_id="de:09162:70",
        station_name="Test Station",
        direction_mappings={"->Giesing": ["U3"]},
        departure_leeway_minutes=5,
        show_ungrouped=True,
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    # Should only have departures after leeway (10+ minutes)
    all_departures = [dep for group in groups for dep in group.departures]
    assert len(all_departures) == 2
    assert all(dep.time >= now + timedelta(minutes=5) for dep in all_departures)


@pytest.mark.asyncio
async def test_group_departures_with_direction_mappings_and_max_hours() -> None:
    """Given direction mappings and max_hours_in_advance, when grouping, then limits future departures."""
    now = datetime.now(UTC)
    departures = [
        Departure(
            time=now + timedelta(hours=1),
            planned_time=now + timedelta(hours=1),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(hours=4),  # Too far
            planned_time=now + timedelta(hours=4),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        ),
        Departure(
            time=now + timedelta(hours=2),
            planned_time=now + timedelta(hours=2),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="54",
            destination="Münchner Freiheit",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
        ),
    ]

    stop_config = StopConfiguration(
        station_id="de:09162:70",
        station_name="Test Station",
        direction_mappings={"->Giesing": ["U3"]},
        max_hours_in_advance=3,
        show_ungrouped=True,
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    # Should only have departures within 3 hours
    all_departures = [dep for group in groups for dep in group.departures]
    assert len(all_departures) == 2
    assert all((dep.time - now).total_seconds() / 3600 <= 3 for dep in all_departures)


@pytest.mark.asyncio
async def test_group_departures_with_stop_point_and_direction_mappings() -> None:
    """Given stop point filter and direction mappings, when grouping, then filters by stop point first."""
    now = datetime.now(UTC)
    departures = [
        Departure(
            time=now + timedelta(minutes=10),
            planned_time=now + timedelta(minutes=10),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
            stop_point_global_id="de:09162:1108:1:1",
        ),
        Departure(
            time=now + timedelta(minutes=15),
            planned_time=now + timedelta(minutes=15),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
            stop_point_global_id="de:09162:1108:2:2",  # Different stop point
        ),
    ]

    stop_config = StopConfiguration(
        station_id="de:09162:1108:1:1",  # Filter by stop point
        station_name="Test Station",
        direction_mappings={"->Giesing": ["U3"]},
        show_ungrouped=False,
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    # Should only have departure from stop point 1:1
    all_departures = [dep for group in groups for dep in group.departures]
    assert len(all_departures) == 1
    assert all_departures[0].stop_point_global_id == "de:09162:1108:1:1"


@pytest.mark.asyncio
async def test_group_departures_with_stop_point_and_ungrouped() -> None:
    """Given stop point filter and show_ungrouped=true, when grouping, then filters by stop point then shows ungrouped."""
    now = datetime.now(UTC)
    departures = [
        Departure(
            time=now + timedelta(minutes=10),
            planned_time=now + timedelta(minutes=10),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
            stop_point_global_id="de:09162:1108:1:1",
        ),
        Departure(
            time=now + timedelta(minutes=15),
            planned_time=now + timedelta(minutes=15),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="54",
            destination="Münchner Freiheit",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
            stop_point_global_id="de:09162:1108:1:1",
        ),
    ]

    stop_config = StopConfiguration(
        station_id="de:09162:1108:1:1",
        station_name="Test Station",
        direction_mappings={},
        show_ungrouped=True,
        ungrouped_title="All",
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    # Should have ungrouped group with both departures from stop point 1:1
    assert len(groups) == 1
    assert groups[0].direction_name == "All"
    assert len(groups[0].departures) == 2
    assert all(dep.stop_point_global_id == "de:09162:1108:1:1" for dep in groups[0].departures)


@pytest.mark.asyncio
async def test_group_departures_with_all_filters_combined() -> None:
    """Given all filters combined, when grouping, then applies all filters correctly."""
    now = datetime.now(UTC)
    departures = [
        # Too soon - filtered by leeway
        Departure(
            time=now + timedelta(minutes=3),
            planned_time=now + timedelta(minutes=3),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
            stop_point_global_id="de:09162:1108:1:1",
        ),
        # OK - matches direction mapping
        Departure(
            time=now + timedelta(minutes=10),
            planned_time=now + timedelta(minutes=10),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
            stop_point_global_id="de:09162:1108:1:1",
        ),
        # OK but wrong stop point
        Departure(
            time=now + timedelta(minutes=12),
            planned_time=now + timedelta(minutes=12),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
            stop_point_global_id="de:09162:1108:2:2",
        ),
        # OK but blacklisted
        Departure(
            time=now + timedelta(minutes=15),
            planned_time=now + timedelta(minutes=15),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="54",
            destination="Münchner Freiheit",
            transport_type="Bus",
            icon="mdi:bus",
            is_cancelled=False,
            messages=[],
            stop_point_global_id="de:09162:1108:1:1",
        ),
        # OK - ungrouped
        Departure(
            time=now + timedelta(minutes=20),
            planned_time=now + timedelta(minutes=20),
            delay_seconds=None,
            platform=None,
            is_realtime=True,
            line="U6",
            destination="Klinikum",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
            stop_point_global_id="de:09162:1108:1:1",
        ),
    ]

    stop_config = StopConfiguration(
        station_id="de:09162:1108:1:1",
        station_name="Test Station",
        direction_mappings={"->Giesing": ["U3"]},
        exclude_destinations=["54"],
        departure_leeway_minutes=5,
        show_ungrouped=True,
        max_departures_per_route=1,
    )

    repo = MockDepartureRepository(departures)
    service = DepartureGroupingService(repo)

    groups = await service.get_grouped_departures(stop_config)

    # Should have ->Giesing with U3 and Other with U6, but not:
    # - U3 at 3min (leeway)
    # - U3 at 2:2 (wrong stop point)
    # - Route 54 (blacklisted)
    all_departures = [dep for group in groups for dep in group.departures]
    assert len(all_departures) == 2
    assert any(
        dep.line == "U3" and dep.stop_point_global_id == "de:09162:1108:1:1"
        for dep in all_departures
    )
    assert any(dep.line == "U6" for dep in all_departures)
    assert not any(dep.line == "54" for dep in all_departures)
