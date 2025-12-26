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
        duration_minutes: int = 60,  # noqa: ARG002  # Not used by MVG API
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

        # Always fetch raw API response to get stopPointGlobalId
        # The mvg library may not include stopPointGlobalId in its transformed response
        raw_results = None
        if self._session:
            try:
                transport_types_str = ",".join(
                    ["UBAHN", "TRAM", "SBAHN", "BUS", "REGIONAL_BUS", "BAHN"]
                )
                url = f"https://www.mvg.de/api/bgw-pt/v3/departures?globalId={station_id}&limit={limit}&transportTypes={transport_types_str}"
                headers = {
                    "accept": "application/json",
                    "user-agent": "Mozilla/5.0",
                }
                # Disable SSL verification for MVG API (may have certificate issues in some environments)
                async with self._session.get(url, headers=headers, ssl=False) as response:
                    if response.status == 200:
                        raw_results = await response.json()
            except Exception:
                # If raw API fetch fails, fall back to mvg library
                pass

        # Use raw results if available (they have stopPointGlobalId), otherwise use mvg library results
        if raw_results and isinstance(raw_results, list):
            # Use raw API response directly
            results = raw_results
        else:
            # Fall back to mvg library
            results = await MvgApi.departures_async(
                station_id,
                limit=limit,
                offset=offset_minutes,
                transport_types=mvg_transport_types,
                session=self._session,
            )

        departures = []
        for result in results:
            # Extract stopPointGlobalId from raw API response
            # The raw API uses camelCase: stopPointGlobalId
            # The mvg library transforms the response and doesn't include stopPointGlobalId
            stop_point_global_id = result.get("stopPointGlobalId") or result.get(
                "stop_point_global_id"
            )

            # Handle both raw API format and mvg library transformed format
            # Raw API format has: realtimeDepartureTime (ms), plannedDepartureTime (ms), delayInMinutes,
            #                     label, transportType, etc.
            # mvg library format has: time (s), planned (s), delay, line, type, etc.

            # Check if this is raw API format (has realtimeDepartureTime) or mvg library format (has time)
            if "realtimeDepartureTime" in result:
                # Raw API format - convert from milliseconds to seconds
                time = datetime.fromtimestamp(result["realtimeDepartureTime"] / 1000, tz=UTC)
                planned_time = datetime.fromtimestamp(result["plannedDepartureTime"] / 1000, tz=UTC)
                delay_seconds = (
                    result.get("delayInMinutes", 0) * 60 if result.get("delayInMinutes") else 0
                )
                platform = result.get("platform")
                is_realtime = result.get("realtime", False)
                line = result.get("label", "")
                destination = result.get("destination", "")
                # Map transportType to display name
                transport_type_enum = result.get("transportType", "")
                transport_type_map = {
                    "UBAHN": "U-Bahn",
                    "SBAHN": "S-Bahn",
                    "BUS": "Bus",
                    "TRAM": "Tram",
                    "BAHN": "Bahn",
                    "REGIONAL_BUS": "Regionalbus",
                }
                transport_type = transport_type_map.get(transport_type_enum, transport_type_enum)
                # Get icon from transport type
                icon_map = {
                    "UBAHN": "mdi:subway",
                    "SBAHN": "mdi:subway-variant",
                    "BUS": "mdi:bus",
                    "TRAM": "mdi:tram",
                    "BAHN": "mdi:train",
                    "REGIONAL_BUS": "mdi:bus",
                }
                icon = icon_map.get(transport_type_enum, "")
                is_cancelled = result.get("cancelled", False)
                messages = result.get("messages", [])
            else:
                # mvg library format - already transformed
                time = datetime.fromtimestamp(result["time"], tz=UTC)
                planned_time = datetime.fromtimestamp(result["planned"], tz=UTC)
                delay_seconds = result.get("delay", 0)
                platform = result.get("platform")
                is_realtime = result.get("realtime", False)
                line = result.get("line", "")
                destination = result.get("destination", "")
                transport_type = result.get("type", "")
                icon = result.get("icon", "")
                is_cancelled = result.get("cancelled", False)
                messages = result.get("messages", [])

            departure = Departure(
                time=time,
                planned_time=planned_time,
                delay_seconds=delay_seconds,
                platform=platform,
                is_realtime=is_realtime,
                line=line,
                destination=destination,
                transport_type=transport_type,
                icon=icon,
                is_cancelled=is_cancelled,
                messages=messages,
                stop_point_global_id=stop_point_global_id,
            )
            departures.append(departure)

        return departures
