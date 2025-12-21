"""Tests for configuration adapter."""

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from mvg_departures.adapters.config import AppConfig
from mvg_departures.adapters.config.route_configuration_loader import (
    RouteConfigurationLoader,
)


def test_config_loads_defaults() -> None:
    """Given no environment variables, when loading config, then defaults are used."""
    config = AppConfig()

    assert config.host == "0.0.0.0"
    assert config.port == 8000
    assert config.reload is False
    assert config.time_format == "minutes"


def test_config_loads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Given environment variables, when loading config, then they are used."""
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("TIME_FORMAT", "at")

    config = AppConfig()

    assert config.host == "127.0.0.1"
    assert config.port == 9000
    assert config.time_format == "at"


def test_config_validates_time_format(monkeypatch: pytest.MonkeyPatch) -> None:
    """Given invalid time format, when loading config, then validation error is raised."""
    monkeypatch.setenv("TIME_FORMAT", "invalid")

    with pytest.raises(ValueError, match="time_format must be either"):
        AppConfig()


def test_config_parses_stops_config_from_toml() -> None:
    """Given valid TOML config file, when loading config, then it can be parsed."""
    toml_content = """
[[stops]]
station_id = "de:09162:70"
station_name = "Universität"

[stops.direction_mappings]
"->Giesing" = ["Giesing"]
"""
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        temp_path = f.name

    try:
        config = AppConfig(config_file=temp_path)
        parsed = config.get_stops_config()
        assert len(parsed) == 1
        assert parsed[0]["station_id"] == "de:09162:70"
        assert parsed[0]["station_name"] == "Universität"
    finally:
        Path(temp_path).unlink()


def test_config_raises_error_when_file_not_found() -> None:
    """Given non-existent config file, when loading config, then FileNotFoundError is raised."""
    config = AppConfig(config_file="nonexistent.toml")

    with pytest.raises(FileNotFoundError, match="Configuration file not found"):
        config.get_stops_config()


def test_config_raises_error_when_config_file_not_set() -> None:
    """Given config_file is None, when loading config, then ValueError is raised."""
    config = AppConfig(config_file=None)

    with pytest.raises(ValueError, match="config_file must be set"):
        config.get_stops_config()


def test_config_parses_routes_config_from_toml() -> None:
    """Given valid TOML config file with routes, when loading config, then routes are parsed."""
    toml_content = """
[[routes]]
path = "/"

[[routes.stops]]
station_id = "de:09162:70"
station_name = "Universität"

[routes.stops.direction_mappings]
"->Giesing" = ["Giesing"]
"""
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        temp_path = f.name

    try:
        config = AppConfig(config_file=temp_path)
        routes = config.get_routes_config()
        assert len(routes) == 1
        assert routes[0]["path"] == "/"
        assert len(routes[0]["stops"]) == 1
        assert routes[0]["stops"][0]["station_id"] == "de:09162:70"
    finally:
        Path(temp_path).unlink()


def test_config_creates_default_route_when_no_routes_defined() -> None:
    """Given TOML config with stops but no routes, when loading config, then default route is created."""
    toml_content = """
[[stops]]
station_id = "de:09162:70"
station_name = "Universität"
"""
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        temp_path = f.name

    try:
        config = AppConfig(config_file=temp_path)
        routes = config.get_routes_config()
        assert len(routes) == 1
        assert routes[0]["path"] == "/"
        assert len(routes[0]["stops"]) == 1
        assert routes[0]["stops"][0]["station_id"] == "de:09162:70"
    finally:
        Path(temp_path).unlink()


def test_config_validates_unique_route_paths() -> None:
    """Given TOML config with duplicate route paths, when loading config, then ValueError is raised."""
    toml_content = """
[[routes]]
path = "/route1"

[[routes.stops]]
station_id = "de:09162:70"
station_name = "Universität"

[[routes]]
path = "/route1"

[[routes.stops]]
station_id = "de:09162:71"
station_name = "Another"
"""
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        temp_path = f.name

    try:
        config = AppConfig(config_file=temp_path)
        with pytest.raises(ValueError, match="Route paths must be unique"):
            config.get_routes_config()
    finally:
        Path(temp_path).unlink()


def test_config_validates_route_has_path() -> None:
    """Given TOML config with route missing path, when loading config, then ValueError is raised."""
    toml_content = """
[[routes]]
# path missing

[[routes.stops]]
station_id = "de:09162:70"
station_name = "Universität"
"""
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        temp_path = f.name

    try:
        config = AppConfig(config_file=temp_path)
        with pytest.raises(ValueError, match="All routes must have a 'path' field"):
            config.get_routes_config()
    finally:
        Path(temp_path).unlink()


def test_route_configuration_loader_loads_routes() -> None:
    """Given valid route config, when loading route configurations, then RouteConfiguration objects are created."""
    toml_content = """
[[routes]]
path = "/route1"

[[routes.stops]]
station_id = "de:09162:70"
station_name = "Universität"
max_departures_per_stop = 10

[[routes]]
path = "/route2"

[[routes.stops]]
station_id = "de:09162:71"
station_name = "Another"
"""
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        temp_path = f.name

    try:
        config = AppConfig(config_file=temp_path)
        route_configs = RouteConfigurationLoader.load(config)
        assert len(route_configs) == 2
        assert route_configs[0].path == "/route1"
        assert len(route_configs[0].stop_configs) == 1
        assert route_configs[0].stop_configs[0].station_id == "de:09162:70"
        assert route_configs[1].path == "/route2"
        assert len(route_configs[1].stop_configs) == 1
        assert route_configs[1].stop_configs[0].station_id == "de:09162:71"
    finally:
        Path(temp_path).unlink()


def test_config_supports_mixed_formats() -> None:
    """Given TOML config with both [[stops]] and [[routes]], when loading config, then both are combined."""
    toml_content = """
[[stops]]
station_id = "de:09162:70"
station_name = "Default Stop"

[[routes]]
path = "/additional"

[[routes.stops]]
station_id = "de:09162:71"
station_name = "Additional Stop"
"""
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        temp_path = f.name

    try:
        config = AppConfig(config_file=temp_path)
        routes = config.get_routes_config()
        assert len(routes) == 2
        # Default route from stops should be first
        assert routes[0]["path"] == "/"
        assert len(routes[0]["stops"]) == 1
        assert routes[0]["stops"][0]["station_id"] == "de:09162:70"
        # Additional route should be second
        assert routes[1]["path"] == "/additional"
        assert len(routes[1]["stops"]) == 1
        assert routes[1]["stops"][0]["station_id"] == "de:09162:71"
    finally:
        Path(temp_path).unlink()


def test_config_rejects_duplicate_path_when_mixing_formats() -> None:
    """Given TOML config with [[stops]] and [[routes]] with path="/", when loading config, then ValueError is raised."""
    toml_content = """
[[stops]]
station_id = "de:09162:70"
station_name = "Default Stop"

[[routes]]
path = "/"

[[routes.stops]]
station_id = "de:09162:71"
station_name = "Additional Stop"
"""
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        temp_path = f.name

    try:
        config = AppConfig(config_file=temp_path)
        with pytest.raises(ValueError, match="Route paths must be unique"):
            config.get_routes_config()
    finally:
        Path(temp_path).unlink()
