"""Ports (interfaces) for the ports-and-adapters architecture."""

from abc import ABC, abstractmethod
from typing import Protocol

from mvg_departures.domain.models import Departure, Station


class StationRepository(Protocol):
    """Port for retrieving station information."""

    @abstractmethod
    async def find_station_by_name(self, name: str, place: str) -> Station | None:
        """Find a station by name and place."""
        ...

    @abstractmethod
    async def find_station_by_id(self, station_id: str) -> Station | None:
        """Find a station by its global identifier."""
        ...

    @abstractmethod
    async def find_nearby_station(self, latitude: float, longitude: float) -> Station | None:
        """Find the nearest station to given coordinates."""
        ...


class DepartureRepository(Protocol):
    """Port for retrieving departure information."""

    @abstractmethod
    async def get_departures(
        self,
        station_id: str,
        limit: int = 10,
        offset_minutes: int = 0,
        transport_types: list[str] | None = None,
    ) -> list[Departure]:
        """Get departures for a station."""
        ...


class DisplayAdapter(ABC):
    """Port for displaying departure information to users."""

    @abstractmethod
    async def display_departures(self, direction_groups: list[tuple[str, list[Departure]]]) -> None:
        """Display grouped departures."""
        ...

    @abstractmethod
    async def start(self) -> None:
        """Start the display adapter."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the display adapter."""
        ...
