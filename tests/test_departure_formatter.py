"""Tests for DepartureFormatter."""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from mvg_departures.adapters.config import AppConfig
from mvg_departures.adapters.web.formatters import DepartureFormatter
from mvg_departures.domain.models import Departure


def test_format_departure_time_minutes_format() -> None:
    """Given a departure in minutes format, when formatting, then returns relative time."""
    with patch.dict(os.environ, {}, clear=True):
        # Use UTC timezone to avoid timezone conversion issues
        config = AppConfig(config_file=None, time_format="minutes", timezone="UTC", _env_file=None)
        formatter = DepartureFormatter(config)

        # Use a large enough delta (10 minutes) to avoid timing issues
        now = datetime.now(UTC)
        departure = Departure(
            time=now + timedelta(minutes=10),
            planned_time=now + timedelta(minutes=10),
            delay_seconds=None,
            platform=None,
            is_realtime=False,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        )

        result = formatter.format_departure_time(departure)
        # Allow for small timing differences (should be 9-10 minutes)
        assert result in ("9m", "10m")


def test_format_departure_time_at_format() -> None:
    """Given a departure in 'at' format, when formatting, then returns absolute time."""
    with patch.dict(os.environ, {}, clear=True):
        # Use UTC timezone to avoid timezone conversion issues
        config = AppConfig(config_file=None, time_format="at", timezone="UTC", _env_file=None)
        formatter = DepartureFormatter(config)

        # Use a fixed UTC time to avoid timezone conversion issues
        departure_time = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        departure = Departure(
            time=departure_time,
            planned_time=departure_time,
            delay_seconds=None,
            platform=None,
            is_realtime=False,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        )

        result = formatter.format_departure_time(departure)
        assert result == "14:30"


def test_format_departure_time_relative() -> None:
    """Given a departure, when formatting relative time, then returns compact relative format."""
    with patch.dict(os.environ, {}, clear=True):
        # Use UTC timezone to avoid timezone conversion issues
        config = AppConfig(config_file=None, timezone="UTC", _env_file=None)
        formatter = DepartureFormatter(config)

        # Use a large enough delta (20 minutes) to avoid timing issues
        now = datetime.now(UTC)
        departure = Departure(
            time=now + timedelta(minutes=20),
            planned_time=now + timedelta(minutes=20),
            delay_seconds=None,
            platform=None,
            is_realtime=False,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        )

        result = formatter.format_departure_time_relative(departure)
        # Allow for small timing differences (should be 19-20 minutes)
        assert result in ("19m", "20m")


def test_format_departure_time_absolute() -> None:
    """Given a departure, when formatting absolute time, then returns HH:mm format."""
    with patch.dict(os.environ, {}, clear=True):
        # Use UTC timezone to avoid timezone conversion issues
        config = AppConfig(config_file=None, timezone="UTC", _env_file=None)
        formatter = DepartureFormatter(config)

        # Use a fixed UTC time to avoid timezone conversion issues
        departure_time = datetime(2024, 1, 15, 9, 45, 0, tzinfo=UTC)
        departure = Departure(
            time=departure_time,
            planned_time=departure_time,
            delay_seconds=None,
            platform=None,
            is_realtime=False,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        )

        result = formatter.format_departure_time_absolute(departure)
        assert result == "09:45"


def test_format_compact_duration_seconds() -> None:
    """Given a duration less than 60 seconds, when formatting, then returns '<1m'."""
    with patch.dict(os.environ, {}, clear=True):
        config = AppConfig(config_file=None, _env_file=None)
        formatter = DepartureFormatter(config)

        delta = timedelta(seconds=30)
        result = formatter.format_compact_duration(delta)
        assert result == "<1m"


def test_format_compact_duration_minutes() -> None:
    """Given a duration less than 60 minutes, when formatting, then returns minutes format."""
    with patch.dict(os.environ, {}, clear=True):
        config = AppConfig(config_file=None, _env_file=None)
        formatter = DepartureFormatter(config)

        delta = timedelta(minutes=25)
        result = formatter.format_compact_duration(delta)
        assert result == "25m"


def test_format_compact_duration_hours_only() -> None:
    """Given a duration of exactly hours, when formatting, then returns hours only."""
    with patch.dict(os.environ, {}, clear=True):
        config = AppConfig(config_file=None, _env_file=None)
        formatter = DepartureFormatter(config)

        delta = timedelta(hours=2)
        result = formatter.format_compact_duration(delta)
        assert result == "2h"


def test_format_compact_duration_hours_and_minutes() -> None:
    """Given a duration with hours and minutes, when formatting, then returns both."""
    with patch.dict(os.environ, {}, clear=True):
        config = AppConfig(config_file=None, _env_file=None)
        formatter = DepartureFormatter(config)

        delta = timedelta(hours=2, minutes=40)
        result = formatter.format_compact_duration(delta)
        assert result == "2h40m"


def test_format_compact_duration_negative() -> None:
    """Given a negative duration, when formatting, then returns 'now'."""
    with patch.dict(os.environ, {}, clear=True):
        config = AppConfig(config_file=None, _env_file=None)
        formatter = DepartureFormatter(config)

        delta = timedelta(seconds=-30)
        result = formatter.format_compact_duration(delta)
        assert result == "now"


def test_format_update_time_with_datetime() -> None:
    """Given a datetime, when formatting update time, then returns HH:MM:SS format."""
    with patch.dict(os.environ, {}, clear=True):
        config = AppConfig(config_file=None, _env_file=None)
        formatter = DepartureFormatter(config)

        update_time = datetime(2024, 1, 15, 14, 30, 45, tzinfo=UTC)
        result = formatter.format_update_time(update_time)
        assert result == "14:30:45"


def test_format_update_time_none() -> None:
    """Given None, when formatting update time, then returns 'Never'."""
    with patch.dict(os.environ, {}, clear=True):
        config = AppConfig(config_file=None, _env_file=None)
        formatter = DepartureFormatter(config)

        result = formatter.format_update_time(None)
        assert result == "Never"


def test_format_departure_time_past_departure() -> None:
    """Given a departure in the past, when formatting, then returns 'now'."""
    with patch.dict(os.environ, {}, clear=True):
        # Use UTC timezone to avoid timezone conversion issues
        config = AppConfig(config_file=None, time_format="minutes", timezone="UTC", _env_file=None)
        formatter = DepartureFormatter(config)

        now = datetime.now(UTC)
        departure = Departure(
            time=now - timedelta(minutes=5),
            planned_time=now - timedelta(minutes=5),
            delay_seconds=None,
            platform=None,
            is_realtime=False,
            line="U3",
            destination="Giesing",
            transport_type="U-Bahn",
            icon="mdi:subway",
            is_cancelled=False,
            messages=[],
        )

        result = formatter.format_departure_time(departure)
        assert result == "now"
