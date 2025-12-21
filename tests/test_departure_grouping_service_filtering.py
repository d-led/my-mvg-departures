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
