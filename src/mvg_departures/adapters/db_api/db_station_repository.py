"""DB station repository adapter using v6.db.transport.rest for search."""

import logging
from typing import TYPE_CHECKING, Any

from mvg_departures.adapters.db_api.http_client import DbHttpClient
from mvg_departures.domain.models.station import Station
from mvg_departures.domain.ports.station_repository import StationRepository

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aiohttp import ClientSession


class DbStationRepository(StationRepository):
    """Adapter for DB station repository using v6.db.transport.rest API."""

    def __init__(self, session: "ClientSession | None" = None) -> None:
        """Initialize with optional aiohttp session.

        Args:
            session: Optional aiohttp ClientSession for HTTP requests.
        """
        self._http_client = DbHttpClient(session=session)

    async def find_station_by_name(self, name: str, place: str) -> Station | None:
        """Find a station by name and place.

        Args:
            name: Station name.
            place: City/place name.

        Returns:
            Station object or None if not found.
        """
        query = f"{name}, {place}"
        results = await self._http_client.search_stations(query)
        if not results:
            return None

        station_data = results[0]
        return self._build_station(
            station_data, station_id=station_data.get("id", ""), name=name, place=place
        )

    async def find_station_by_id(self, station_id: str) -> Station | None:
        """Find a station by its identifier.

        Args:
            station_id: Station ID (e.g., "8000013").

        Returns:
            Station object or None if not found.
        """
        station_data = await self._http_client.get_station_info(station_id)
        if not station_data:
            return None

        return self._build_station(station_data, station_id=station_id)

    async def find_nearby_station(self, latitude: float, longitude: float) -> Station | None:
        """Find the nearest station to given coordinates.

        Args:
            latitude: Latitude coordinate.
            longitude: Longitude coordinate.

        Returns:
            None (not implemented for DB API).
        """
        _ = latitude, longitude  # Unused - DB API doesn't support nearby search
        logger.warning("find_nearby_station not implemented for DB API")
        return None

    @staticmethod
    def _build_station(
        station_data: dict[str, Any],
        station_id: str,
        name: str | None = None,
        place: str | None = None,
    ) -> Station:
        """Build Station object from API data.

        Args:
            station_data: Station data from API.
            station_id: Station ID.
            name: Optional fallback name.
            place: Optional fallback place.

        Returns:
            Station domain object.
        """
        return Station(
            id=station_id,
            name=station_data.get("name", name or station_id),
            place=station_data.get("place", place or ""),
            latitude=station_data.get("latitude", 0.0),
            longitude=station_data.get("longitude", 0.0),
        )
