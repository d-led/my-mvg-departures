"""Station repository port."""

from typing import Protocol

from mvg_departures.domain.models.station import Station


class StationRepository(Protocol):
    """Port for retrieving station information."""

    async def find_station_by_name(self, name: str, place: str) -> Station | None:
        """Find a station by name and place."""
        ...

    async def find_station_by_id(self, station_id: str) -> Station | None:
        """Find a station by its global identifier."""
        ...

    async def find_nearby_station(self, latitude: float, longitude: float) -> Station | None:
        """Find the nearest station to given coordinates."""
        ...
