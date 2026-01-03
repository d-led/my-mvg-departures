"""Tests for CLI helper functions with typed configuration."""

from typing import Any

import pytest

from mvg_departures.cli import (
    RouteEntryConfig,
    StationResultData,
    _build_station_result,
    _initialize_route_entry,
)
from mvg_departures.cli_db import (
    RouteProcessingConfig,
    SubStopConfig,
    _process_route,
    _process_sub_stop,
)


def test_route_entry_config_creation() -> None:
    """Given route information, when creating RouteEntryConfig, then all fields are set."""
    config = RouteEntryConfig(
        route_key="U-Bahn U3",
        line="U3",
        transport_type="U-Bahn",
        icon="mdi:subway",
    )

    assert config.route_key == "U-Bahn U3"
    assert config.line == "U3"
    assert config.transport_type == "U-Bahn"
    assert config.icon == "mdi:subway"


def test_route_entry_config_is_frozen() -> None:
    """Given RouteEntryConfig, when trying to modify, then raises AttributeError."""
    config = RouteEntryConfig(route_key="test", line="L1", transport_type="Bus", icon="mdi:bus")

    with pytest.raises(AttributeError):
        config.line = "L2"


def test_initialize_route_entry_creates_new_entry() -> None:
    """Given a new route key, when initializing route entry, then creates entry in both dicts."""
    routes: dict[str, set[str]] = {}
    route_details: dict[str, dict[str, Any]] = {}
    config = RouteEntryConfig(
        route_key="U-Bahn U3",
        line="U3",
        transport_type="U-Bahn",
        icon="mdi:subway",
    )

    _initialize_route_entry(routes, route_details, config)

    assert "U-Bahn U3" in routes
    assert routes["U-Bahn U3"] == set()
    assert "U-Bahn U3" in route_details
    assert route_details["U-Bahn U3"]["line"] == "U3"
    assert route_details["U-Bahn U3"]["transport_type"] == "U-Bahn"
    assert route_details["U-Bahn U3"]["icon"] == "mdi:subway"


def test_initialize_route_entry_does_not_overwrite_existing() -> None:
    """Given an existing route key, when initializing, then does not overwrite existing entry."""
    routes: dict[str, set[str]] = {"U-Bahn U3": {"Giesing"}}
    route_details: dict[str, dict[str, Any]] = {
        "U-Bahn U3": {"line": "U3", "transport_type": "U-Bahn", "icon": "old"}
    }
    config = RouteEntryConfig(
        route_key="U-Bahn U3",
        line="U3",
        transport_type="U-Bahn",
        icon="mdi:subway",
    )

    _initialize_route_entry(routes, route_details, config)

    assert routes["U-Bahn U3"] == {"Giesing"}  # Preserved
    assert route_details["U-Bahn U3"]["icon"] == "old"  # Preserved


def test_station_result_data_creation() -> None:
    """Given all data, when creating StationResultData, then all fields are set."""
    routes = {"U-Bahn U3": {"Giesing", "Olympiazentrum"}}
    route_details = {"U-Bahn U3": {"line": "U3", "transport_type": "U-Bahn", "icon": "mdi:subway"}}
    stop_point_mapping = {"de:09162:70": {"name": "Universität"}}
    departures = [{"line": "U3", "destination": "Giesing"}]
    routes_from_endpoint = {"U3": {"destinations": ["Giesing"]}}

    data = StationResultData(
        station_id="de:09162:70",
        routes=routes,
        route_details=route_details,
        stop_point_mapping=stop_point_mapping,
        departures=departures,
        routes_from_endpoint=routes_from_endpoint,
    )

    assert data.station_id == "de:09162:70"
    assert data.routes == routes
    assert data.route_details == route_details
    assert data.stop_point_mapping == stop_point_mapping
    assert data.departures == departures
    assert data.routes_from_endpoint == routes_from_endpoint


def test_station_result_data_is_frozen() -> None:
    """Given StationResultData, when trying to modify, then raises AttributeError."""
    data = StationResultData(
        station_id="test",
        routes={},
        route_details={},
        stop_point_mapping={},
        departures=[],
        routes_from_endpoint=None,
    )

    with pytest.raises(AttributeError):
        data.station_id = "modified"


