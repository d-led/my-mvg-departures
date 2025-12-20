"""MVG station repository adapter."""

from typing import TYPE_CHECKING

from mvg import MvgApi

from mvg_departures.domain.models.station import Station
from mvg_departures.domain.ports.station_repository import StationRepository

if TYPE_CHECKING:
    from aiohttp import ClientSession


class MvgStationRepository(StationRepository):
    """Adapter for MVG station repository."""

    def __init__(self, session: "ClientSession | None" = None) -> None:
        """Initialize with optional aiohttp session."""
        self._session = session

    async def find_station_by_name(self, name: str, place: str) -> Station | None:
        """Find a station by name and place."""
        query = f"{name}, {place}"
        result = await MvgApi.station_async(query, session=self._session)
        if not result:
            return None
        return Station(
            id=result["id"],
            name=result["name"],
            place=result["place"],
            latitude=result["latitude"],
            longitude=result["longitude"],
        )

    async def find_station_by_id(self, station_id: str) -> Station | None:
        """Find a station by its global identifier."""
        # MVG API doesn't have a direct lookup by ID, so we need to search
        # For now, we'll use a workaround by trying to get departures
        # In a real implementation, we might cache station info
        try:
            # Try to get a single departure to validate the station exists
            departures = await MvgApi.departures_async(station_id, limit=1, session=self._session)
            if not departures:
                return None
            # We don't have full station info from departures, so we'll need
            # to store station info separately or use stations() endpoint
            # For now, return a minimal station
            return Station(
                id=station_id,
                name=station_id,  # Placeholder
                place="München",
                latitude=0.0,
                longitude=0.0,
            )
        except Exception:
            return None

    async def find_nearby_station(self, latitude: float, longitude: float) -> Station | None:
        """Find the nearest station to given coordinates."""
        result = await MvgApi.nearby_async(latitude, longitude, session=self._session)
        if not result:
            return None
        return Station(
            id=result["id"],
            name=result["name"],
            place=result["place"],
            latitude=result["latitude"],
            longitude=result["longitude"],
        )
