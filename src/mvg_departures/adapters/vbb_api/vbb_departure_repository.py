"""VBB (Berlin/Brandenburg) REST API departure repository adapter.

Uses v6.bvg.transport.rest API for real-time Berlin public transport data.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from mvg_departures.adapters.api_rate_limiter import ApiRateLimiter
from mvg_departures.domain.models.departure import Departure
from mvg_departures.domain.ports.departure_repository import DepartureRepository

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aiohttp import ClientSession

# Minimum delay between VBB API requests (in seconds)
# Using 1.5s to be nice to the API and avoid rate limiting
VBB_API_MIN_DELAY_SECONDS = 1.5


class VbbDepartureRepository(DepartureRepository):
    """Adapter for VBB REST API departure repository."""

    def __init__(self, session: "ClientSession | None" = None) -> None:
        """Initialize with optional aiohttp session."""
        self._session = session
        self._base_url = "https://v6.bvg.transport.rest"
        self._rate_limiter: ApiRateLimiter | None = None

    async def _get_rate_limiter(self) -> ApiRateLimiter:
        """Get the shared rate limiter for VBB API."""
        if self._rate_limiter is None:
            self._rate_limiter = await ApiRateLimiter.get_instance(
                "vbb_api", VBB_API_MIN_DELAY_SECONDS
            )
        return self._rate_limiter

    def _build_request_params(
        self, offset_minutes: int, duration_minutes: int
    ) -> dict[str, int | str]:
        """Build request parameters for VBB API.

        Args:
            offset_minutes: Offset in minutes from now.
            duration_minutes: Duration parameter for API.

        Returns:
            Dictionary of request parameters.
        """
        params: dict[str, int | str] = {
            "duration": duration_minutes,
            "results": 500,  # Get up to 500 departures to have enough for all routes
        }

        now_utc = datetime.now(UTC)
        if offset_minutes > 0:
            future_time = now_utc + timedelta(minutes=offset_minutes)
            params["when"] = future_time.isoformat()
        else:
            params["when"] = now_utc.isoformat()

        return params

    async def _fetch_departures_data(
        self, station_id: str, params: dict[str, int | str]
    ) -> list[dict[str, Any]]:
        """Fetch raw departure data from VBB API.

        Args:
            station_id: VBB station ID.
            params: Request parameters.

        Returns:
            List of raw departure data dictionaries.

        Raises:
            RuntimeError: If the API call fails.
        """
        if not self._session:
            raise RuntimeError("VBB API requires an aiohttp session")

        url = f"{self._base_url}/stops/{station_id}/departures"

        # Rate limit: wait for permission before making request
        rate_limiter = await self._get_rate_limiter()
        await rate_limiter.acquire()

        async with self._session.get(url, params=params, ssl=False) as response:
            if response.status != 200:
                response_text = await response.text()
                raise RuntimeError(f"VBB API returned status {response.status}: {response_text}")

            data = await response.json()
            departures_data: list[dict[str, Any]] = data.get("departures", [])
            return departures_data

    def _parse_departure_time(self, dep_data: dict[str, Any]) -> tuple[datetime, datetime] | None:
        """Parse departure time and planned time from VBB departure data.

        Args:
            dep_data: Raw departure data dictionary.

        Returns:
            Tuple of (when, planned_when) in UTC, or None if parsing fails.
        """
        when_str = dep_data.get("when") or dep_data.get("plannedWhen")
        planned_when_str = dep_data.get("plannedWhen") or when_str

        if not when_str or not planned_when_str:
            return None

        when = datetime.fromisoformat(when_str.replace("Z", "+00:00"))
        planned_when = datetime.fromisoformat(planned_when_str.replace("Z", "+00:00"))

        # Ensure UTC timezone
        when = when.replace(tzinfo=UTC) if when.tzinfo is None else when.astimezone(UTC)
        planned_when = (
            planned_when.replace(tzinfo=UTC)
            if planned_when.tzinfo is None
            else planned_when.astimezone(UTC)
        )

        return when, planned_when

    def _calculate_delay(self, when: datetime, planned_when: datetime) -> int | None:
        """Calculate delay in seconds.

        Args:
            when: Actual departure time.
            planned_when: Planned departure time.

        Returns:
            Delay in seconds, or None if no delay.
        """
        delay_seconds = int((when - planned_when).total_seconds())
        return delay_seconds if delay_seconds > 0 else None

    def _extract_line_info(self, dep_data: dict[str, Any]) -> tuple[str, str]:
        """Extract line name and transport type from VBB departure data.

        Args:
            dep_data: Raw departure data dictionary.

        Returns:
            Tuple of (line_name, transport_type).
        """
        line_obj = dep_data.get("line", {})
        line_name = line_obj.get("name", "") or line_obj.get("id", "")
        product = line_obj.get("product", "")

        transport_type_map = {
            "subway": "U-Bahn",
            "suburban": "S-Bahn",
            "bus": "Bus",
            "tram": "Tram",
            "ferry": "Ferry",
            "regional": "Regional",
            "express": "Express",
        }
        transport_type = transport_type_map.get(product, product.capitalize())

        return line_name, transport_type

    def _extract_destination(self, dep_data: dict[str, Any]) -> str:
        """Extract destination from VBB departure data.

        Args:
            dep_data: Raw departure data dictionary.

        Returns:
            Destination name.
        """
        direction = dep_data.get("direction", "") or ""
        dest_obj = dep_data.get("destination")
        dest_name = ""

        if dest_obj and isinstance(dest_obj, dict):
            dest_name = dest_obj.get("name", "") or ""

        if direction:
            return direction
        if dest_name:
            return dest_name
        return ""

    def _extract_messages(self, dep_data: dict[str, Any]) -> list[str]:
        """Extract messages/remarks from VBB departure data.

        Args:
            dep_data: Raw departure data dictionary.

        Returns:
            List of message strings.
        """
        remarks = dep_data.get("remarks", [])
        messages = [r.get("text", "") for r in remarks if isinstance(r, dict)]
        if not messages:
            messages = [r for r in remarks if isinstance(r, str)]
        return messages

    def _convert_departure(self, dep_data: dict[str, Any]) -> Departure | None:
        """Convert VBB departure data to Departure model.

        Args:
            dep_data: Raw departure data dictionary.

        Returns:
            Departure object, or None if conversion fails.
        """
        time_data = self._parse_departure_time(dep_data)
        if not time_data:
            return None

        when, planned_when = time_data
        delay_seconds = self._calculate_delay(when, planned_when)
        line_name, transport_type = self._extract_line_info(dep_data)
        destination = self._extract_destination(dep_data)
        messages = self._extract_messages(dep_data)

        platform = dep_data.get("platform")
        is_cancelled = dep_data.get("cancelled", False)
        is_realtime = delay_seconds is not None or dep_data.get("realtime", False)

        return Departure(
            time=when,
            planned_time=planned_when,
            delay_seconds=delay_seconds,
            platform=platform,
            is_realtime=is_realtime,
            line=line_name,
            destination=destination,
            transport_type=transport_type,
            icon="",  # VBB API doesn't provide icons
            is_cancelled=is_cancelled,
            messages=messages,
        )

    async def get_departures(
        self,
        station_id: str,
        limit: int = 10,
        offset_minutes: int = 0,
        transport_types: list[str] | None = None,  # noqa: ARG002
        duration_minutes: int = 60,  # VBB API duration parameter
    ) -> list[Departure]:
        """Get departures for a VBB station.

        Args:
            station_id: VBB station ID (can be HAFAS ID or VBB-specific ID)
            limit: Maximum number of departures to return
            offset_minutes: Offset in minutes from now
            transport_types: Not used for VBB API (all types returned)

        Returns:
            List of Departure objects
        """
        try:
            params = self._build_request_params(offset_minutes, duration_minutes)
            departures_data = await self._fetch_departures_data(station_id, params)

            departures = []
            for dep_data in departures_data[:limit]:
                try:
                    departure = self._convert_departure(dep_data)
                    if departure:
                        departures.append(departure)
                except Exception as e:
                    logger.warning(f"Error processing VBB departure: {e}")
                    continue

            return departures

        except Exception as e:
            logger.error(f"Error fetching departures from VBB API for station '{station_id}': {e}")
            raise