def test_build_station_result_with_routes_endpoint() -> None:
    """Given station data with routes endpoint, when building result, then includes both sources."""
    data = StationResultData(
        station_id="de:09162:70",
        routes={"U-Bahn U3": {"Giesing"}},
        route_details={
            "U-Bahn U3": {"line": "U3", "transport_type": "U-Bahn", "icon": "mdi:subway"}
        },
        stop_point_mapping={},
        departures=[{"line": "U3"}],
        routes_from_endpoint={"U3": {}},
    )

    result = _build_station_result(data)

    assert result["station"]["id"] == "de:09162:70"
    assert result["station"]["place"] == "München"
    assert "U-Bahn U3" in result["routes"]
    assert result["routes"]["U-Bahn U3"]["destinations"] == ["Giesing"]
    assert result["total_departures_found"] == 1
    assert "routes_endpoint" in result["source"]


def test_build_station_result_without_routes_endpoint() -> None:
    """Given station data without routes endpoint, when building result, then uses only departures source."""
    data = StationResultData(
        station_id="de:09162:70",
        routes={"U-Bahn U3": {"Giesing"}},
        route_details={
            "U-Bahn U3": {"line": "U3", "transport_type": "U-Bahn", "icon": "mdi:subway"}
        },
        stop_point_mapping={},
        departures=[{"line": "U3"}],
        routes_from_endpoint=None,
    )

    result = _build_station_result(data)

    assert result["source"] == "departures_sampling"
    assert "routes_endpoint" not in result["source"]


def test_build_station_result_sorts_destinations() -> None:
    """Given routes with unsorted destinations, when building result, then destinations are sorted."""
    data = StationResultData(
        station_id="de:09162:70",
        routes={"U-Bahn U3": {"Olympiazentrum", "Giesing", "Moosach"}},
        route_details={
            "U-Bahn U3": {"line": "U3", "transport_type": "U-Bahn", "icon": "mdi:subway"}
        },
        stop_point_mapping={},
        departures=[],
        routes_from_endpoint=None,
    )

    result = _build_station_result(data)

    assert result["routes"]["U-Bahn U3"]["destinations"] == ["Giesing", "Moosach", "Olympiazentrum"]


def test_sub_stop_config_creation() -> None:
    """Given sub-stop information, when creating SubStopConfig, then all fields are set."""
    config = SubStopConfig(
        stop_point_id="de:09162:70:1",
        line="U3",
        transport_type="U-Bahn",
        destination="Giesing",
    )

    assert config.stop_point_id == "de:09162:70:1"
    assert config.line == "U3"
    assert config.transport_type == "U-Bahn"
    assert config.destination == "Giesing"


def test_sub_stop_config_with_none_destination() -> None:
    """Given sub-stop without destination, when creating SubStopConfig, then destination is None."""
    config = SubStopConfig(
        stop_point_id="de:09162:70:1",
        line="U3",
        transport_type="U-Bahn",
        destination=None,
    )

    assert config.destination is None


def test_sub_stop_config_is_frozen() -> None:
    """Given SubStopConfig, when trying to modify, then raises AttributeError."""
    config = SubStopConfig(
        stop_point_id="test", line="L1", transport_type="Bus", destination="Dest"
    )

    with pytest.raises(AttributeError):
        config.line = "L2"


def test_process_sub_stop_creates_new_entry() -> None:
    """Given a new stop point ID, when processing sub-stop, then creates entry."""
    sub_stops: dict[str, dict[str, Any]] = {}
    config = SubStopConfig(
        stop_point_id="de:09162:70:1",
        line="U3",
        transport_type="U-Bahn",
        destination="Giesing",
    )

    _process_sub_stop(config, sub_stops)

    assert "de:09162:70:1" in sub_stops
    assert sub_stops["de:09162:70:1"]["id"] == "de:09162:70:1"
    assert "U-Bahn" in sub_stops["de:09162:70:1"]["transport_types"]
    assert "U3" in sub_stops["de:09162:70:1"]["routes"]
    assert "Giesing" in sub_stops["de:09162:70:1"]["routes"]["U3"]["destinations"]


def test_process_sub_stop_adds_to_existing_entry() -> None:
    """Given an existing stop point, when processing another route, then adds to existing entry."""
    sub_stops: dict[str, dict[str, Any]] = {
        "de:09162:70:1": {
            "id": "de:09162:70:1",
            "routes": {
                "U3": {"line": "U3", "transport_type": "U-Bahn", "destinations": {"Giesing"}}
            },
            "transport_types": {"U-Bahn"},
        }
    }
    config = SubStopConfig(
        stop_point_id="de:09162:70:1",
        line="U6",
        transport_type="U-Bahn",
        destination="Klinikum Großhadern",
    )

    _process_sub_stop(config, sub_stops)

    assert "U6" in sub_stops["de:09162:70:1"]["routes"]
    assert "Klinikum Großhadern" in sub_stops["de:09162:70:1"]["routes"]["U6"]["destinations"]
    assert "U3" in sub_stops["de:09162:70:1"]["routes"]  # Preserved


