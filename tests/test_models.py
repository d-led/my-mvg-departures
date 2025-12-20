"""Tests for domain models."""

from datetime import datetime

from mvg_departures.domain.models import Departure, Station, StopConfiguration


def test_station_creation() -> None:
    """Given station data, when creating a Station, then all fields are set correctly."""
    station = Station(
        id="de:09162:70",
        name="Universität",
        place="München",
        latitude=48.15007,
        longitude=11.581,
    )

    assert station.id == "de:09162:70"
    assert station.name == "Universität"
    assert station.place == "München"
    assert station.latitude == 48.15007
    assert station.longitude == 11.581


def test_departure_creation() -> None:
    """Given departure data, when creating a Departure, then all fields are set correctly."""
    now = datetime.now()
    departure = Departure(
        time=now,
        planned_time=now,
        delay_seconds=60,
        platform=1,
        is_realtime=True,
        line="U3",
        destination="Giesing",
        transport_type="U-Bahn",
        icon="mdi:subway",
        is_cancelled=False,
        messages=["Delay"],
    )

    assert departure.time == now
    assert departure.delay_seconds == 60
    assert departure.platform == 1
    assert departure.is_realtime is True
    assert departure.line == "U3"
    assert departure.destination == "Giesing"
    assert departure.is_cancelled is False
    assert len(departure.messages) == 1


def test_stop_configuration_creation() -> None:
    """Given stop config data, when creating StopConfiguration, then all fields are set correctly."""
    config = StopConfiguration(
        station_id="de:09162:70",
        station_name="Universität",
        direction_mappings={"->Giesing": ["Giesing", "Fürstenried"]},
    )

    assert config.station_id == "de:09162:70"
    assert config.station_name == "Universität"
    assert "->Giesing" in config.direction_mappings
    assert len(config.direction_mappings["->Giesing"]) == 2


