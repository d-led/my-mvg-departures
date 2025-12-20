"""MVG departure repository adapter."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from mvg import MvgApi, TransportType

from mvg_departures.domain.models.departure import Departure
from mvg_departures.domain.ports.departure_repository import DepartureRepository

if TYPE_CHECKING:
    from aiohttp import ClientSession


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
                time=datetime.fromtimestamp(result["time"], tz=UTC),
                planned_time=datetime.fromtimestamp(result["planned"], tz=UTC),
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
