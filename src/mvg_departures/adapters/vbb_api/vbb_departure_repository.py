"""VBB (Berlin/Brandenburg) REST API departure repository adapter.

Uses v6.bvg.transport.rest API for real-time Berlin public transport data.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from mvg_departures.domain.models.departure import Departure
from mvg_departures.domain.ports.departure_repository import DepartureRepository

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aiohttp import ClientSession


class VbbDepartureRepository(DepartureRepository):
    """Adapter for VBB REST API departure repository."""

    def __init__(self, session: "ClientSession | None" = None) -> None:
        """Initialize with optional aiohttp session."""
        self._session = session
        self._base_url = "https://v6.bvg.transport.rest"

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
        if not self._session:
            raise RuntimeError("VBB API requires an aiohttp session")

        # VBB API uses HAFAS station IDs
        # URL format: /stops/{stationId}/departures
        url = f"{self._base_url}/stops/{station_id}/departures"
        # Note: VBB API doesn't support filtering by route/line, so we must fetch all departures
        # Use configurable duration and high results count to get many departures
        # This ensures we capture infrequent routes like bus 249 that may only run every 20-30 minutes
        # The limit parameter is applied after fetching to control how many we return
        params: dict[str, int | str] = {
            "duration": duration_minutes,  # Configurable duration (default: 60 minutes)
            "results": 500,  # Get up to 500 departures to have enough for all routes
        }

        # Always pass 'when' parameter in UTC to ensure consistent behavior
        # The API may use local timezone as default "now", but we want UTC to match what it returns
        now_utc = datetime.now(UTC)
        if offset_minutes > 0:
            # VBB API uses 'when' parameter for future departures (ISO 8601 string)
            future_time = now_utc + timedelta(minutes=offset_minutes)
            params["when"] = future_time.isoformat()
        else:
            # Explicitly pass 'when' in UTC even when offset is 0
            # This ensures the API uses UTC "now" instead of local timezone "now"
            params["when"] = now_utc.isoformat()

        try:
            # Disable SSL verification for VBB API (similar to HAFAS)
            # The API may have certificate issues
            async with self._session.get(url, params=params, ssl=False) as response:
                if response.status != 200:
                    response_text = await response.text()
                    raise RuntimeError(
                        f"VBB API returned status {response.status}: {response_text}"
                    )

                data = await response.json()

                # VBB API response structure:
                # {
                #   "departures": [
                #     {
                #       "tripId": "...",
                #       "when": "2024-01-01T12:00:00+01:00",
                #       "plannedWhen": "2024-01-01T12:00:00+01:00",
                #       "delay": 0,
                #       "platform": "1",
                #       "line": {"name": "U2", "product": "subway", ...},
                #       "direction": "...",
                #       "cancelled": false,
                #       ...
                #     }
                #   ]
                # }

                departures_data = data.get("departures", [])

                departures = []
                for dep_data in departures_data[:limit]:
                    try:
                        # Parse departure time
                        when_str = dep_data.get("when") or dep_data.get("plannedWhen")
                        planned_when_str = dep_data.get("plannedWhen") or when_str

                        if not when_str:
                            continue

                        # Parse ISO 8601 datetime strings
                        when = datetime.fromisoformat(when_str.replace("Z", "+00:00"))
                        planned_when = datetime.fromisoformat(
                            planned_when_str.replace("Z", "+00:00")
                        )

                        # Ensure UTC timezone
                        if when.tzinfo is None:
                            when = when.replace(tzinfo=UTC)
                        else:
                            when = when.astimezone(UTC)
                        if planned_when.tzinfo is None:
                            planned_when = planned_when.replace(tzinfo=UTC)
                        else:
                            planned_when = planned_when.astimezone(UTC)

                        # Calculate delay
                        delay_seconds = int((when - planned_when).total_seconds())

                        # Extract line information
                        line_obj = dep_data.get("line", {})
                        line_name = line_obj.get("name", "") or line_obj.get("id", "")
                        product = line_obj.get("product", "")

                        # Map product to transport type
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

                        # Extract other fields
                        platform = dep_data.get("platform")
                        # Prefer direction (more descriptive, includes district/area) for individual departures
                        # direction often includes district info (e.g., "Schmargendorf, Elsterplatz")
                        # while destination.name is just the stop name (e.g., "Elsterplatz (Berlin)")
                        # For route listing (CLI), both are shown separately so users can find by either name
                        direction = dep_data.get("direction", "") or ""
                        dest_obj = dep_data.get("destination")
                        dest_name = ""
                        if dest_obj and isinstance(dest_obj, dict):
                            dest_name = dest_obj.get("name", "") or ""

                        # Use direction if available (more descriptive), otherwise use destination.name
                        if direction:
                            destination = direction
                        elif dest_name:
                            destination = dest_name
                        else:
                            destination = ""
                        is_cancelled = dep_data.get("cancelled", False)
                        remarks = dep_data.get("remarks", [])
                        messages = [r.get("text", "") for r in remarks if isinstance(r, dict)]
                        if not messages:
                            messages = [r for r in remarks if isinstance(r, str)]

                        departure = Departure(
                            time=when,
                            planned_time=planned_when,
                            delay_seconds=delay_seconds if delay_seconds > 0 else None,
                            platform=platform,
                            is_realtime=delay_seconds != 0 or dep_data.get("realtime", False),
                            line=line_name,
                            destination=destination,
                            transport_type=transport_type,
                            icon="",  # VBB API doesn't provide icons
                            is_cancelled=is_cancelled,
                            messages=messages,
                        )
                        departures.append(departure)
                    except Exception as e:
                        logger.warning(f"Error processing VBB departure: {e}")
                        continue

                return departures

        except Exception as e:
            logger.error(f"Error fetching departures from VBB API for station '{station_id}': {e}")
            raise
