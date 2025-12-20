"""Domain models for MVG departures."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Station:
    """Represents a public transport station."""

    id: str
    name: str
    place: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class Departure:
    """Represents a single departure from a station."""

    time: datetime
    planned_time: datetime
    delay_seconds: int | None
    platform: Optional[int]
    is_realtime: bool
    line: str
    destination: str
    transport_type: str
    icon: str
    is_cancelled: bool
    messages: list[str]


@dataclass(frozen=True)
class DirectionGroup:
    """Represents a group of departures heading in the same direction."""

    direction_name: str
    stop_name: str
    departures: list[Departure]


@dataclass(frozen=True)
class StopConfiguration:
    """Configuration for a stop to monitor."""

    station_id: str
    station_name: str
    direction_mappings: dict[str, list[str]]  # direction_name -> list of patterns (whitelist)
    # Patterns can be: destination ("Messestadt"), route ("U2", "Bus 59"), or route+destination ("U2 Messestadt")
    max_departures_per_stop: int = (
        20  # Maximum departures to display per direction group (not total)
    )
    max_departures_per_route: int = (
        2  # Maximum departures to display per route (line) within each direction group
    )
    show_ungrouped: bool = (
        True  # If False, only show departures matching direction_mappings (strict whitelist)
    )
    departure_leeway_minutes: int = (
        0  # Leeway in minutes: departures earlier than now + leeway are filtered out (does not affect counts)
    )