def test_process_sub_stop_with_none_destination() -> None:
    """Given sub-stop without destination, when processing, then does not add destination."""
    sub_stops: dict[str, dict[str, Any]] = {}
    config = SubStopConfig(
        stop_point_id="de:09162:70:1",
        line="U3",
        transport_type="U-Bahn",
        destination=None,
    )

    _process_sub_stop(config, sub_stops)

    assert sub_stops["de:09162:70:1"]["routes"]["U3"]["destinations"] == set()


def test_route_processing_config_creation() -> None:
    """Given route information, when creating RouteProcessingConfig, then all fields are set."""
    config = RouteProcessingConfig(
        line="U3",
        transport_type="U-Bahn",
        destination="Giesing",
        stop_point_id="de:09162:70:1",
    )

    assert config.line == "U3"
    assert config.transport_type == "U-Bahn"
    assert config.destination == "Giesing"
    assert config.stop_point_id == "de:09162:70:1"


def test_route_processing_config_with_none_values() -> None:
    """Given route without destination or stop point, when creating config, then None values are allowed."""
    config = RouteProcessingConfig(
        line="U3",
        transport_type="U-Bahn",
        destination=None,
        stop_point_id=None,
    )

    assert config.destination is None
    assert config.stop_point_id is None


def test_route_processing_config_is_frozen() -> None:
    """Given RouteProcessingConfig, when trying to modify, then raises AttributeError."""
    config = RouteProcessingConfig(
        line="U3", transport_type="U-Bahn", destination="Giesing", stop_point_id="test"
    )

    with pytest.raises(AttributeError):
        config.line = "U6"


def test_process_route_creates_new_entry() -> None:
    """Given a new route, when processing, then creates entry."""
    routes: dict[str, dict[str, Any]] = {}
    config = RouteProcessingConfig(
        line="U3",
        transport_type="U-Bahn",
        destination="Giesing",
        stop_point_id="de:09162:70:1",
    )

    _process_route(config, routes)

    assert "U3" in routes
    assert routes["U3"]["transport_type"] == "U-Bahn"
    assert routes["U3"]["line"] == "U3"
    assert "Giesing" in routes["U3"]["destinations"]
    assert "de:09162:70:1" in routes["U3"]["stop_points"]


def test_process_route_adds_to_existing_entry() -> None:
    """Given an existing route, when processing another departure, then adds to existing entry."""
    routes: dict[str, dict[str, Any]] = {
        "U3": {
            "transport_type": "U-Bahn",
            "line": "U3",
            "destinations": {"Giesing"},
            "stop_points": {"de:09162:70:1"},
        }
    }
    config = RouteProcessingConfig(
        line="U3",
        transport_type="U-Bahn",
        destination="Olympiazentrum",
        stop_point_id="de:09162:70:2",
    )

    _process_route(config, routes)

    assert "Giesing" in routes["U3"]["destinations"]  # Preserved
    assert "Olympiazentrum" in routes["U3"]["destinations"]  # Added
    assert "de:09162:70:1" in routes["U3"]["stop_points"]  # Preserved
    assert "de:09162:70:2" in routes["U3"]["stop_points"]  # Added


def test_process_route_with_none_destination() -> None:
    """Given route without destination, when processing, then does not add destination."""
    routes: dict[str, dict[str, Any]] = {}
    config = RouteProcessingConfig(
        line="U3",
        transport_type="U-Bahn",
        destination=None,
        stop_point_id="de:09162:70:1",
    )

    _process_route(config, routes)

    assert routes["U3"]["destinations"] == set()
    assert "de:09162:70:1" in routes["U3"]["stop_points"]


def test_process_route_with_none_stop_point() -> None:
    """Given route without stop point, when processing, then does not add stop point."""
    routes: dict[str, dict[str, Any]] = {}
    config = RouteProcessingConfig(
        line="U3",
        transport_type="U-Bahn",
        destination="Giesing",
        stop_point_id=None,
    )

    _process_route(config, routes)

    assert "Giesing" in routes["U3"]["destinations"]
    assert routes["U3"]["stop_points"] == set()
