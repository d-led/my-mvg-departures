"""MVG departure repository adapter."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from mvg import MvgApi, TransportType

from mvg_departures.domain.models.departure import Departure
from mvg_departures.domain.ports.departure_repository import DepartureRepository

if TYPE_CHECKING:
    from aiohttp import ClientResponse, ClientSession


class MvgDepartureRepository(DepartureRepository):
    """Adapter for MVG departure repository."""

    def __init__(self, session: "ClientSession | None" = None) -> None:
        """Initialize with optional aiohttp session."""
        self._session = session

    def _map_transport_types(self, transport_types: list[str] | None) -> list[TransportType] | None:
        """Map string transport types to MVG TransportType enum.

        Args:
            transport_types: List of transport type strings.

        Returns:
            List of TransportType enums, or None if no mapping needed.
        """
        if not transport_types:
            return None

        type_map = {
            "U-Bahn": TransportType.UBAHN,
            "S-Bahn": TransportType.SBAHN,
            "Bus": TransportType.BUS,
            "Tram": TransportType.TRAM,
        }
        return [type_map[t] for t in transport_types if t in type_map]

    def _build_departures_url(self, station_id: str, limit: int) -> str:
        """Build the MVG departures API URL."""
        transport_types_str = ",".join(["UBAHN", "TRAM", "SBAHN", "BUS", "REGIONAL_BUS", "BAHN"])
        return (
            f"https://www.mvg.de/api/bgw-pt/v3/departures"
            f"?globalId={station_id}&limit={limit}&transportTypes={transport_types_str}"
        )

    def _get_departures_headers(self) -> dict[str, str]:
        """Get headers for MVG departures API request."""
        return {
            "accept": "application/json",
            "user-agent": "Mozilla/5.0",
        }

    async def _parse_departures_response(
        self, response: "ClientResponse"
    ) -> list[dict[str, Any]] | None:
        """Parse the departures API response."""
        if response.status == 200:
            raw_results = await response.json()
            if isinstance(raw_results, list):
                return raw_results
        return None

    async def _fetch_raw_api_response(
        self, station_id: str, limit: int
    ) -> list[dict[str, Any]] | None:
        """Fetch raw API response to get stopPointGlobalId.

        Args:
            station_id: Station ID.
            limit: Maximum number of departures.

        Returns:
            Raw API response as list, or None if fetch fails.
        """
        if not self._session:
            return None

        try:
            url = self._build_departures_url(station_id, limit)
            headers = self._get_departures_headers()
            async with self._session.get(url, headers=headers, ssl=False) as response:
                return await self._parse_departures_response(response)
        except Exception:
            pass

        return None

    def _parse_raw_api_format(self, result: dict[str, Any]) -> dict[str, Any]:
        """Parse raw API format response.

        Args:
            result: Raw API response dictionary.

        Returns:
            Dictionary with parsed departure data.
        """
        time = datetime.fromtimestamp(result["realtimeDepartureTime"] / 1000, tz=UTC)
        planned_time = datetime.fromtimestamp(result["plannedDepartureTime"] / 1000, tz=UTC)
        delay_seconds = result.get("delayInMinutes", 0) * 60 if result.get("delayInMinutes") else 0

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

        icon_map = {
            "UBAHN": "mdi:subway",
            "SBAHN": "mdi:subway-variant",
            "BUS": "mdi:bus",
            "TRAM": "mdi:tram",
            "BAHN": "mdi:train",
            "REGIONAL_BUS": "mdi:bus",
        }
        icon = icon_map.get(transport_type_enum, "")

        return {
            "time": time,
            "planned_time": planned_time,
            "delay_seconds": delay_seconds,
            "platform": result.get("platform"),
            "is_realtime": result.get("realtime", False),
            "line": result.get("label", ""),
            "destination": result.get("destination", ""),
            "transport_type": transport_type,
            "icon": icon,
            "is_cancelled": result.get("cancelled", False),
            "messages": result.get("messages", []),
        }

    def _parse_mvg_library_format(self, result: dict[str, Any]) -> dict[str, Any]:
        """Parse mvg library format response.

        Args:
            result: mvg library response dictionary.

        Returns:
            Dictionary with parsed departure data.
        """
        return {
            "time": datetime.fromtimestamp(result["time"], tz=UTC),
            "planned_time": datetime.fromtimestamp(result["planned"], tz=UTC),
            "delay_seconds": result.get("delay", 0),
            "platform": result.get("platform"),
            "is_realtime": result.get("realtime", False),
            "line": result.get("line", ""),
            "destination": result.get("destination", ""),
            "transport_type": result.get("type", ""),
            "icon": result.get("icon", ""),
            "is_cancelled": result.get("cancelled", False),
            "messages": result.get("messages", []),
        }

    def _convert_to_departure(
        self, result: dict[str, Any], parsed_data: dict[str, Any]
    ) -> Departure:
        """Convert parsed data to Departure model.

        Args:
            result: Original result dictionary (for stop_point_global_id).
            parsed_data: Parsed departure data.

        Returns:
            Departure object.
        """
        stop_point_global_id = result.get("stopPointGlobalId") or result.get("stop_point_global_id")

        return Departure(
            time=parsed_data["time"],
            planned_time=parsed_data["planned_time"],
            delay_seconds=parsed_data["delay_seconds"],
            platform=parsed_data["platform"],
            is_realtime=parsed_data["is_realtime"],
            line=parsed_data["line"],
            destination=parsed_data["destination"],
            transport_type=parsed_data["transport_type"],
            icon=parsed_data["icon"],
            is_cancelled=parsed_data["is_cancelled"],
            messages=parsed_data["messages"],
            stop_point_global_id=stop_point_global_id,
        )

    async def get_departures(
        self,
        station_id: str,
        limit: int = 10,
        offset_minutes: int = 0,
        transport_types: list[str] | None = None,
        duration_minutes: int = 60,  # noqa: ARG002  # Not used by MVG API
    ) -> list[Departure]:
        """Get departures for a station."""
        mvg_transport_types = self._map_transport_types(transport_types)

        raw_results = await self._fetch_raw_api_response(station_id, limit)

        if raw_results:
            results = raw_results
        else:
            results = await MvgApi.departures_async(
                station_id,
                limit=limit,
                offset=offset_minutes,
                transport_types=mvg_transport_types,
                session=self._session,
            )

        departures = []
        for result in results:
            if "realtimeDepartureTime" in result:
                parsed_data = self._parse_raw_api_format(result)
            else:
                parsed_data = self._parse_mvg_library_format(result)

            departure = self._convert_to_departure(result, parsed_data)
            departures.append(departure)

        return departures
