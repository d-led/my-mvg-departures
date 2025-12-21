"""Stop configuration domain model."""

from dataclasses import dataclass


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
        0  # Leeway in minutes: departures earlier than now + leeway are filtered out before counting for limits
    )
