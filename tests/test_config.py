"""Tests for configuration adapter."""

import json
import os

import pytest

from mvg_departures.adapters.config import AppConfig


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


def test_config_validates_stops_config_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Given invalid JSON in stops config, when loading config, then validation error is raised."""
    monkeypatch.setenv("STOPS_CONFIG", "invalid json")

    with pytest.raises(ValueError, match="stops_config must be valid JSON"):
        AppConfig()


def test_config_parses_stops_config() -> None:
    """Given valid stops config JSON, when loading config, then it can be parsed."""
    stops_data = [
        {
            "station_id": "de:09162:70",
            "station_name": "Universität",
            "direction_mappings": {"->Giesing": ["Giesing"]},
        }
    ]
    config = AppConfig(stops_config=json.dumps(stops_data))

    parsed = config.get_stops_config()
    assert len(parsed) == 1
    assert parsed[0]["station_id"] == "de:09162:70"
    assert parsed[0]["station_name"] == "Universität"


