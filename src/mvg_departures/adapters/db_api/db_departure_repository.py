"""DB departure repository adapter using v6.db.transport.rest API.

API Documentation: https://v6.db.transport.rest/api.html
"""

import logging
from typing import TYPE_CHECKING

from mvg_departures.adapters.db_api.departure_parser import DepartureParser
from mvg_departures.adapters.db_api.http_client import DbHttpClient
from mvg_departures.domain.models.departure import Departure
from mvg_departures.domain.ports.departure_repository import DepartureRepository

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aiohttp import ClientSession


class DbDepartureRepository(DepartureRepository):
    """Adapter for DB departure repository using v6.db.transport.rest API."""

    def __init__(self, session: "ClientSession | None" = None) -> None:
        """Initialize with optional aiohttp session.

        Args:
            session: Optional aiohttp ClientSession for HTTP requests.
        """
        self._http_client = DbHttpClient(session=session)

    async def get_departures(
        self,
        station_id: str,
        limit: int = 10,
        offset_minutes: int = 0,  # noqa: ARG002  # v6 API doesn't support offset
        transport_types: list[str] | None = None,
        duration_minutes: int = 60,
    ) -> list[Departure]:
        """Get live departures for a DB station.

        Args:
            station_id: Station ID (e.g., "8000013" for Augsburg Hbf).
            limit: Maximum number of departures to return.
            offset_minutes: Offset in minutes from now (not supported by v6 API).
            transport_types: Filter by transport types (filtered client-side if provided).
            duration_minutes: Time window in minutes.

        Returns:
            List of Departure objects with live data.
        """
        departures_data = await self._http_client.fetch_departures(
            station_id, duration=duration_minutes
        )

        if not departures_data:
            logger.debug(f"No departures returned for station {station_id}")
            return []

        departures = DepartureParser.parse_departures(departures_data, limit * 2)

        # Filter by transport types if specified
        if transport_types:
            type_set = {t.lower() for t in transport_types}
            departures = [d for d in departures if d.transport_type.lower() in type_set]

        return departures[:limit]
