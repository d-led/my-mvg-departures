"""HTTP client for DB API requests.

Uses the v6.db.transport.rest public API.
API Documentation: https://v6.db.transport.rest/api.html
"""

import logging
from typing import TYPE_CHECKING, Any

from mvg_departures.adapters.api_rate_limiter import ApiRateLimiter
from mvg_departures.adapters.db_api.constants import (
    DB_LOCATIONS_URL,
    DB_STOPS_URL,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aiohttp import ClientResponse, ClientSession

# Minimum delay between DB API requests (in seconds)
# DB API rate limit is 100 requests/minute, so ~0.6s minimum
# Using 1.5s to be safe and account for multiple instances
DB_API_MIN_DELAY_SECONDS = 1.5


class DbHttpClient:
    """HTTP client for DB API requests using v6.db.transport.rest."""

    def __init__(self, session: "ClientSession | None" = None) -> None:
        """Initialize with optional aiohttp session."""
        self._session = session
        self._rate_limiter: ApiRateLimiter | None = None

    async def _get_rate_limiter(self) -> ApiRateLimiter:
        """Get the shared rate limiter for DB API."""
        if self._rate_limiter is None:
            self._rate_limiter = await ApiRateLimiter.get_instance(
                "db_api", DB_API_MIN_DELAY_SECONDS
            )
        return self._rate_limiter

    async def _handle_search_response(self, response: "ClientResponse") -> list[dict[str, Any]]:
        """Handle search stations API response."""
        if response.status != 200:
            response_text = await response.text()
            logger.warning(f"DB API returned status {response.status}: {response_text[:200]}")
            return []

        data = await response.json()
        if isinstance(data, list):
            return self._parse_locations(data)
        return []

    async def search_stations(self, query: str) -> list[dict[str, Any]]:
        """Search for stations using v6.db.transport.rest/locations.

        Args:
            query: Search query string.

        Returns:
            List of station dictionaries from API response.
        """
        if not self._session:
            return []

        params: dict[str, str | int] = {"query": query, "results": 20}

        try:
            async with self._session.get(DB_LOCATIONS_URL, params=params, ssl=False) as response:
                return await self._handle_search_response(response)
        except Exception as e:
            logger.warning(f"Error searching DB stations: {e}")
            return []

    @staticmethod
    def _parse_locations(locations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Parse v6 API location format to our internal format."""
        results = []
        for loc in locations:
            if not isinstance(loc, dict):
                continue

            # Extract ID
            station_id = str(loc.get("id", ""))
            if not station_id:
                continue

            # Get name directly from location
            name = loc.get("name", "")

            # Get coordinates from nested location object
            location_data = loc.get("location", {})
            latitude = location_data.get("latitude", 0.0) if location_data else 0.0
            longitude = location_data.get("longitude", 0.0) if location_data else 0.0

            # Get products for transport type info
            products = loc.get("products", {})

            results.append(
                {
                    "id": station_id,
                    "name": name or station_id,
                    "place": "",  # v6 API doesn't always provide place
                    "latitude": float(latitude) if latitude else 0.0,
                    "longitude": float(longitude) if longitude else 0.0,
                    "products": products,
                }
            )

        return results

    def _parse_station_data(self, data: dict[str, Any], station_id: str) -> dict[str, Any]:
        """Parse station data from API response."""
        return {
            "id": str(data.get("id", station_id)),
            "name": data.get("name", ""),
            "place": "",
            "latitude": data.get("location", {}).get("latitude", 0.0),
            "longitude": data.get("location", {}).get("longitude", 0.0),
            "products": data.get("products", {}),
        }

    async def _parse_station_response(
        self, response: "ClientResponse", station_id: str
    ) -> dict[str, Any] | None:
        """Parse station info from API response."""
        if response.status == 200:
            data = await response.json()
            if isinstance(data, dict):
                return self._parse_station_data(data, station_id)
        return None

    async def _fetch_station_info_direct(self, station_id: str) -> dict[str, Any] | None:
        """Fetch station info directly from the API endpoint."""
        if not self._session:
            return None

        try:
            url = f"{DB_STOPS_URL}/{station_id}"
            async with self._session.get(url, ssl=False) as response:
                return await self._parse_station_response(response, station_id)
        except Exception as e:
            logger.warning(f"Error getting station info: {e}")

        return None

    async def _get_station_info_fallback(self, station_id: str) -> dict[str, Any] | None:
        """Fallback to search if direct fetch fails."""
        results = await self.search_stations(station_id)
        if results:
            return results[0]
        return None

    async def get_station_info(self, station_id: str) -> dict[str, Any] | None:
        """Get station information by ID.

        Args:
            station_id: Station ID to look up.

        Returns:
            Station data dictionary or None if not found.
        """
        direct_result = await self._fetch_station_info_direct(station_id)
        if direct_result:
            return direct_result

        return await self._get_station_info_fallback(station_id)

    def _extract_departures_from_response(
        self, data: dict[str, Any] | list[dict[str, Any]]
    ) -> list[dict[str, Any]] | None:
        """Extract departures list from API response."""
        if isinstance(data, dict):
            departures = data.get("departures", [])
            return departures if isinstance(departures, list) else None
        if isinstance(data, list):
            return data
        return None

    async def _log_error_response(self, response: Any, url: str) -> None:
        """Log error response details."""
        error_text = await response.text()
        error_body = error_text[:500] if error_text else "(empty response body)"
        content_type = response.headers.get("Content-Type", "unknown")
        retry_after = response.headers.get("Retry-After")
        server = response.headers.get("Server", "unknown")
        extra_info = []
        if retry_after:
            extra_info.append(f"Retry-After: {retry_after}")
        extra_info_str = f" [{', '.join(extra_info)}]" if extra_info else ""
        logger.error(
            f"DB API returned status {response.status} for {url}: "
            f"{error_body} (Content-Type: {content_type}, Server: {server}){extra_info_str}"
        )

    async def _handle_departures_response(
        self, response: "ClientResponse", url: str
    ) -> list[dict[str, Any]] | None:
        """Handle departures API response."""
        if response.status == 200:
            data = await response.json()
            departures = self._extract_departures_from_response(data)
            if departures is not None:
                return departures

        await self._log_error_response(response, url)
        return None

    async def fetch_departures(self, station_id: str, duration: int = 60) -> list[dict[str, Any]]:
        """Fetch departures from v6.db.transport.rest/stops/{id}/departures.

        Args:
            station_id: Station ID to get departures for.
            duration: Duration in minutes to fetch departures for.

        Returns:
            List of departure dictionaries or empty list if request failed.
        """
        if not self._session:
            return []

        url = f"{DB_STOPS_URL}/{station_id}/departures"
        params: dict[str, str | int] = {"duration": duration, "results": 100}

        rate_limiter = await self._get_rate_limiter()
        await rate_limiter.acquire()

        try:
            async with self._session.get(url, params=params, ssl=False) as response:
                result = await self._handle_departures_response(response, url)
                if result is not None:
                    return result
        except Exception as e:
            logger.warning(f"Error fetching DB departures for {url}: {e}")

        return []
