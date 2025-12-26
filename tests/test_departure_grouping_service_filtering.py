"""Tests for DepartureGroupingService filtering and limiting logic."""

from datetime import UTC, datetime, timedelta

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
    direction_names = [name for name, _ in result]
    assert "->City" in direction_names
    assert "Other" in direction_names

    # Check that route 54 is not in any group
    all_departures = [dep for _, deps in result for dep in deps]
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
    all_departures = [dep for _, deps in result for dep in deps]
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
    all_departures = [dep for _, deps in result for dep in deps]
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
    all_departures = [dep for _, deps in result for dep in deps]
    assert len(all_departures) == 2
    assert any(dep.line == "U3" for dep in all_departures)
    assert any(dep.line == "54" for dep in all_departures)
