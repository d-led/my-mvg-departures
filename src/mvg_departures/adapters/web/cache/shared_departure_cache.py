"""Shared departure cache implementation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mvg_departures.domain.contracts.departure_cache import DepartureCacheProtocol

if TYPE_CHECKING:
    from mvg_departures.domain.models.departure import Departure

logger = logging.getLogger(__name__)


class SharedDepartureCache(DepartureCacheProtocol):
    """In-memory cache for raw departures by station ID."""

    def __init__(self) -> None:
        """Initialize the cache."""
        self._cache: dict[str, list[Departure]] = {}

    def get(self, station_id: str) -> list[Departure]:
        """Get cached departures for a station.

        Args:
            station_id: The station ID to get departures for.

        Returns:
            List of cached departures, or empty list if not found.
        """
        return self._cache.get(station_id, [])

    def set(self, station_id: str, departures: list[Departure]) -> None:
        """Set cached departures for a station.

        Args:
            station_id: The station ID.
            departures: The departures to cache.
        """
        self._cache[station_id] = departures

    def get_all_station_ids(self) -> set[str]:  # type: ignore[valid-type]
        """Get all station IDs that have cached data.

        Returns:
            Set of station IDs.
        """
        return set(self._cache.keys())
