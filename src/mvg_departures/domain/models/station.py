"""Station domain model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Station:
    """Represents a public transport station."""

    id: str
    name: str
    place: str
    latitude: float
    longitude: float
