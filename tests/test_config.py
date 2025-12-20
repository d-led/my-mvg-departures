"""Tests for configuration adapter."""

from pathlib import Path
from tempfile import NamedTemporaryFile

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


