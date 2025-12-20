"""MVG API adapter implementing repository ports."""

from datetime import datetime
from typing import TYPE_CHECKING

from mvg import MvgApi, TransportType

from mvg_departures.domain.models import Departure, Station
from mvg_departures.domain.ports import DepartureRepository, StationRepository

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


class MvgDepartureRepository(DepartureRepository):
    """Adapter for MVG departure repository."""

    def __init__(self, session: "ClientSession | None" = None) -> None:
        """Initialize with optional aiohttp session."""
        self._session = session

    async def get_departures(
        self,
        station_id: str,
        limit: int = 10,
        offset_minutes: int = 0,
        transport_types: list[str] | None = None,
    ) -> list[Departure]:
        """Get departures for a station."""
        mvg_transport_types = None
        if transport_types:
            # Map string transport types to MVG TransportType enum
            type_map = {
                "U-Bahn": TransportType.UBAHN,
                "S-Bahn": TransportType.SBAHN,
                "Bus": TransportType.BUS,
                "Tram": TransportType.TRAM,
            }
            mvg_transport_types = [type_map[t] for t in transport_types if t in type_map]

        results = await MvgApi.departures_async(
            station_id,
            limit=limit,
            offset=offset_minutes,
            transport_types=mvg_transport_types,
            session=self._session,
        )

        departures = []
        for result in results:
            departure = Departure(
                time=datetime.fromtimestamp(result["time"]),
                planned_time=datetime.fromtimestamp(result["planned"]),
                delay_seconds=result.get("delay", 0),
                platform=result.get("platform"),
                is_realtime=result.get("realtime", False),
                line=result["line"],
                destination=result["destination"],
                transport_type=result["type"],
                icon=result.get("icon", ""),
                is_cancelled=result.get("cancelled", False),
                messages=result.get("messages", []),
            )
            departures.append(departure)

        return departures
